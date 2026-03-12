# coding:utf-8
from collections import Counter

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel


class _ScatterCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.samples = []
        self.recommend = None
        self.setMinimumHeight(230)

    def set_data(self, samples, recommend=None):
        self.samples = samples or []
        self.recommend = recommend
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(14, 14, -14, -14)
        painter.setPen(QPen(QColor(120, 120, 120, 100), 1))
        painter.drawRoundedRect(rect, 6, 6)

        if not self.samples:
            painter.setPen(QColor("#8A8A8A"))
            painter.drawText(rect, Qt.AlignCenter, "暂无散点数据")
            return

        plot = QRectF(rect.adjusted(20, 20, -20, -28))
        ns = [s["n"] for s in self.samples]
        fzs = [s["fz"] for s in self.samples]
        n_min, n_max = min(ns), max(ns)
        fz_min, fz_max = min(fzs), max(fzs)
        colors = {"low": QColor("#47c97f"), "medium": QColor("#f5a623"), "high": QColor("#eb5a56")}

        def to_px(nv, fzv):
            x = plot.left() + ((nv - n_min) / max(1e-6, (n_max - n_min))) * plot.width()
            y = plot.bottom() - ((fzv - fz_min) / max(1e-6, (fz_max - fz_min))) * plot.height()
            return x, y

        for sample in self.samples[:280]:
            color = colors.get(sample.get("damage_level"), QColor("#7d7d7d"))
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            x, y = to_px(sample["n"], sample["fz"])
            painter.drawEllipse(int(x), int(y), 5, 5)

        if self.recommend:
            x, y = to_px(self.recommend["n"], self.recommend["fz"])
            painter.setPen(QPen(QColor("#4C8DFF"), 2))
            painter.setBrush(QColor(255, 255, 255, 30))
            painter.drawEllipse(int(x) - 6, int(y) - 6, 12, 12)
            painter.drawText(int(x) + 8, int(y) - 8, "推荐点")

        painter.setPen(QColor("#8A8A8A"))
        painter.drawText(rect.adjusted(5, 0, -5, -5), Qt.AlignBottom | Qt.AlignLeft, "n - fz 样本散点")


class _HistogramCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.samples = []
        self.setMinimumHeight(230)

    def set_data(self, samples):
        self.samples = samples or []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(14, 14, -14, -14)
        painter.setPen(QPen(QColor(120, 120, 120, 100), 1))
        painter.drawRoundedRect(rect, 6, 6)

        if not self.samples:
            painter.setPen(QColor("#8A8A8A"))
            painter.drawText(rect, Qt.AlignCenter, "暂无分布数据")
            return

        counter = Counter([s.get("damage_level", "unknown") for s in self.samples])
        levels = ["low", "medium", "high"]
        colors = [QColor("#47c97f"), QColor("#f5a623"), QColor("#eb5a56")]
        max_count = max(counter.get(l, 0) for l in levels) or 1
        plot = QRectF(rect.adjusted(20, 22, -20, -30))

        bar_w = plot.width() / 4
        for idx, level in enumerate(levels):
            count = counter.get(level, 0)
            height = (count / max_count) * plot.height()
            x = plot.left() + (idx + 0.5) * bar_w
            y = plot.bottom() - height
            painter.setBrush(colors[idx])
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(x, y, bar_w * 0.7, height))
            painter.setPen(QColor("#8A8A8A"))
            painter.drawText(QRectF(x, plot.bottom() + 4, bar_w * 0.7, 20), Qt.AlignCenter, level)
            painter.drawText(QRectF(x, y - 20, bar_w * 0.7, 20), Qt.AlignCenter, str(count))

        painter.setPen(QColor("#8A8A8A"))
        painter.drawText(rect.adjusted(5, 0, -5, -5), Qt.AlignBottom | Qt.AlignLeft, "A_damage 等级分布")


class RecommendationChartCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame{border:1px solid rgba(120,120,120,0.45);border-radius:8px;}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.scatter = _ScatterCanvas(self)
        self.hist = _HistogramCanvas(self)

        row.addWidget(self.scatter, 1)
        row.addWidget(self.hist, 1)

        layout.addWidget(BodyLabel("可视化分析（含推荐点高亮）"))
        layout.addLayout(row)

    def update_data(self, samples, recommend):
        self.scatter.set_data(samples, recommend)
        self.hist.set_data(samples)
