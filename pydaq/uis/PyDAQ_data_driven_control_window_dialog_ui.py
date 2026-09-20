# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'PyDAQ_data_driven_control_window_dialog.ui'
##
## Created manually as a PySide6-compatible fallback.
## Re-run pyside6-uic after editing the .ui file.
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy,
    QSpacerItem, QSplitter, QTabWidget, QVBoxLayout, QWidget,
)
from pyqtgraph import PlotWidget


class Ui_DataDrivenControlWindowDialog(object):
    def setupUi(self, DataDrivenControlWindowDialog):
        if not DataDrivenControlWindowDialog.objectName():
            DataDrivenControlWindowDialog.setObjectName(
                "DataDrivenControlWindowDialog"
            )
        DataDrivenControlWindowDialog.resize(1100, 760)
        DataDrivenControlWindowDialog.setMinimumSize(QSize(900, 650))

        self.verticalLayoutMain = QVBoxLayout(DataDrivenControlWindowDialog)
        self.verticalLayoutMain.setObjectName("verticalLayoutMain")
        self.verticalLayoutMain.setContentsMargins(12, 12, 12, 12)
        self.verticalLayoutMain.setSpacing(10)

        self.groupBoxStatus = QGroupBox(DataDrivenControlWindowDialog)
        self.groupBoxStatus.setObjectName("groupBoxStatus")
        self.gridLayoutStatus = QGridLayout(self.groupBoxStatus)
        self.gridLayoutStatus.setObjectName("gridLayoutStatus")

        self.labelStateTitle = QLabel(self.groupBoxStatus)
        self.labelStateTitle.setObjectName("labelStateTitle")
        self.labelStateTitle.setAlignment(
            Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter
        )
        self.gridLayoutStatus.addWidget(self.labelStateTitle, 0, 0, 1, 1)

        self.labelState = QLabel(self.groupBoxStatus)
        self.labelState.setObjectName("labelState")
        state_font = QFont()
        state_font.setBold(True)
        self.labelState.setFont(state_font)
        self.gridLayoutStatus.addWidget(self.labelState, 0, 1, 1, 1)

        self.labelSetpointTitle = QLabel(self.groupBoxStatus)
        self.labelSetpointTitle.setObjectName("labelSetpointTitle")
        self.labelSetpointTitle.setAlignment(
            Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter
        )
        self.gridLayoutStatus.addWidget(
            self.labelSetpointTitle, 0, 2, 1, 1
        )

        self.doubleSpinBoxSetpoint = QDoubleSpinBox(self.groupBoxStatus)
        self.doubleSpinBoxSetpoint.setObjectName("doubleSpinBoxSetpoint")
        self.doubleSpinBoxSetpoint.setDecimals(6)
        self.doubleSpinBoxSetpoint.setRange(0.0, 5.0)
        self.doubleSpinBoxSetpoint.setSingleStep(0.1)
        self.doubleSpinBoxSetpoint.setValue(2.0)
        self.doubleSpinBoxSetpoint.setSuffix(" V")
        self.spin_setpoint = self.doubleSpinBoxSetpoint
        self.button_apply_setpoint = QPushButton("APPLY", self.groupBoxStatus)
        self.button_apply_setpoint.setObjectName("button_apply_setpoint")
        self.gridLayoutStatus.addWidget(self.button_apply_setpoint, 1, 3, 1, 1)
        self.gridLayoutStatus.addWidget(
            self.doubleSpinBoxSetpoint, 0, 3, 1, 1
        )

        self.labelStatusTitle = QLabel(self.groupBoxStatus)
        self.labelStatusTitle.setObjectName("labelStatusTitle")
        self.labelStatusTitle.setAlignment(
            Qt.AlignRight | Qt.AlignTrailing | Qt.AlignTop
        )
        self.gridLayoutStatus.addWidget(
            self.labelStatusTitle, 1, 0, 1, 1
        )

        self.labelStatus = QLabel(self.groupBoxStatus)
        self.labelStatus.setObjectName("labelStatus")
        self.labelStatus.setWordWrap(True)
        self.gridLayoutStatus.addWidget(self.labelStatus, 1, 1, 1, 3)

        self.progressBar = QProgressBar(self.groupBoxStatus)
        self.progressBar.setObjectName("progressBar")
        self.progressBar.setValue(0)
        self.progressBar.setFormat("%p%")
        self.gridLayoutStatus.addWidget(self.progressBar, 2, 0, 1, 4)
        self.verticalLayoutMain.addWidget(self.groupBoxStatus)

        self.splitterMain = QSplitter(DataDrivenControlWindowDialog)
        self.splitterMain.setObjectName("splitterMain")
        self.splitterMain.setOrientation(Qt.Horizontal)

        self.tabWidgetPlots = QTabWidget(self.splitterMain)
        self.tabWidgetPlots.setObjectName("tabWidgetPlots")

        self.tabExperiment = QWidget()
        self.tabExperiment.setObjectName("tabExperiment")
        self.verticalLayoutExperiment = QVBoxLayout(self.tabExperiment)
        self.verticalLayoutExperiment.setObjectName(
            "verticalLayoutExperiment"
        )
        self.verticalLayoutExperiment.setContentsMargins(4, 4, 4, 4)
        self.plotWidgetExperiment = PlotWidget(self.tabExperiment)
        self.plotWidgetExperiment.setObjectName("plotWidgetExperiment")
        self.verticalLayoutExperiment.addWidget(self.plotWidgetExperiment)
        self.tabWidgetPlots.addTab(self.tabExperiment, "")

        self.tabControl = QWidget()
        self.tabControl.setObjectName("tabControl")
        self.verticalLayoutControl = QVBoxLayout(self.tabControl)
        self.verticalLayoutControl.setObjectName("verticalLayoutControl")
        self.verticalLayoutControl.setContentsMargins(4, 4, 4, 4)
        self.plotWidgetControl = PlotWidget(self.tabControl)
        self.plotWidgetControl.setObjectName("plotWidgetControl")
        self.verticalLayoutControl.addWidget(self.plotWidgetControl)
        self.tabWidgetPlots.addTab(self.tabControl, "")

        self.groupBoxController = QGroupBox(self.splitterMain)
        self.groupBoxController.setObjectName("groupBoxController")
        self.groupBoxController.setMinimumSize(QSize(270, 0))
        self.groupBoxController.setMaximumSize(QSize(360, 16777215))
        self.verticalLayoutController = QVBoxLayout(
            self.groupBoxController
        )
        self.verticalLayoutController.setObjectName(
            "verticalLayoutController"
        )

        self.labelRhoTitle = QLabel(self.groupBoxController)
        self.labelRhoTitle.setObjectName("labelRhoTitle")
        self.verticalLayoutController.addWidget(self.labelRhoTitle)

        self.plainTextEditRho = QPlainTextEdit(self.groupBoxController)
        self.plainTextEditRho.setObjectName("plainTextEditRho")
        self.plainTextEditRho.setMinimumSize(QSize(0, 150))
        self.plainTextEditRho.setReadOnly(True)
        self.verticalLayoutController.addWidget(self.plainTextEditRho)

        self.labelWorkflowTitle = QLabel(self.groupBoxController)
        self.labelWorkflowTitle.setObjectName("labelWorkflowTitle")
        workflow_font = QFont()
        workflow_font.setBold(True)
        self.labelWorkflowTitle.setFont(workflow_font)
        self.verticalLayoutController.addWidget(self.labelWorkflowTitle)

        self.labelWorkflow = QLabel(self.groupBoxController)
        self.labelWorkflow.setObjectName("labelWorkflow")
        self.labelWorkflow.setWordWrap(True)
        self.verticalLayoutController.addWidget(self.labelWorkflow)

        self.verticalSpacerController = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.verticalLayoutController.addItem(self.verticalSpacerController)
        self.verticalLayoutMain.addWidget(self.splitterMain)

        self.horizontalLayoutButtons = QHBoxLayout()
        self.horizontalLayoutButtons.setObjectName("horizontalLayoutButtons")
        self.horizontalSpacerButtons = QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum
        )
        self.horizontalLayoutButtons.addItem(self.horizontalSpacerButtons)

        self.pushButtonStart = QPushButton(DataDrivenControlWindowDialog)
        self.pushButtonStart.setObjectName("pushButtonStart")
        self.pushButtonStart.setMinimumSize(QSize(120, 34))
        self.pushButtonStart.setDefault(True)
        self.horizontalLayoutButtons.addWidget(self.pushButtonStart)

        self.pushButtonStop = QPushButton(DataDrivenControlWindowDialog)
        self.pushButtonStop.setObjectName("pushButtonStop")
        self.pushButtonStop.setMinimumSize(QSize(120, 34))
        self.horizontalLayoutButtons.addWidget(self.pushButtonStop)

        self.pushButtonSave = QPushButton(DataDrivenControlWindowDialog)
        self.pushButtonSave.setObjectName("pushButtonSave")
        self.pushButtonSave.setMinimumSize(QSize(120, 34))
        self.horizontalLayoutButtons.addWidget(self.pushButtonSave)
        self.verticalLayoutMain.addLayout(self.horizontalLayoutButtons)

        self.retranslateUi(DataDrivenControlWindowDialog)
        self.tabWidgetPlots.setCurrentIndex(0)
        QMetaObject.connectSlotsByName(DataDrivenControlWindowDialog)

    def retranslateUi(self, DataDrivenControlWindowDialog):
        DataDrivenControlWindowDialog.setWindowTitle(
            QCoreApplication.translate(
                "DataDrivenControlWindowDialog",
                "PYDAQ - Data-Driven Control",
                None,
            )
        )
        self.groupBoxStatus.setTitle(
            QCoreApplication.translate(
                "DataDrivenControlWindowDialog", "Experiment status", None
            )
        )
        self.labelStateTitle.setText("State:")
        self.labelState.setText("Idle")
        self.labelSetpointTitle.setText("Setpoint:")
        self.labelStatusTitle.setText("Status:")
        self.labelStatus.setText(
            "Configure the experiment and press Start."
        )
        self.tabWidgetPlots.setTabText(
            self.tabWidgetPlots.indexOf(self.tabExperiment),
            "PRBS experiment",
        )
        self.tabWidgetPlots.setTabText(
            self.tabWidgetPlots.indexOf(self.tabControl),
            "Real-time control",
        )
        self.groupBoxController.setTitle("NCbT controller")
        self.labelRhoTitle.setText("Estimated parameters (rho)")
        self.plainTextEditRho.setPlaceholderText(
            "Controller parameters will appear here after the NCbT design."
        )
        self.labelWorkflowTitle.setText("Workflow")
        self.labelWorkflow.setText(
            "1. Connect to Arduino\n"
            "2. Apply the PRBS signal\n"
            "3. Collect input-output data\n"
            "4. Estimate rho with NCbT\n"
            "5. Run the controller\n"
            "6. Apply the safe output"
        )
        self.pushButtonStart.setText("Start")
        self.pushButtonStop.setText("Stop")
        self.pushButtonSave.setText("Save data")
