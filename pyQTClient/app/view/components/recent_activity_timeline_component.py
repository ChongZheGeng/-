# coding:utf-8
from typing import Dict, List

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QFrame, QWidget

from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    FluentIcon as FIF,
    IconWidget,
    StrongBodyLabel,
    setFont,
)


class RecentActivityTimelineCard(CardWidget):
    """系统概览页最近活动三分类时间线组件"""

    CATEGORY_CONFIG = {
        "task": {
            "title": "最近任务活动",
            "icon": FIF.CALENDAR,
            "dot": "#0078D4",
            "iconColor": "#0078D4",
        },
        "analysis": {
            "title": "最近分析活动",
            "icon": FIF.SPEED_HIGH,
            "dot": "#0A805E",
            "iconColor": "#0A805E",
        },
        "recommendation": {
            "title": "最近推荐活动",
            "icon": FIF.ROBOT,
            "dot": "#8764B8",
            "iconColor": "#8764B8",
        },
    }

    EMPTY_TEXT = "暂无活动记录"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_records = 10
        self._section_layouts: Dict[str, QVBoxLayout] = {}

        container = QVBoxLayout(self)
        container.setContentsMargins(20, 18, 20, 18)
        container.setSpacing(10)

        header = QHBoxLayout()
        header_icon = IconWidget(FIF.HISTORY, self)
        header_icon.setFixedSize(20, 20)
        header_label = StrongBodyLabel("最近活动")
        setFont(header_label, 15)
        header.addWidget(header_icon)
        header.addWidget(header_label)
        header.addStretch()
        container.addLayout(header)

        for key in ["task", "analysis", "recommendation"]:
            container.addLayout(self._build_section(key))

    def _build_section(self, key: str) -> QVBoxLayout:
        config = self.CATEGORY_CONFIG[key]

        section = QVBoxLayout()
        section.setSpacing(6)

        title_row = QHBoxLayout()
        icon = IconWidget(config["icon"], self)
        icon.setFixedSize(16, 16)
        icon.setStyleSheet(f"color:{config['iconColor']};")

        title = BodyLabel(config["title"])
        title.setStyleSheet("color:#606060;font-size:13px;")

        title_row.addWidget(icon)
        title_row.addWidget(title)
        title_row.addStretch()

        section.addLayout(title_row)

        content = QVBoxLayout()
        content.setSpacing(4)
        content.setContentsMargins(6, 0, 0, 0)
        self._section_layouts[key] = content

        section.addLayout(content)
        return section

    def update_activities(self, activities: Dict[str, List[dict]]):
        for key in self.CATEGORY_CONFIG:
            self._render_category(key, activities.get(key, [])[: self.max_records])

    def _render_category(self, key: str, records: List[dict]):
        layout = self._section_layouts[key]
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not records:
            placeholder = CaptionLabel(self.EMPTY_TEXT, self)
            placeholder.setStyleSheet("color:#A0A0A0;")
            layout.addWidget(placeholder)
            return

        dot_color = self.CATEGORY_CONFIG[key]["dot"]

        for record in records:
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(8)

            dot = QFrame(row)
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background:{dot_color};border-radius:4px;")

            text_layout = QVBoxLayout()
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(0)

            title = BodyLabel(record.get("title", "未命名活动"), row)
            title.setStyleSheet("color:#303030;")
            desc = CaptionLabel(record.get("description", ""), row)
            desc.setStyleSheet("color:#7A7A7A;")

            text_layout.addWidget(title)
            text_layout.addWidget(desc)

            time_label = CaptionLabel(record.get("time", "--"), row)
            time_label.setStyleSheet("color:#9A9A9A;")

            row_layout.addWidget(dot)
            row_layout.addLayout(text_layout, 1)
            row_layout.addWidget(time_label)

            layout.addWidget(row)
