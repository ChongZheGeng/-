# coding:utf-8
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional

from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt5.QtGui import QColor, QPainter, QPen, QPainterPath, QFont
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget, QGridLayout

from qfluentwidgets import BodyLabel, CaptionLabel, PrimaryPushButton, StrongBodyLabel, isDarkTheme


class TrendChartWidget(QWidget):
    """Simple 7-day trend line chart"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels = []
        self._values = []
        self.setMinimumHeight(180)

    def setData(self, labels, values):
        self._labels = labels
        self._values = values
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._values:
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        margin = 28
        rect = self.rect().adjusted(margin, 12, -12, -34)
        min_v = min(self._values)
        max_v = max(self._values)
        span = max(max_v - min_v, 1)

        grid_pen = QPen(QColor(40, 40, 40, 35) if not isDarkTheme() else QColor(255, 255, 255, 32))
        painter.setPen(grid_pen)
        for i in range(5):
            y = rect.top() + rect.height() * i / 4
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

        points = []
        count = len(self._values)
        for i, value in enumerate(self._values):
            x = rect.left() + rect.width() * i / max(count - 1, 1)
            y = rect.bottom() - (value - min_v) * rect.height() / span
            points.append(QPointF(x, y))

        area_path = QPainterPath()
        area_path.moveTo(points[0].x(), rect.bottom())
        for p in points:
            area_path.lineTo(p)
        area_path.lineTo(points[-1].x(), rect.bottom())
        area_path.closeSubpath()
        area_color = QColor(66, 133, 244, 45 if not isDarkTheme() else 70)
        painter.fillPath(area_path, area_color)

        line_pen = QPen(QColor(59, 130, 246), 2)
        painter.setPen(line_pen)
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

        dot_color = QColor(37, 99, 235)
        painter.setPen(Qt.NoPen)
        painter.setBrush(dot_color)
        for p in points:
            painter.drawEllipse(p, 3.5, 3.5)

        label_pen = QPen(QColor(80, 80, 80) if not isDarkTheme() else QColor(220, 220, 220))
        painter.setPen(label_pen)
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        for i, label in enumerate(self._labels):
            x = rect.left() + rect.width() * i / max(count - 1, 1)
            painter.drawText(QRectF(x - 18, rect.bottom() + 8, 36, 20), Qt.AlignCenter, label)


class PieChartWidget(QWidget):
    """Simple sensor type ratio chart"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {}
        self.setMinimumHeight(180)

    def setData(self, data: Dict[str, int]):
        self._data = data
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._data:
            return

        total = max(sum(self._data.values()), 1)
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        size = min(self.width() * 0.45, self.height() * 0.8)
        pie_rect = QRectF(16, (self.height() - size) / 2, size, size)

        start_angle = 90 * 16
        palette = [QColor(59, 130, 246), QColor(16, 185, 129), QColor(245, 158, 11), QColor(168, 85, 247)]

        legend_x = pie_rect.right() + 18
        legend_y = pie_rect.top() + 8

        text_pen = QColor(60, 60, 60) if not isDarkTheme() else QColor(220, 220, 220)
        painter.setPen(text_pen)

        for idx, (name, value) in enumerate(self._data.items()):
            color = palette[idx % len(palette)]
            angle_span = int(360 * 16 * value / total)
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawPie(pie_rect, start_angle, -angle_span)
            start_angle -= angle_span

            y = legend_y + idx * 28
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(legend_x, y, 12, 12), 2, 2)
            painter.setPen(text_pen)
            painter.drawText(QRectF(legend_x + 18, y - 2, self.width() - legend_x - 22, 18),
                             Qt.AlignLeft | Qt.AlignVCenter,
                             f"{name}: {value / total * 100:.1f}%")


class StatCard(QFrame):

    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setObjectName('sensorStatCard')
        self.titleLabel = CaptionLabel(title, self)
        self.valueLabel = StrongBodyLabel(value, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.valueLabel)

    def setValue(self, value: str):
        self.valueLabel.setText(value)


class SensorDataOverviewWidget(QFrame):
    openAnalysisRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('sensorDataOverviewWidget')
        self._source_mode = 'mock'
        self._backend_fetcher: Optional[Callable[[], Dict]] = None

        self.titleLabel = StrongBodyLabel('传感器数据分析概览', self)
        self.subtitleLabel = BodyLabel('最近 7 天数据趋势、类型占比与分析摘要', self)
        self.jumpButton = PrimaryPushButton('进入传感器数据分析页面', self)

        self.trendChart = TrendChartWidget(self)
        self.pieChart = PieChartWidget(self)
        self.latestResultLabel = BodyLabel('', self)

        self.pendingCard = StatCard('待分析数据数', '0', self)
        self.doneCard = StatCard('已分析数据数', '0', self)
        self.abnormalCard = StatCard('异常样本数', '0', self)
        self.rateCard = StatCard('分析完成率', '0%', self)

        self.__initLayout()
        self.jumpButton.clicked.connect(self.openAnalysisRequested)
        self.refresh()

    def __initLayout(self):
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(20, 18, 20, 18)
        mainLayout.setSpacing(14)

        mainLayout.addWidget(self.titleLabel)
        mainLayout.addWidget(self.subtitleLabel)

        chartLayout = QHBoxLayout()
        chartLayout.setSpacing(14)

        trendWrapper = QFrame(self)
        trendWrapper.setObjectName('sensorChartCard')
        trendLayout = QVBoxLayout(trendWrapper)
        trendLayout.setContentsMargins(12, 12, 12, 12)
        trendLayout.addWidget(BodyLabel('最近7天数据量趋势', trendWrapper))
        trendLayout.addWidget(self.trendChart)

        pieWrapper = QFrame(self)
        pieWrapper.setObjectName('sensorChartCard')
        pieLayout = QVBoxLayout(pieWrapper)
        pieLayout.setContentsMargins(12, 12, 12, 12)
        pieLayout.addWidget(BodyLabel('传感器类型占比', pieWrapper))
        pieLayout.addWidget(self.pieChart)

        chartLayout.addWidget(trendWrapper, 2)
        chartLayout.addWidget(pieWrapper, 1)
        mainLayout.addLayout(chartLayout)

        statsLayout = QGridLayout()
        statsLayout.setSpacing(10)
        statsLayout.addWidget(self.pendingCard, 0, 0)
        statsLayout.addWidget(self.doneCard, 0, 1)
        statsLayout.addWidget(self.abnormalCard, 1, 0)
        statsLayout.addWidget(self.rateCard, 1, 1)
        mainLayout.addLayout(statsLayout)

        latestFrame = QFrame(self)
        latestFrame.setObjectName('sensorChartCard')
        latestLayout = QHBoxLayout(latestFrame)
        latestLayout.setContentsMargins(12, 10, 12, 10)
        latestLayout.addWidget(BodyLabel('最近一次分析结果：', latestFrame))
        latestLayout.addWidget(self.latestResultLabel, 1)
        mainLayout.addWidget(latestFrame)

        mainLayout.addWidget(self.jumpButton, 0, Qt.AlignRight)

    def setDataMode(self, mode: str, backend_fetcher: Optional[Callable[[], Dict]] = None):
        """mode: mock or backend"""
        self._source_mode = mode
        self._backend_fetcher = backend_fetcher
        self.refresh()

    def refresh(self):
        if self._source_mode == 'backend' and self._backend_fetcher is not None:
            payload = self._backend_fetcher() or self._mockData()
        else:
            payload = self._mockData()

        trend = payload.get('trend', {})
        summary = payload.get('summary', {})
        ratio = payload.get('ratio', {})

        self.trendChart.setData(trend.get('labels', []), trend.get('values', []))
        self.pieChart.setData(ratio)
        self.pendingCard.setValue(str(summary.get('pending', 0)))
        self.doneCard.setValue(str(summary.get('done', 0)))
        self.abnormalCard.setValue(str(summary.get('abnormal', 0)))
        self.rateCard.setValue(f"{summary.get('completion_rate', 0)}%")
        self.latestResultLabel.setText(payload.get('latest_result', '暂无分析结果'))

    def _mockData(self):
        today = datetime.now().date()
        labels = [(today - timedelta(days=6 - i)).strftime('%m-%d') for i in range(7)]
        values = [128, 146, 153, 190, 172, 210, 225]
        return {
            'trend': {'labels': labels, 'values': values},
            'ratio': {'力': 45, '振动': 35, '温度': 20},
            'summary': {'pending': 37, 'done': 318, 'abnormal': 26, 'completion_rate': 89.6},
            'latest_result': '振动异常（轴承疑似磨损）；温度正常；力信号波动过大'
        }
