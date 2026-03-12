# coding:utf-8
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from qfluentwidgets import BodyLabel, StrongBodyLabel

from ..components.sensor_analysis_overview import SensorDataOverviewWidget
from ..common.style_sheet import StyleSheet


class SensorAnalysisInterface(QWidget):
    """Dedicated sensor analysis page"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('sensorAnalysisInterface')

        self.titleLabel = StrongBodyLabel('传感器数据分析页面', self)
        self.tipLabel = BodyLabel('支持 mock 与后端真实数据模式，可在业务代码中调用 setDataMode("backend", fetcher)。', self)
        self.overviewWidget = SensorDataOverviewWidget(self)

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(24, 20, 24, 24)
        self.vBoxLayout.setSpacing(12)
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.tipLabel)
        self.vBoxLayout.addWidget(self.overviewWidget)

        StyleSheet.HOME_INTERFACE.apply(self)
