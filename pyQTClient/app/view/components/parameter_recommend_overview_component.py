# coding:utf-8
from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
)
from qfluentwidgets import CardWidget, StrongBodyLabel, BodyLabel, CaptionLabel, setFont


class SummaryItem(QFrame):
    """顶部统计摘要项"""

    def __init__(self, title, value="-", suffix="", color="#2f2f2f", parent=None):
        super().__init__(parent)
        self.suffix = suffix
        self.setObjectName("SummaryItem")
        self.setStyleSheet(
            """
            #SummaryItem {
                background: #f7f8fa;
                border: 1px solid #eceff3;
                border-radius: 10px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.title_label = CaptionLabel(title, self)
        self.title_label.setStyleSheet("color:#7b7f86;")
        self.value_label = StrongBodyLabel("-", self)
        self.value_label.setStyleSheet(f"color:{color};")
        setFont(self.value_label, 18)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

        self.set_value(value)

    def set_value(self, value):
        self.value_label.setText(f"{value}{self.suffix}" if self.suffix else str(value))


class ParameterRecommendOverviewWidget(CardWidget):
    """参数推荐概览组件（可独立插入首页布局）"""

    recordActivated = pyqtSignal(str)

    HEADERS = ["任务编号", "材料类型", "刀具类型", "推荐转速(rpm)", "推荐进给量(mm/rev)", "推荐置信度", "推荐时间", "是否已采纳"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        title = StrongBodyLabel("参数推荐概览", self)
        setFont(title, 15)
        subtitle = CaptionLabel("点击记录可跳转至参数推荐页并打开对应任务", self)
        subtitle.setStyleSheet("color:#8a8a8a;")

        header_row.addWidget(title)
        header_row.addStretch(1)
        layout.addLayout(header_row)
        layout.addWidget(subtitle)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(10)
        self.today_item = SummaryItem("今日推荐次数", "0", color="#5c2d91")
        self.avg_conf_item = SummaryItem("平均推荐置信度", "0", suffix="%", color="#0f7b0f")
        self.adoption_item = SummaryItem("采纳率", "0", suffix="%", color="#0078d4")
        summary_row.addWidget(self.today_item)
        summary_row.addWidget(self.avg_conf_item)
        summary_row.addWidget(self.adoption_item)
        layout.addLayout(summary_row)

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(220)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellDoubleClicked.connect(self._emit_record_activated)
        layout.addWidget(self.table)

        self.recordActivated.connect(lambda _: None)

    def set_records(self, records):
        self.records = records or []
        self._refresh_summary()
        self._refresh_table()

    def _refresh_summary(self):
        if not self.records:
            self.today_item.set_value(0)
            self.avg_conf_item.set_value(0)
            self.adoption_item.set_value(0)
            return

        today_str = datetime.now().strftime("%Y-%m-%d")
        today_count = 0
        conf_values = []
        adopted_count = 0

        for record in self.records:
            rec_time = str(record.get("recommended_at", ""))
            if rec_time.startswith(today_str):
                today_count += 1

            conf = float(record.get("confidence", 0) or 0)
            conf_values.append(conf)
            if bool(record.get("adopted", False)):
                adopted_count += 1

        avg_conf = (sum(conf_values) / len(conf_values) * 100) if conf_values else 0
        adoption_rate = (adopted_count / len(self.records) * 100) if self.records else 0

        self.today_item.set_value(today_count)
        self.avg_conf_item.set_value(f"{avg_conf:.1f}")
        self.adoption_item.set_value(f"{adoption_rate:.1f}")

    def _refresh_table(self):
        self.table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            data = [
                record.get("task_code", "-"),
                record.get("material_type", "-"),
                record.get("tool_type", "-"),
                str(record.get("recommended_speed", "-")),
                str(record.get("recommended_feed", "-")),
                f"{float(record.get('confidence', 0) or 0) * 100:.1f}%",
                str(record.get("recommended_at", "-")),
                "已采纳" if record.get("adopted", False) else "未采纳",
            ]
            for col, value in enumerate(data):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

    def _emit_record_activated(self, row, _column):
        if 0 <= row < len(self.records):
            task_code = str(self.records[row].get("task_code", "")).strip()
            if task_code:
                self.recordActivated.emit(task_code)


MOCK_RECOMMENDATION_RECORDS = [
    {
        "task_code": "TK-240301-01",
        "material_type": "CFRP",
        "tool_type": "金刚石立铣刀",
        "recommended_speed": 12800,
        "recommended_feed": 0.085,
        "confidence": 0.92,
        "recommended_at": "2026-03-12 09:12:15",
        "adopted": True,
    },
    {
        "task_code": "TK-240301-02",
        "material_type": "GFRP",
        "tool_type": "涂层麻花钻",
        "recommended_speed": 9600,
        "recommended_feed": 0.072,
        "confidence": 0.81,
        "recommended_at": "2026-03-12 10:47:33",
        "adopted": False,
    },
    {
        "task_code": "TK-240229-08",
        "material_type": "AFRP",
        "tool_type": "PCD钻头",
        "recommended_speed": 8400,
        "recommended_feed": 0.061,
        "confidence": 0.88,
        "recommended_at": "2026-03-11 15:05:52",
        "adopted": True,
    },
    {
        "task_code": "TK-240228-11",
        "material_type": "CFRP/铝叠层",
        "tool_type": "DLC涂层立铣刀",
        "recommended_speed": 10200,
        "recommended_feed": 0.079,
        "confidence": 0.84,
        "recommended_at": "2026-03-10 17:26:08",
        "adopted": False,
    },
]
