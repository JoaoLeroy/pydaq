# pydaq/data_driven_control.py

import time
import warnings
import numpy as np
import scipy.signal as signal
import ast

from pydaq.utils.base import Base, nidaqmx



try:
    from pyncbt import NCbT_open, NCbT_closed
except ImportError:
    NCbT_open = None
    NCbT_closed = None


class DiscreteFilter:
    """
    Simple discrete-time filter used to evaluate each controller basis function
    sample by sample.

    The transfer function is represented in q^-1 as:

        H(q) = B(q) / A(q)

    with:

        y[k] = b0*x[k] + b1*x[k-1] + ...
               - a1*y[k-1] - a2*y[k-2] - ...

    The first denominator coefficient is normalized to 1.
    """

    def __init__(self, numerator, denominator):
        self.b = np.asarray(numerator, dtype=float).flatten()
        self.a = np.asarray(denominator, dtype=float).flatten()

        if self.a.size == 0:
            raise ValueError("[PYDAQ] Denominator cannot be empty.")

        if np.isclose(self.a[0], 0.0):
            raise ValueError("[PYDAQ] First denominator coefficient cannot be zero.")

        self.b = self.b / self.a[0]
        self.a = self.a / self.a[0]

        self.x_memory = np.zeros(max(len(self.b), 1))
        self.y_memory = np.zeros(max(len(self.a) - 1, 1))

    def reset(self):
        """
        Reset internal filter states.
        """

        self.x_memory[:] = 0.0
        self.y_memory[:] = 0.0

    def update(self, x):
        """
        Update the filter with one input sample.

        Parameters
        ----------
        x : float
            Current input sample.

        Returns
        -------
        float
            Current output sample.
        """

        self.x_memory[1:] = self.x_memory[:-1]
        self.x_memory[0] = float(x)

        y = 0.0

        for i in range(len(self.b)):
            y += self.b[i] * self.x_memory[i]

        for i in range(1, len(self.a)):
            y -= self.a[i] * self.y_memory[i - 1]

        if len(self.y_memory) > 0:
            self.y_memory[1:] = self.y_memory[:-1]
            self.y_memory[0] = y

        return float(y)


class DataDrivenController:
    """
    Fixed-structure data-driven controller.

    The controller has the form:

        C(q) = rho_0 * beta_0(q)
             + rho_1 * beta_1(q)
             + ...
             + rho_n * beta_n(q)

    The beta structure is defined by the user. The rho vector is computed
    by NCbT.
    """

    def __init__(self, rho, beta):
        self.rho = np.asarray(rho, dtype=float).flatten()
        self.beta = beta

        validate_beta(self.beta)

        if len(self.rho) != len(self.beta):
            raise ValueError(
                "[PYDAQ] The number of rho parameters must match the number "
                "of beta basis functions."
            )

        self.filters = []
        self.reset()

    def reset(self):
        """
        Reset all basis filters.
        """

        self.filters = [
            DiscreteFilter(num, den)
            for num, den in self.beta
        ]

    def update(self, error):
        """
        Compute one control sample from the current tracking error.

        Parameters
        ----------
        error : float
            Current control error.

        Returns
        -------
        float
            Control action before calibration and saturation.
        """

        control_action = 0.0

        for rho_i, filter_i in zip(self.rho, self.filters):
            control_action += rho_i * filter_i.update(error)

        return float(control_action)

    def get_transfer_function(self):
        """
        Compute the equivalent transfer function of the NCbT controller.

        The controller is:

            C(q) = rho[0] * beta[0](q)
                 + rho[1] * beta[1](q)
                 + ...
                 + rho[n] * beta[n](q)

        where:

            beta[i](q) = B_i(q) / A_i(q)

        The returned numerator and denominator are represented in ascending
        powers of q^-1.

        Example
        -------
        [1, 2, 3] means:

            1 + 2 q^-1 + 3 q^-2

        Returns
        -------
        numerator : numpy.ndarray
            Equivalent controller numerator.
        denominator : numpy.ndarray
            Equivalent controller denominator.
        """

        validate_beta(self.beta)

        # Common denominator:
        #
        # A_common(q) = A_0(q) * A_1(q) * ... * A_n(q)
        common_den = np.array([1.0])

        for _, den_i in self.beta:
            den_i = np.asarray(den_i, dtype=float).flatten()
            common_den = qpolymul(common_den, den_i)

        # Equivalent numerator:
        #
        # B_eq(q) = sum_i rho_i * B_i(q) * product_{j != i} A_j(q)
        equivalent_num = np.zeros(1)

        for i, (rho_i, basis_i) in enumerate(zip(self.rho, self.beta)):
            num_i = np.asarray(basis_i[0], dtype=float).flatten()
            den_i = np.asarray(basis_i[1], dtype=float).flatten()

            partial_num = rho_i * num_i

            multiplier = np.array([1.0])

            for j, basis_j in enumerate(self.beta):
                if j == i:
                    continue

                den_j = np.asarray(basis_j[1], dtype=float).flatten()
                multiplier = qpolymul(multiplier, den_j)

            term_num = qpolymul(partial_num, multiplier)
            equivalent_num = qpolyadd(equivalent_num, term_num)

        equivalent_num, common_den = normalize_transfer_function(
            equivalent_num,
            common_den
        )

        return equivalent_num, common_den


class NCbTClosedLoopEstimator:
    """
    Wrapper around pyncbt.NCbT_closed.

    This class isolates the external pyncbt dependency from the rest of PYDAQ.
    """

    def __init__(
        self,
        u,
        y,
        r,
        num_M,
        den_M,
        Ts,
        t,
        l,
        beta
    ):
        self.u = np.asarray(u, dtype=float).flatten()
        self.y = np.asarray(y, dtype=float).flatten()
        self.r = np.asarray(r, dtype=float).flatten()
        self.num_M = np.asarray(num_M, dtype=float).flatten()
        self.den_M = np.asarray(den_M, dtype=float).flatten()
        self.Ts = float(Ts)
        self.t = np.asarray(t, dtype=float).flatten()
        self.l = int(l)
        self.beta = beta
        self.rho = None
        validate_beta(self.beta)
        self._validate_data()


    def _validate_data(self):
        """
        Validate data before calling pyncbt.
        """

        n = len(self.u)

        if len(self.y) != n:
            raise ValueError("[PYDAQ] Signals u and y must have the same length.")

        if len(self.r) != n:
            raise ValueError("[PYDAQ] Signals u and r must have the same length.")

        if len(self.t) != n:
            raise ValueError("[PYDAQ] Signals u and t must have the same length.")

        if n < 2:
            raise ValueError("[PYDAQ] At least two samples are required.")

        if self.Ts <= 0:
            raise ValueError("[PYDAQ] Sampling time Ts must be positive.")

        if self.l <= 0:
            raise ValueError("[PYDAQ] Instrument length l must be positive.")


    def run(self):
        """
        Run closed-loop NCbT.

        Returns
        -------
        numpy.ndarray
            Estimated controller parameter vector.
        """

        if NCbT_closed is None:
            raise ImportError(
                "[PYDAQ] pyncbt is not installed. Install it with: pip install pyncbt"
            )

        estimator = NCbT_closed(
            self.u,
            self.y,
            self.r,
            self.num_M,
            self.den_M,
            self.Ts,
            self.t,
            self.l,
            self.beta
        )

        self.rho = np.asarray(estimator.run(), dtype=float).flatten()

        return self.rho


class DataDrivenControl(Base):
    """
    Data-driven control implementation for PYDAQ.

    This class follows the same general structure as PIDControl, but the
    controller parameters are obtained using NCbT through the pyncbt package.

    The controller is then executed sample by sample using the estimated
    parameter vector rho and the chosen controller basis beta.
    """

    def __init__(
        self,
        rho=None,
        beta=None,
        setpoint=0.0,
        numerator='1',
        denominator='s+0.2',
        calibration_equation_vu=None,
        calibration_equation_uv=None,
        unit='Voltage (V)',
        period=1
    ):
        super().__init__()

        self.rho = None if rho is None else np.asarray(rho, dtype=float).flatten()
        self.beta = beta

        self.setpoint = float(setpoint)
        self.numerator = numerator
        self.denominator = denominator
        self.calibration_equation_vu = calibration_equation_vu
        self.calibration_equation_uv = calibration_equation_uv
        self.unit = unit
        self.period = float(period)

        self.disturbe = 0

        # NI-DAQ defaults
        self.device = "Dev1"
        self.ao_channel = "ao0"
        self.ai_channel = "ai0"
        self.terminal = "Diff"

        # Arduino defaults
        self.com_port = "COM1"

        self.channels = [self.ai_channel]
        self.ao_channels = [self.ao_channel]

        # Internal control variables
        self.feedback_value = 0.0
        self.feedback_calibrated = 0.0
        self.control_voltage = 0.0
        self.control_unit = 0.0
        self.control = 0.0
        self.error = 0.0
        self.output = 0.0
        self.previous_output = 0.0

        # NCbT-related variables
        self.num_M = None
        self.den_M = None
        self.l = 20
        self.controller = None

        if self.rho is not None and self.beta is not None:
            self.controller = DataDrivenController(self.rho, self.beta)

    def tune_ncbt_open_loop(
        self,
        u,
        y,
        num_M,
        den_M,
        Ts=None,
        t=None,
        l=20,
        beta=None,
    ):
        """
        Tune controller using open-loop NCbT.

        Required by pyncbt:
            NCbT_open(u, y, num_M, den_M, Ts, t, l, beta)
        """

        if NCbT_open is None:
            raise ImportError(
                "[PYDAQ] pyncbt is not installed. Install it with: pip install pyncbt"
            )

        validate_beta(beta)

        u = np.asarray(u, dtype=float).flatten()
        y = np.asarray(y, dtype=float).flatten()
        num_M = np.asarray(num_M, dtype=float).flatten()
        den_M = np.asarray(den_M, dtype=float).flatten()

        if Ts is None:
            Ts = self.period

        Ts = float(Ts)

        if t is None:
            t = np.arange(len(u)) * Ts
        else:
            t = np.asarray(t, dtype=float).flatten()

        if len(u) != len(y):
            raise ValueError("[PYDAQ] u and y must have the same length.")

        if len(t) != len(u):
            raise ValueError("[PYDAQ] t must have the same length as u and y.")

        estimator = NCbT_open(
            u,
            y,
            num_M,
            den_M,
            Ts,
            t,
            int(l),
            beta,
        )

        self.rho = np.asarray(estimator.run(), dtype=float).flatten()
        self.beta = beta
        self.num_M = num_M
        self.den_M = den_M
        self.period = Ts
        self.l = int(l)

        self.controller = DataDrivenController(
            rho=self.rho,
            beta=self.beta,
        )

        return self.rho

    def tune_ncbt_closed_loop(
        self,
        u,
        y,
        r,
        num_M,
        den_M,
        Ts=None,
        t=None,
        l=20,
        beta=None,
    ):
        """
        Tune controller using closed-loop NCbT.

        Required by pyncbt:
            NCbT_closed(u, y, r, num_M, den_M, Ts, t, l, beta)
        """

        if NCbT_closed is None:
            raise ImportError(
                "[PYDAQ] pyncbt is not installed. Install it with: pip install pyncbt"
            )

        validate_beta(beta)

        u = np.asarray(u, dtype=float).flatten()
        y = np.asarray(y, dtype=float).flatten()
        r = np.asarray(r, dtype=float).flatten()
        num_M = np.asarray(num_M, dtype=float).flatten()
        den_M = np.asarray(den_M, dtype=float).flatten()

        if Ts is None:
            Ts = self.period

        Ts = float(Ts)

        if t is None:
            t = np.arange(len(u)) * Ts
        else:
            t = np.asarray(t, dtype=float).flatten()

        if len(u) != len(y):
            raise ValueError("[PYDAQ] u and y must have the same length.")

        if len(r) != len(u):
            raise ValueError("[PYDAQ] r must have the same length as u and y.")

        if len(t) != len(u):
            raise ValueError("[PYDAQ] t must have the same length as u, y and r.")

        estimator = NCbT_closed(
            u,
            y,
            r,
            num_M,
            den_M,
            Ts,
            t,
            int(l),
            beta,
        )

        self.rho = np.asarray(estimator.run(), dtype=float).flatten()
        self.beta = beta
        self.num_M = num_M
        self.den_M = den_M
        self.period = Ts
        self.l = int(l)

        self.controller = DataDrivenController(
            rho=self.rho,
            beta=self.beta,
        )

        return self.rho

    def update(self, feedback_value):
        """
        Compute one control sample.

        This method mirrors PIDControl.update(), but instead of computing
        proportional, integral and derivative terms, it evaluates the NCbT
        controller basis functions.

        Parameters
        ----------
        feedback_value : float
            Current plant output.

        Returns
        -------
        tuple
            control output and tracking error.
        """

        if self.controller is None:
            raise RuntimeError("[PYDAQ] Data-driven controller has not been tuned yet.")

        self.error = self.setpoint - feedback_value
        self.output = self.controller.update(self.error)
        self.previous_output = self.output

        return self.output, self.error

    def reset_controller(self):
        """
        Reset internal controller states.
        """

        if self.controller is not None:
            self.controller.reset()

        self.error = 0.0
        self.output = 0.0
        self.previous_output = 0.0

    def data_driven_control_arduino(self):
        """
        Initialize Arduino data-driven control.
        """

        self.feedback_value = 0.0
        self.feedback_calibrated = 0.0
        self.control_voltage = 0.0
        self.control_unit = 0.0
        self.control = 0.0
        self.error = 0.0
        self.output = 0.0
        self.previous_output = 0.0

        self.reset_controller()

        self._open_serial()

        self.arduino_ai_bits = 10
        self.ard_ao_max, self.ard_ao_min = 5, 0
        self.ard_vpb = (
            (self.ard_ao_max - self.ard_ao_min)
            / ((2 ** self.arduino_ai_bits) - 1)
        )

        time.sleep(0.5)

        if hasattr(self, '_verify_arduino_firmware') and not self._verify_arduino_firmware():
            self.ser.close()
            warnings.warn(
                "[PYDAQ] PyDAQ Firmware not detected on this board! "
                "Please go to the top menu and click on 'Arduino - Firmware' "
                "to upload the correct code."
            )
            self.plot_running = False
            self.control_running = False
            return

        self.ser.reset_input_buffer()

        try:
            _ = self.ser.readline()
        except Exception:
            pass

        self.title = f"PYDAQ - Data-Driven Control (Arduino), Port: {self.com_port}"

    def update_plot_arduino(self):
        """
        Read Arduino data, compute one data-driven control sample, send PWM,
        and return values for plotting.
        """

        try:
            self.ser.reset_input_buffer()
            self.ser.readline()

            raw = self.ser.readline()
            values = list(map(int, raw.decode("utf-8").strip().split(",")))

            if len(values) < 6:
                raise ValueError(
                    "[PYDAQ] Data parsing error: incomplete universal frame received. "
                    "Please ensure the correct PyDAQ firmware is running."
                )

        except Exception:
            values = None

        if values is not None:
            idx = int(self.channels[0].replace("A", ""))
            self.feedback_value = values[idx] * self.ard_vpb

        self.feedback_calibrated = self.calibrationuv(self.feedback_value)

        self.control_unit, self.error = self.update(self.feedback_calibrated)

        self.control_voltage = self.calibrationvu(self.control_unit)
        self.control = self.control_voltage

        if self.control <= self.ard_ao_min:
            self.control = self.ard_ao_min
        elif self.control >= self.ard_ao_max:
            self.control = self.ard_ao_max

        duty = int((self.control / self.ard_ao_max) * 255)

        pin_num = self.ao_channels[0].replace("D", "")
        msg = f"{pin_num}:{duty}\n"

        self.ser.write(msg.encode())

        return (
            self.feedback_calibrated,
            self.error,
            self.setpoint,
            self.control
        )

    def data_driven_control_nidaq(self):
        """
        Initialize NI-DAQ data-driven control.
        """

        if not self._check_nidaq_availability():
            return

        terminal_config = self.terminal

        self._nidaq_info()

        self.task_ai = nidaqmx.Task()
        self.task_ao = nidaqmx.Task()

        self.task_ai.ai_channels.add_ai_voltage_chan(
            self.device + "/" + self.channels[0],
            terminal_config=terminal_config
        )

        self.task_ao.ao_channels.add_ao_voltage_chan(
            self.device + "/" + self.ao_channels[0],
            min_val=0.0,
            max_val=5.0
        )

        self.feedback_value = 0.0
        self.feedback_calibrated = 0.0
        self.control_voltage = 0.0
        self.control = 0.0
        self.control_unit = 0.0
        self.error = 0.0
        self.output = 0.0
        self.previous_output = 0.0

        self.reset_controller()

    def update_plot_nidaq(self):
        """
        Read NI-DAQ data, compute one control sample, write analog output,
        and return values for plotting.
        """

        if not hasattr(self, 'task_ai'):
            return (0.0, 0.0, self.setpoint, 0.0)

        values = self.task_ai.read()

        if isinstance(values, list):
            self.feedback_value = values[0]
        else:
            self.feedback_value = values

        self.feedback_calibrated = self.calibrationuv(self.feedback_value)

        self.control_unit, self.error = self.update(self.feedback_calibrated)

        self.control_voltage = self.calibrationvu(self.control_unit)
        self.control = self.control_voltage

        if self.control <= 0:
            self.control = 0
        elif self.control >= 5:
            self.control = 5

        self.task_ao.write(self.control)

        return (
            self.feedback_calibrated,
            self.error,
            self.setpoint,
            self.control
        )

    def simulate_system(self):
        """
        Inicializa a simulação para um sistema discreto.
        Espera que self.numerator e self.denominator sejam listas de coeficientes
        no domínio q^-1 (ordem crescente de potências).
        Exemplo: numerator = [1], denominator = [1, -0.8] representa:
            G(q) = 1 / (1 - 0.8 q^-1)
        """
        self.feedback_voltages = []
        self.controls_voltages = []

        self.feedback_value = 0.0
        self.control = 0.0
        self.control_voltage = 0.0
        self.feedback_calibrated = 0.0
        self.control_unit = 0.0
        self.error = 0.0
        self.output = 0.0
        self.previous_output = 0.0

        self.reset_controller()

        # Converte as strings para listas de floats, se forem strings
        if isinstance(self.numerator, str):
            # Assume que é uma representação de lista, ex: "[1, 0.5]"
            # Usamos ast.literal_eval para segurança
            import ast
            self.num_discrete = np.asarray(ast.literal_eval(self.numerator), dtype=float).flatten()
        else:
            self.num_discrete = np.asarray(self.numerator, dtype=float).flatten()

        if isinstance(self.denominator, str):
            import ast
            self.den_discrete = np.asarray(ast.literal_eval(self.denominator), dtype=float).flatten()
        else:
            self.den_discrete = np.asarray(self.denominator, dtype=float).flatten()

        # Normaliza para que den[0] = 1
        if np.isclose(self.den_discrete[0], 0.0):
            raise ValueError("[PYDAQ] First denominator coefficient cannot be zero.")
        self.num_discrete = self.num_discrete / self.den_discrete[0]
        self.den_discrete = self.den_discrete / self.den_discrete[0]

        # Estado do filtro para simulação (zi)
        self.zi = None

    def update_simulated_system(self):
        """
        Atualiza a simulação de um sistema discreto por um período de amostragem.
        Usa scipy.signal.lfilter para atualizar a saída.
        """
        self.feedback_calibrated = self.calibrationuv(self.feedback_value)

        self.control_unit, self.error = self.update(self.feedback_calibrated)

        self.control_unit = self.control_unit - self.disturbe

        self.control_voltage = self.calibrationvu(self.control_unit)
        self.control = self.control_voltage

        if self.control <= 0:
            self.control = 0
        elif self.control >= 5:
            self.control = 5

        self.controls_voltages.append(self.control_voltage)
        self.feedback_voltages.append(self.feedback_value)

        # Aplica o filtro discreto: y[k] = sum(b * x) - sum(a[1:] * y_anterior)
        # Usamos lfilter com o estado inicial zi
        if self.zi is None:
            # Inicializa zi com zeros (condições iniciais nulas)
            self.zi = np.zeros(max(len(self.den_discrete)-1, len(self.num_discrete)-1))
        # A entrada é o sinal de controle
        y_new, self.zi = signal.lfilter(self.num_discrete, self.den_discrete, [self.control], zi=self.zi)
        self.feedback_value = y_new[0]

        return (
            self.feedback_calibrated,
            self.error,
            self.setpoint,
            self.control
        )

    def calibrationvu(self, output):
        """
        Convert control unit to voltage using user calibration equation.
        """

        if not self.calibration_equation_vu or not self.calibration_equation_vu.strip():
            return output

        try:
            output_calibrated = eval(
                self.calibration_equation_vu,
                {"__builtins__": None},
                {"x": output}
            )
            return float(output_calibrated)

        except Exception as e:
            print(f"\n[PYDAQ] Error evaluating calibration_equation_vu: {e}")
            return output

    def calibrationuv(self, output):
        """
        Convert voltage to engineering unit using user calibration equation.
        """

        if not self.calibration_equation_uv or not self.calibration_equation_uv.strip():
            return output

        try:
            output_calibrated = eval(
                self.calibration_equation_uv,
                {"__builtins__": None},
                {"x": output}
            )
            return float(output_calibrated)

        except Exception as e:
            print(f"\n[PYDAQ] Error evaluating calibration_equation_uv: {e}")
            return output

    def parse_polynomial(self, poly_str):
        """
        Parse a polynomial string into coefficients.

        Example
        -------
        '2*s**2 + 3*s - 1' -> [2.0, 3.0, -1.0]
        """

        poly_str = poly_str.replace(' ', '').replace('-', '+-')

        if poly_str.startswith('+-'):
            poly_str = poly_str[1:]

        terms = poly_str.split('+')

        max_degree = 0

        for term in terms:
            if not term:
                continue

            if 's' in term:
                if '**' in term:
                    try:
                        degree = int(term.split('**')[1])
                        if degree > max_degree:
                            max_degree = degree
                    except (ValueError, IndexError):
                        raise ValueError(f"[PYDAQ] Invalid term format: {term}")
                else:
                    if 1 > max_degree:
                        max_degree = 1

        coeffs = [0.0] * (max_degree + 1)

        for term in terms:
            if not term:
                continue

            if 's' not in term:
                coeffs[max_degree] += float(term)
                continue

            if '**' in term:
                parts = term.split('**')
                degree = int(parts[1])
                coeff_part = parts[0].replace('s', '').replace('*', '')
            else:
                degree = 1
                coeff_part = term.replace('s', '').replace('*', '')

            if coeff_part == '':
                coeff_val = 1.0
            elif coeff_part == '-':
                coeff_val = -1.0
            else:
                coeff_val = float(coeff_part)

            coeffs[max_degree - degree] += coeff_val

        return coeffs

    def get_value_simulate_system(self, system, period, control, x0):
        """
        Simulate the continuous-time plant during one sampling period.
        """

        time_control = np.linspace(0, period, 100)
        input_control_signal = np.full_like(time_control, control)

        time_array_output, system_output, _ = signal.lsim(
            system,
            input_control_signal,
            time_control,
            X0=x0
        )

        last_time = time_array_output[-1]
        last_output = system_output[-1]

        return last_time, last_output

    def get_controller_parameters(self):
        """
        Return NCbT controller parameters.
        """

        if self.rho is None:
            return None

        return self.rho.copy()

    def get_controller_transfer_function(self):
        """
        Return equivalent controller transfer function.
        """

        if self.controller is None:
            raise RuntimeError("[PYDAQ] Data-driven controller has not been tuned yet.")

        return self.controller.get_transfer_function()


def create_default_reference_model(Ts, omega_bar=10.0, delay=3):
    """
    Create the default reference model used in the pyncbt closed-loop tutorial.

    M(q) = q^-delay * (1 - alpha)^2 / (1 - 2 alpha q^-1 + alpha^2 q^-2)

    Parameters
    ----------
    Ts : float
        Sampling time.
    omega_bar : float
        Desired closed-loop bandwidth.
    delay : int
        Delay in samples.

    Returns
    -------
    tuple
        num_M, den_M
    """

    Ts = float(Ts)

    if Ts <= 0:
        raise ValueError("[PYDAQ] Sampling time Ts must be positive.")

    if delay < 0:
        raise ValueError("[PYDAQ] Delay must be non-negative.")

    alpha = np.exp(-Ts * float(omega_bar))

    num_M = np.zeros(delay + 1)
    num_M[-1] = (1.0 - alpha) ** 2

    den_M = np.array([1.0, -2.0 * alpha, alpha ** 2])

    return num_M, den_M


def create_default_ncbt_basis(order=6):
    """
    Create default NCbT basis.

    For order = 6:

        beta = [
            ([1], [1, -1]),
            ([0, 1], [1, -1]),
            ([0, 0, 1], [1, -1]),
            ...
        ]

    This matches the structure used in the pyncbt closed-loop tutorial.
    """

    order = int(order)

    if order <= 0:
        raise ValueError("[PYDAQ] Basis order must be positive.")

    beta = []

    for i in range(order):
        numerator = [0.0] * i + [1.0]
        denominator = [1.0, -1.0]
        beta.append((numerator, denominator))

    return beta


def create_fir_basis(order):
    """
    Create FIR controller basis.

    The basis is:

        1, q^-1, q^-2, ..., q^-(order-1)
    """

    order = int(order)

    if order <= 0:
        raise ValueError("[PYDAQ] FIR order must be positive.")

    beta = []

    for i in range(order):
        numerator = [0.0] * i + [1.0]
        denominator = [1.0]
        beta.append((numerator, denominator))

    return beta


def trim_small_coefficients(poly, tolerance=1e-12):
    """
    Remove small numerical coefficients.
    """

    poly = np.asarray(poly, dtype=float).flatten()

    poly[np.abs(poly) < tolerance] = 0.0

    while len(poly) > 1 and np.isclose(poly[0], 0.0):
        poly = poly[1:]

    return poly

def validate_beta(beta):
    """
    Validate NCbT controller basis.

    Parameters
    ----------
    beta : list
        List of controller basis transfer functions.

        Expected format:

            beta = [
                ([num_0], [den_0]),
                ([num_1], [den_1]),
                ...
            ]

    Raises
    ------
    ValueError
        If beta is invalid.
    """

    if beta is None:
        raise ValueError(
            "[PYDAQ] beta must be provided. "
            "In NCbT, beta defines the controller structure."
        )

    if not isinstance(beta, list):
        raise ValueError("[PYDAQ] beta must be a list of basis transfer functions.")

    if len(beta) == 0:
        raise ValueError("[PYDAQ] beta cannot be empty.")

    for i, basis in enumerate(beta):
        if not isinstance(basis, (list, tuple)) or len(basis) != 2:
            raise ValueError(
                f"[PYDAQ] beta[{i}] must be a tuple/list: (numerator, denominator)."
            )

        numerator, denominator = basis

        numerator = np.asarray(numerator, dtype=float).flatten()
        denominator = np.asarray(denominator, dtype=float).flatten()

        if numerator.size == 0:
            raise ValueError(f"[PYDAQ] beta[{i}] numerator cannot be empty.")

        if denominator.size == 0:
            raise ValueError(f"[PYDAQ] beta[{i}] denominator cannot be empty.")

        if np.isclose(denominator[0], 0.0):
            raise ValueError(
                f"[PYDAQ] beta[{i}] first denominator coefficient cannot be zero."
            )


def qpolyadd(poly_a, poly_b):
    """
    Add two polynomials represented in ascending powers of q^-1.

    Example
    -------
    [1, 2] means:

        1 + 2 q^-1

    This is different from numpy.polyadd, which assumes descending powers.
    """

    poly_a = np.asarray(poly_a, dtype=float).flatten()
    poly_b = np.asarray(poly_b, dtype=float).flatten()

    n = max(len(poly_a), len(poly_b))

    result = np.zeros(n)

    result[:len(poly_a)] += poly_a
    result[:len(poly_b)] += poly_b

    return trim_small_coefficients(result)


def qpolymul(poly_a, poly_b):
    """
    Multiply two polynomials represented in ascending powers of q^-1.
    """

    poly_a = np.asarray(poly_a, dtype=float).flatten()
    poly_b = np.asarray(poly_b, dtype=float).flatten()

    return trim_small_coefficients(np.convolve(poly_a, poly_b))


def normalize_transfer_function(num, den):
    """
    Normalize transfer function so that den[0] = 1.
    """

    num = np.asarray(num, dtype=float).flatten()
    den = np.asarray(den, dtype=float).flatten()

    if den.size == 0:
        raise ValueError("[PYDAQ] Denominator cannot be empty.")

    if np.isclose(den[0], 0.0):
        raise ValueError("[PYDAQ] First denominator coefficient cannot be zero.")

    num = num / den[0]
    den = den / den[0]

    return trim_small_coefficients(num), trim_small_coefficients(den)
