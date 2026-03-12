# coding:utf-8
from typing import Dict, Any

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame

from qfluentwidgets import (
    CardWidget,
    StrongBodyLabel,
    BodyLabel,
    CaptionLabel,
    PushButton,
    FluentIcon as FIF,
    IconWidget,
    setFont,
)


class WarningTodoItemButton(PushButton):
    """可点击的预警/待办项"""

    def __init__(
        self,
        title: str,
        icon,
        route_key: str,
        warning_style: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.route_key = route_key
        self.warning_style = warning_style
        self._count = 0

        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        self.icon_widget = IconWidget(icon, self)
        self.icon_widget.setFixedSize(18, 18)

        self.title_label = BodyLabel(title, self)
        self.value_label = StrongBodyLabel("0", self)

        layout.addWidget(self.icon_widget)
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.value_label)

        self._apply_style()

    def _apply_style(self):
        if self.warning_style:
            self.setStyleSheet(
                """
                WarningTodoItemButton {
                    border: 1px solid #f1d4d6;
                    border-radius: 8px;
                    background-color: #fff7f7;
                    text-align: left;
                }
                WarningTodoItemButton:hover {
                    background-color: #fdeeee;
                }
                """
            )
            self.icon_widget.setStyleSheet("color:#d13438;")
            self.value_label.setStyleSheet("color:#d13438;")
        else:
            self.setStyleSheet(
                """
                WarningTodoItemButton {
                    border: 1px solid rgba(0, 0, 0, 0.07);
                    border-radius: 8px;
                    background-color: rgba(0, 0, 0, 0.02);
                    text-align: left;
                }
                WarningTodoItemButton:hover {
                    background-color: rgba(0, 0, 0, 0.04);
                }
                """
            )
            self.icon_widget.setStyleSheet("color:#0078d4;")
            self.value_label.setStyleSheet("color:#0078d4;")

    def update_count(self, count: int):
        self._count = max(0, int(count))
        self.value_label.setText(str(self._count))


class WarningTodoCenterWidget(QWidget):
    """预警与待办中心模块（独立 QWidget）"""

    itemClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items: Dict[str, WarningTodoItemButton] = {}
        self.current_data: Dict[str, int] = self.mock_data()

        container = CardWidget(self)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        icon_widget = IconWidget(FIF.WARNING, self)
        icon_widget.setFixedSize(20, 20)
        icon_widget.setStyleSheet("color:#d13438;")
        title = StrongBodyLabel("预警与待办中心", self)
        setFont(title, 15)
        desc = CaptionLabel("点击条目可进入对应业务页面", self)
        desc.setStyleSheet("color:#6f6f6f;")

        title_row.addWidget(icon_widget)
        title_row.addWidget(title)
        title_row.addStretch()
        layout.addLayout(title_row)
        layout.addWidget(desc)

        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: rgba(0,0,0,0.08);")
        layout.addWidget(line)

        self.items_layout = QVBoxLayout()
        self.items_layout.setSpacing(8)
        layout.addLayout(self.items_layout)

        self.empty_state_label = BodyLabel("当前无预警", self)
        self.empty_state_label.setAlignment(Qt.AlignCenter)
        self.empty_state_label.setStyleSheet(
            "color:#6f6f6f;padding:12px;border:1px dashed rgba(0,0,0,0.15);border-radius:8px;"
        )
        layout.addWidget(self.empty_state_label)

        self._build_items()
        self.set_data(self.current_data)

    def _build_items(self):
        configs = [
            ("pending_analysis", "待分析传感器数据数量", FIF.IOT, "sensor_processing", False),
            ("alerts", "异常预警数量", FIF.WARNING, "sensor_processing", True),
            ("pending_recommend", "待推荐任务数量", FIF.ROBOT, "recommendation", False),
            ("unconfirmed_recommend", "推荐后未确认任务数量", FIF.CANCEL_MEDIUM, "recommendation", True),
            ("tool_wear_over_threshold", "刀具磨损超阈值提醒", FIF.DEVELOPER_TOOLS, "tool", True),
        ]

        for key, title, icon, route_key, warning_style in configs:
            item = WarningTodoItemButton(title, icon, route_key, warning_style, self)
            item.clicked.connect(lambda _, k=key: self._on_item_clicked(k))
            self.items_layout.addWidget(item)
            self.items[key] = item

    def _on_item_clicked(self, item_key: str):
        item = self.items.get(item_key)
        if item:
            self.itemClicked.emit(item.route_key)

    def set_data(self, payload: Dict[str, Any]):
        payload = payload or {}
        self.current_data.update(payload)
        has_warning = False

        for key, item in self.items.items():
            value = self.current_data.get(key, 0)
            item.update_count(value)
            if item.warning_style and int(value) > 0:
                has_warning = True

        self.empty_state_label.setVisible(not has_warning)

    def update_item(self, key: str, value: int):
        self.set_data({key: value})

    @staticmethod
    def mock_data() -> Dict[str, int]:
        return {
            "pending_analysis": 18,
            "alerts": 3,
            "pending_recommend": 7,
            "unconfirmed_recommend": 2,
            "tool_wear_over_threshold": 1,
        }
