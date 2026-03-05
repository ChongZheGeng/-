# coding:utf-8
import math
import random

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import MessageBoxBase, SubtitleLabel, BodyLabel, CheckBox, LineEdit, ComboBox, PrimaryPushButton


class SensorAnalysisWorker(QThread):
    finished = pyqtSignal(list, list, dict)
    error = pyqtSignal(str)

    def __init__(self, use_filter=False, window_size=5, feature="RMS"):
        super().__init__()
        self.use_filter = use_filter
        self.window_size = max(1, window_size)
        self.feature = feature
        self._cancelled = False

    def run(self):
        try:
            raw = [math.sin(i * 0.08) + random.uniform(-0.25, 0.25) for i in range(300)]
            if self._cancelled:
                return

            if self.use_filter:
                processed = []
                for i in range(len(raw)):
                    start = max(0, i - self.window_size + 1)
                    window = raw[start:i + 1]
                    processed.append(sum(window) / len(window))
            else:
                processed = raw[:]

            if self._cancelled:
                return

            feature_value = self._calculate_feature(processed)
            self.finished.emit(raw, processed, {self.feature: feature_value})
        except Exception as e:
            self.error.emit(str(e))

    def _calculate_feature(self, data):
        if not data:
            return 0.0
        if self.feature == "峰值":
            return max(abs(x) for x in data)
        if self.feature == "均值":
            return sum(data) / len(data)
        return math.sqrt(sum(x * x for x in data) / len(data))

    def cancel(self):
        self._cancelled = True


class SensorDataAnalysisDialog(MessageBoxBase):
    def __init__(self, sensor_data=None, parent=None):
        super().__init__(parent)
        self.sensor_data = sensor_data or {}
        self.worker = None

        self.viewLayout.addWidget(SubtitleLabel("传感器数据分析/处理"))

        main_widget = QWidget(self)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        left_panel = QVBoxLayout()
        self.filter_check = CheckBox("启用滤波")
        self.window_edit = LineEdit(self)
        self.window_edit.setPlaceholderText("窗口大小，默认 5")
        self.window_edit.setText("5")

        self.feature_combo = ComboBox(self)
        self.feature_combo.addItems(["RMS", "峰值", "均值"])

        self.run_button = PrimaryPushButton("开始分析")
        self.run_button.clicked.connect(self.run_analysis)

        self.meta_label = BodyLabel(self._build_meta_text())
        self.meta_label.setWordWrap(True)

        left_panel.addWidget(self.meta_label)
        left_panel.addWidget(self.filter_check)
        left_panel.addWidget(BodyLabel("窗口大小"))
        left_panel.addWidget(self.window_edit)
        left_panel.addWidget(BodyLabel("特征选择"))
        left_panel.addWidget(self.feature_combo)
        left_panel.addWidget(self.run_button)
        left_panel.addStretch(1)

        right_panel = QVBoxLayout()
        self.raw_chart = BodyLabel("原始波形")
        self.raw_chart.setMinimumSize(460, 180)
        self.raw_chart.setAlignment(Qt.AlignCenter)

        self.processed_chart = BodyLabel("处理后结果")
        self.processed_chart.setMinimumSize(460, 180)
        self.processed_chart.setAlignment(Qt.AlignCenter)

        self.feature_label = BodyLabel("特征值：-")

        right_panel.addWidget(BodyLabel("原始波形"))
        right_panel.addWidget(self.raw_chart)
        right_panel.addWidget(BodyLabel("处理后波形"))
        right_panel.addWidget(self.processed_chart)
        right_panel.addWidget(self.feature_label)

        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 2)

        self.viewLayout.addWidget(main_widget)

        self.yesButton.setText("关闭")
        self.cancelButton.hide()

    def _build_meta_text(self):
        return (
            f"记录ID: {self.sensor_data.get('id', '-')}, "
            f"文件: {self.sensor_data.get('file_url', 'N/A')}\n"
            f"TODO: 后续在此接入真实波形下载与解析逻辑。"
        )

    def run_analysis(self):
        try:
            window_size = int(self.window_edit.text().strip() or "5")
        except ValueError:
            window_size = 5
            self.window_edit.setText("5")

        self.run_button.setEnabled(False)
        self.feature_label.setText("分析中...")

        self.worker = SensorAnalysisWorker(
            use_filter=self.filter_check.isChecked(),
            window_size=window_size,
            feature=self.feature_combo.currentText(),
        )
        self.worker.finished.connect(self.on_analysis_finished)
        self.worker.error.connect(self.on_analysis_error)
        self.worker.start()

    def on_analysis_finished(self, raw, processed, feature_result):
        self.run_button.setEnabled(True)
        self.raw_chart.setPixmap(self._create_wave_pixmap(raw, QColor("#4C8DFF")))
        self.processed_chart.setPixmap(self._create_wave_pixmap(processed, QColor("#00BFA5")))
        key, value = list(feature_result.items())[0]
        self.feature_label.setText(f"特征值（{key}）：{value:.4f}")

    def on_analysis_error(self, error):
        self.run_button.setEnabled(True)
        self.feature_label.setText(f"分析失败: {error}")

    def _create_wave_pixmap(self, data, color):
        width, height = 460, 180
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor("#1E1E1E"))

        if not data:
            return pixmap

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(color, 2))

        min_v, max_v = min(data), max(data)
        span = (max_v - min_v) or 1

        points = []
        for i, value in enumerate(data):
            x = int(i * (width - 10) / max(1, len(data) - 1)) + 5
            y = int((1 - (value - min_v) / span) * (height - 10)) + 5
            points.append((x, y))

        for i in range(1, len(points)):
            painter.drawLine(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1])

        painter.end()
        return pixmap

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
        super().closeEvent(event)
