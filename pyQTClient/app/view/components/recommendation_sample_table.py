# coding:utf-8
from PyQt5.QtWidgets import QTableWidgetItem, QHeaderView
from qfluentwidgets import TableWidget


class RecommendationSampleTable(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "样本编号", "转速 n", "每齿进给 fz", "A_damage", "损伤等级", "相似度/说明"
        ])
        self.setBorderVisible(True)
        self.setBorderRadius(8)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)

    def update_samples(self, samples):
        self.setRowCount(len(samples))
        for row, sample in enumerate(samples):
            values = [
                sample.get("sample_id", "--"),
                sample.get("n", "--"),
                sample.get("fz", "--"),
                sample.get("A_damage", "--"),
                sample.get("damage_level", "--"),
                f"{sample.get('similarity', '--')} / {sample.get('reference', '--')}",
            ]
            for col, value in enumerate(values):
                self.setItem(row, col, QTableWidgetItem(str(value)))
