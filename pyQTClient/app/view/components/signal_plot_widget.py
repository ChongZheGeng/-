# coding:utf-8
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QToolButton, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel


class _SignalCanvas(QWidget):
    """轻量曲线绘制画布，支持滚轮缩放 + 视图重置。"""

    viewChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setMinimumHeight(220)
        self._x_data = []
        self._y_data = []
        self._view_range = (0, 0)
        self._full_range = (0, 0)
        self._line_color = QColor("#4C8DFF")

    def set_data(self, x_data, y_data, line_color: QColor):
        self._x_data = [float(v) for v in x_data]
        self._y_data = [float(v) for v in y_data]
        self._line_color = line_color

        if len(self._x_data) > 0:
            self._full_range = (0, len(self._x_data) - 1)
            self._view_range = self._full_range
        else:
            self._full_range = (0, 0)
            self._view_range = (0, 0)

        self.update()
        self.viewChanged.emit()

    def clear(self):
        self._x_data = []
        self._y_data = []
        self._full_range = (0, 0)
        self._view_range = (0, 0)
        self.update()
        self.viewChanged.emit()

    def reset_view(self):
        self._view_range = self._full_range
        self.update()
        self.viewChanged.emit()

    def zoom_in(self):
        self._zoom(0.7)

    def zoom_out(self):
        self._zoom(1.3)

    def _zoom(self, factor: float):
        if len(self._x_data) < 2:
            return

        left, right = self._view_range
        center = (left + right) / 2
        span = max((right - left + 1) * factor, 20)
        span = min(span, len(self._x_data))

        new_left = int(max(center - span / 2, 0))
        new_right = int(min(new_left + span - 1, len(self._x_data) - 1))

        if new_right - new_left < 1:
            return

        self._view_range = (new_left, new_right)
        self.update()
        self.viewChanged.emit()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(12, 12, -12, -12)
        painter.setPen(QPen(QColor(120, 120, 120, 80), 1))
        painter.drawRoundedRect(rect, 6, 6)

        if len(self._x_data) == 0:
            painter.setPen(QColor("#8A8A8A"))
            painter.drawText(rect, Qt.AlignCenter, "暂无数据")
            return

        left, right = self._view_range
        segment_x = self._x_data[left:right + 1]
        segment_y = self._y_data[left:right + 1]

        if len(segment_x) < 2:
            return

        x_min, x_max = segment_x[0], segment_x[-1]
        y_min, y_max = min(segment_y), max(segment_y)
        if abs(y_max - y_min) < 1e-8:
            y_max = y_min + 1.0

        plot_rect = QRectF(rect.adjusted(14, 14, -14, -24))

        path = QPainterPath()
        for idx, (x_val, y_val) in enumerate(zip(segment_x, segment_y)):
            px = plot_rect.left() + (x_val - x_min) / (x_max - x_min) * plot_rect.width()
            py = plot_rect.bottom() - (y_val - y_min) / (y_max - y_min) * plot_rect.height()
            if idx == 0:
                path.moveTo(px, py)
            else:
                path.lineTo(px, py)

        painter.setPen(QPen(self._line_color, 1.5))
        painter.drawPath(path)

        painter.setPen(QColor("#8A8A8A"))
        painter.drawText(rect.adjusted(8, 0, -8, -2), Qt.AlignBottom | Qt.AlignLeft,
                         f"样本范围: {left} - {right}")


class SignalPlotWidget(QFrame):
    """信号波形组件：标题 + 交互按钮 + 曲线画布。"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent=parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "QFrame { border: 1px solid rgba(120, 120, 120, 0.45); border-radius: 8px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        self.title_label = BodyLabel(title)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)

        self.zoom_out_btn = QToolButton(self)
        self.zoom_out_btn.setText("-")
        self.zoom_in_btn = QToolButton(self)
        self.zoom_in_btn.setText("+")
        self.reset_btn = QToolButton(self)
        self.reset_btn.setText("重置视图")

        header_layout.addWidget(self.zoom_out_btn)
        header_layout.addWidget(self.zoom_in_btn)
        header_layout.addWidget(self.reset_btn)

        self.canvas = _SignalCanvas(self)

        layout.addLayout(header_layout)
        layout.addWidget(self.canvas, 1)

        self.zoom_in_btn.clicked.connect(self.canvas.zoom_in)
        self.zoom_out_btn.clicked.connect(self.canvas.zoom_out)
        self.reset_btn.clicked.connect(self.canvas.reset_view)

    def set_signal_data(self, x_data, y_data, color: str = "#4C8DFF"):
        self.canvas.set_data(x_data, y_data, QColor(color))

    def clear(self):
        self.canvas.clear()

    def reset_view(self):
        self.canvas.reset_view()
