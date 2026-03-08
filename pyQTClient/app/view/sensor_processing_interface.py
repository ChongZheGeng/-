# coding:utf-8
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    CaptionLabel,
    CheckBox,
    ComboBox,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
)

from .nav_interface import NavInterface

logger = logging.getLogger(__name__)


class SensorProcessingInterface(NavInterface):
    """传感器处理页面（第一阶段骨架）"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SensorProcessingInterface")

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(40, 30, 40, 30)
        self.main_layout.setSpacing(20)

        self._build_header()
        self._build_content()
        self._build_bottom_actions()

    def _build_header(self):
        """顶部标题与信息区"""
        title_label = SubtitleLabel("传感器处理")
        self.main_layout.addWidget(title_label)

        info_card = CardWidget(self)
        info_layout = QHBoxLayout(info_card)
        info_layout.setContentsMargins(20, 16, 20, 16)
        info_layout.setSpacing(24)

        info_layout.addWidget(BodyLabel("当前数据记录：未选择"))
        info_layout.addWidget(BodyLabel("文件名：--"))
        info_layout.addWidget(BodyLabel("任务编号：--"))
        info_layout.addWidget(BodyLabel("采样时间：--"))
        info_layout.addStretch(1)

        self.main_layout.addWidget(info_card)

    def _build_content(self):
        """中部：左侧控制区 + 右侧图表占位区"""
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # 左侧控制区
        control_card = CardWidget(self)
        control_card.setMinimumWidth(320)
        control_layout = QVBoxLayout(control_card)
        control_layout.setContentsMargins(20, 20, 20, 20)
        control_layout.setSpacing(12)

        control_layout.addWidget(BodyLabel("数据选择"))
        self.data_selector = ComboBox(control_card)
        self.data_selector.addItems(["示例数据 A", "示例数据 B", "示例数据 C"])
        control_layout.addWidget(self.data_selector)

        control_layout.addSpacing(8)
        control_layout.addWidget(BodyLabel("通道选择"))
        for channel in ["Fx", "Fy", "Fz", "F"]:
            control_layout.addWidget(CheckBox(channel, control_card))

        control_layout.addSpacing(8)
        control_layout.addWidget(BodyLabel("基础处理参数"))
        control_layout.addWidget(CaptionLabel("滤波参数（占位）"))
        control_layout.addWidget(ComboBox(control_card))
        control_layout.addWidget(CaptionLabel("窗口长度（占位）"))
        control_layout.addWidget(ComboBox(control_card))
        control_layout.addStretch(1)

        # 右侧图表占位区
        chart_layout = QVBoxLayout()
        chart_layout.setSpacing(12)

        self.raw_plot_placeholder = self._build_plot_placeholder("原始波形区域（占位）")
        self.processed_plot_placeholder = self._build_plot_placeholder("处理后波形区域（占位）")

        chart_layout.addWidget(self.raw_plot_placeholder, 1)
        chart_layout.addWidget(self.processed_plot_placeholder, 1)

        content_layout.addWidget(control_card, 0)
        content_layout.addLayout(chart_layout, 1)

        self.main_layout.addLayout(content_layout, 1)

    def _build_plot_placeholder(self, text: str):
        """创建图表占位容器"""
        frame = QFrame(self)
        frame.setMinimumHeight(220)
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { border: 1px dashed rgba(120, 120, 120, 0.55); border-radius: 8px; }"
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(BodyLabel(text), alignment=Qt.AlignCenter)
        return frame

    def _build_bottom_actions(self):
        """底部按钮区"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.load_btn = PushButton("加载数据")
        self.apply_btn = PrimaryPushButton("应用处理")
        self.reset_btn = PushButton("重置")
        self.export_btn = PushButton("导出结果")

        button_layout.addWidget(self.load_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch(1)

        self.main_layout.addLayout(button_layout)

    def on_activated(self):
        logger.info("SensorProcessingInterface activated")

    def on_deactivated(self):
        logger.info("SensorProcessingInterface deactivated")
