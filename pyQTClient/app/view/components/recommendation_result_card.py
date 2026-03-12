# coding:utf-8
from PyQt5.QtWidgets import QGridLayout
from qfluentwidgets import BodyLabel, CardWidget, StrongBodyLabel


class RecommendationResultCard(CardWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._fields = {}

        layout = QGridLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        layout.addWidget(StrongBodyLabel(title), 0, 0, 1, 2)
        labels = [
            ("推荐转速 n", "n"),
            ("推荐每齿进给 fz", "fz"),
            ("目标损伤等级", "damage_target"),
            ("估计损伤值", "estimated_damage"),
            ("推荐模式", "mode"),
            ("置信说明", "confidence"),
            ("推荐理由", "reason"),
        ]

        for row, (name, key) in enumerate(labels, start=1):
            layout.addWidget(BodyLabel(name), row, 0)
            value = BodyLabel("--")
            value.setWordWrap(True)
            layout.addWidget(value, row, 1)
            self._fields[key] = value

    def update_data(self, data: dict):
        for key, label in self._fields.items():
            label.setText(str(data.get(key, "--")))
