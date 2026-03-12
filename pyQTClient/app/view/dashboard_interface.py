# coding:utf-8
import logging
from datetime import datetime

from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QSizePolicy,
)

from qfluentwidgets import (
    CardWidget,
    SubtitleLabel,
    BodyLabel,
    StrongBodyLabel,
    IconWidget,
    FluentIcon as FIF,
    ProgressBar,
    TitleLabel,
    CaptionLabel,
    PushButton,
    PrimaryPushButton,
    setFont,
)

from .nav_interface import NavInterface
from ..api.data_manager import data_manager
from .components.parameter_recommend_overview_component import (
    ParameterRecommendOverviewWidget,
    MOCK_RECOMMENDATION_RECORDS,
)
from .components.recent_activity_timeline_component import RecentActivityTimelineCard

logger = logging.getLogger(__name__)


class ShadowCard(CardWidget):
    """带统一阴影效果的基础卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apply_shadow()

    def _apply_shadow(self):
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setBlurRadius(14)
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)


class StatCard(ShadowCard):
    """指标统计卡"""

    def __init__(self, title, value, icon, color="#0078d4", suffix="", parent=None):
        super().__init__(parent)
        self.suffix = suffix
        self.color = color
        self.setMinimumHeight(128)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        top = QHBoxLayout()
        icon_widget = IconWidget(icon, self)
        icon_widget.setFixedSize(22, 22)
        icon_widget.setStyleSheet(f"color:{color};")

        title_label = BodyLabel(title)
        title_label.setStyleSheet("color:#666;font-size:13px;")

        top.addWidget(icon_widget)
        top.addWidget(title_label)
        top.addStretch()
        layout.addLayout(top)

        self.value_label = TitleLabel("0")
        self.value_label.setStyleSheet(f"color:{color};font-weight:700;")
        setFont(self.value_label, 28)
        layout.addWidget(self.value_label)

        self.tip_label = CaptionLabel("较昨日 +0.0%")
        self.tip_label.setStyleSheet("color:#8a8a8a;")
        layout.addWidget(self.tip_label)

        self.update_value(value)

    def update_value(self, value, trend_text=None):
        text = f"{value}{self.suffix}" if self.suffix else str(value)
        self.value_label.setText(text)
        if trend_text:
            self.tip_label.setText(trend_text)


class StatusDistributionCard(ShadowCard):
    """任务状态分布"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        self._build_title(layout, FIF.CALENDAR, "任务状态分布")

        self.status_items = {}
        configs = [
            ("planned", "计划中", "#0078d4"),
            ("in_progress", "进行中", "#107c10"),
            ("completed", "已完成", "#0a805e"),
            ("paused", "已暂停", "#ffaa44"),
            ("aborted", "已中止", "#d13438"),
        ]

        for key, text, color in configs:
            row = QHBoxLayout()
            dot = QFrame()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(f"background:{color};border-radius:5px;")

            label = BodyLabel(text)
            value = StrongBodyLabel("0")
            value.setStyleSheet(f"color:{color};")

            bar = ProgressBar(self)
            bar.setFixedHeight(6)
            bar.setValue(0)

            row.addWidget(dot)
            row.addWidget(label)
            row.addStretch()
            row.addWidget(value)

            layout.addLayout(row)
            layout.addWidget(bar)

            self.status_items[key] = (value, bar)

    def _build_title(self, layout, icon, text):
        title = QHBoxLayout()
        iw = IconWidget(icon, self)
        iw.setFixedSize(20, 20)
        label = StrongBodyLabel(text)
        setFont(label, 15)
        title.addWidget(iw)
        title.addWidget(label)
        title.addStretch()
        layout.addLayout(title)

    def update_status_counts(self, status_counts):
        total = sum(status_counts.values()) or 1
        for key, (value_label, progress) in self.status_items.items():
            count = status_counts.get(key, 0)
            value_label.setText(str(count))
            progress.setValue(int(count / total * 100))


class AnalysisOverviewCard(ShadowCard):
    """通用分析概览卡片（支持 mock）"""

    def __init__(self, title, icon, color, metrics, parent=None):
        super().__init__(parent)
        self.metrics = metrics
        self.bars = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        top = QHBoxLayout()
        iw = IconWidget(icon, self)
        iw.setFixedSize(20, 20)
        iw.setStyleSheet(f"color:{color};")
        label = StrongBodyLabel(title)
        setFont(label, 15)
        top.addWidget(iw)
        top.addWidget(label)
        top.addStretch()
        layout.addLayout(top)

        for item in metrics:
            row = QHBoxLayout()
            name = BodyLabel(item["name"])
            value = StrongBodyLabel("0")
            value.setStyleSheet(f"color:{color};")
            row.addWidget(name)
            row.addStretch()
            row.addWidget(value)
            layout.addLayout(row)

            bar = ProgressBar(self)
            bar.setFixedHeight(6)
            bar.setValue(0)
            layout.addWidget(bar)
            self.bars[item["key"]] = (value, bar)

    def update_metrics(self, payload):
        for key, (value_label, bar) in self.bars.items():
            info = payload.get(key, {})
            value_label.setText(str(info.get("value", "0")))
            bar.setValue(int(info.get("ratio", 0)))


class QuickActionsCard(ShadowCard):
    """快捷操作区"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title = StrongBodyLabel("快捷操作区")
        setFont(title, 15)
        layout.addWidget(title)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_new_task = PrimaryPushButton("新建任务")
        self.btn_upload = PushButton("上传传感器数据")
        self.btn_analyze = PushButton("开始分析")
        self.btn_recommend = PushButton("参数推荐")
        self.btn_history = PushButton("查看历史记录")

        for btn in [
            self.btn_new_task,
            self.btn_upload,
            self.btn_analyze,
            self.btn_recommend,
            self.btn_history,
        ]:
            btn.setMinimumHeight(36)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)


class DashboardInterface(NavInterface):
    """复合材料加工决策驾驶舱主页"""

    recommendationTaskRequested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("DashboardInterface")
        self.active_workers = []

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(32, 24, 32, 24)
        self.main_layout.setSpacing(18)

        self._build_header()
        self._build_stat_cards()
        self._build_analysis_overview()
        self._build_status_and_activity()
        self._build_recommendation_overview()
        self._build_quick_actions()
        self.main_layout.addStretch()

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)

    def _build_header(self):
        title = SubtitleLabel("系统概览 · 复合材料加工决策驾驶舱")
        setFont(title, 24)
        subtitle = CaptionLabel("面向项目答辩展示：融合任务、传感器、推荐闭环指标")
        subtitle.setStyleSheet("color:#6f6f6f;")
        self.main_layout.addWidget(title)
        self.main_layout.addWidget(subtitle)

    def _build_stat_cards(self):
        stat_grid = QGridLayout()
        stat_grid.setSpacing(14)

        self.stat_cards = {
            "users": StatCard("总用户数", "0", FIF.PEOPLE, "#0078d4"),
            "tasks": StatCard("总任务数", "0", FIF.CALENDAR, "#107c10"),
            "pending": StatCard("待处理任务", "0", FIF.DATE_TIME, "#ffaa44"),
            "sensor": StatCard("传感器数据", "0", FIF.IOT, "#8764b8"),
            "pending_analysis": StatCard("待分析数据数", "0", FIF.ALIGNMENT, "#008575"),
            "alerts": StatCard("异常预警数", "0", FIF.WARNING, "#d13438"),
            "recommend_today": StatCard("今日推荐次数", "0", FIF.ROBOT, "#5c2d91"),
            "adoption": StatCard("推荐采纳率", "0", FIF.ACCEPT_MEDIUM, "#0f7b0f", "%"),
        }

        keys = list(self.stat_cards.keys())
        for idx, key in enumerate(keys):
            row, col = divmod(idx, 4)
            stat_grid.addWidget(self.stat_cards[key], row, col)

        self.main_layout.addLayout(stat_grid)

    def _build_analysis_overview(self):
        row = QHBoxLayout()
        row.setSpacing(14)

        sensor_metrics = [
            {"key": "coverage", "name": "数据覆盖率"},
            {"key": "quality", "name": "有效信号占比"},
            {"key": "alerts", "name": "异常定位完成率"},
        ]
        rec_metrics = [
            {"key": "confidence", "name": "最近推荐置信度"},
            {"key": "hit_rate", "name": "历史命中率"},
            {"key": "closed_loop", "name": "闭环验证率"},
        ]

        self.sensor_overview = AnalysisOverviewCard("传感器分析概览", FIF.SPEED_HIGH, "#0078d4", sensor_metrics)
        self.recommend_overview = AnalysisOverviewCard("参数推荐概览", FIF.ROBOT, "#5c2d91", rec_metrics)

        row.addWidget(self.sensor_overview)
        row.addWidget(self.recommend_overview)
        self.main_layout.addLayout(row)

    def _build_status_and_activity(self):
        row = QHBoxLayout()
        row.setSpacing(14)

        self.task_status_card = StatusDistributionCard()
        self.activity_card = RecentActivityTimelineCard()

        row.addWidget(self.task_status_card, 3)
        row.addWidget(self.activity_card, 2)
        self.main_layout.addLayout(row)


    def _build_recommendation_overview(self):
        self.recommendation_overview_widget = ParameterRecommendOverviewWidget(self)
        self.recommendation_overview_widget.recordActivated.connect(self.recommendationTaskRequested.emit)
        self.main_layout.addWidget(self.recommendation_overview_widget)

    def _build_quick_actions(self):
        self.quick_actions_card = QuickActionsCard()
        self.main_layout.addWidget(self.quick_actions_card)

    def _mock_dashboard_payload(self):
        """后端未完全就绪时用于展示的数据"""
        now = datetime.now().strftime("%Y-%m-%d")
        return {
            "pending_analysis": 24,
            "alerts": 6,
            "recommend_today": 13,
            "adoption": 78.6,
            "sensor_overview": {
                "coverage": {"value": "92%", "ratio": 92},
                "quality": {"value": "87%", "ratio": 87},
                "alerts": {"value": "81%", "ratio": 81},
            },
            "recommend_overview": {
                "confidence": {"value": "0.86", "ratio": 86},
                "hit_rate": {"value": "74%", "ratio": 74},
                "closed_loop": {"value": "68%", "ratio": 68},
            },
            "recommendation_records": MOCK_RECOMMENDATION_RECORDS,
            "activities": {
                "task": [
                    {
                        "title": "任务 TK-105 完成参数回写",
                        "description": "工艺卡同步至任务看板，等待归档。",
                        "time": now,
                    },
                    {
                        "title": "任务 TK-108 切换进行中",
                        "description": "现场班组已确认并开始执行。",
                        "time": now,
                    },
                ],
                "analysis": [
                    {
                        "title": "批次 B-302 触发振动异常预警",
                        "description": "异常点位已自动标注，等待复核。",
                        "time": now,
                    },
                    {
                        "title": "传感器 S-22 完成清洗",
                        "description": "有效信号占比提升至 87%。",
                        "time": now,
                    },
                ],
                "recommendation": [
                    {
                        "title": "系统生成新推荐方案 R-018",
                        "description": "建议调整进给速率 +6%，置信度 0.86。",
                        "time": now,
                    },
                    {
                        "title": "推荐方案 R-013 被采纳",
                        "description": "已进入闭环验证阶段。",
                        "time": now,
                    },
                ],
            },
        }

    def refresh_data(self):
        try:
            self.cancel_active_workers()

            worker_users = data_manager.get_data_async(
                data_type="users",
                success_callback=self.on_users_data_received,
                error_callback=self.on_api_error,
            )
            if worker_users:
                self.active_workers.append(worker_users)

            worker_tasks = data_manager.get_data_async(
                data_type="processing_tasks",
                success_callback=self.on_tasks_data_received,
                error_callback=self.on_api_error,
            )
            if worker_tasks:
                self.active_workers.append(worker_tasks)

            worker_sensor = data_manager.get_data_async(
                data_type="sensor_data",
                success_callback=self.on_sensor_data_received,
                error_callback=self.on_api_error,
            )
            if worker_sensor:
                self.active_workers.append(worker_sensor)

            self.apply_mock_data()
        except Exception as e:
            logger.error(f"看板刷新失败: {e}")
            self.apply_mock_data()

    def apply_mock_data(self):
        payload = self._mock_dashboard_payload()
        self.stat_cards["pending_analysis"].update_value(payload["pending_analysis"], "来自最近24小时")
        self.stat_cards["alerts"].update_value(payload["alerts"], "需人工复核")
        self.stat_cards["recommend_today"].update_value(payload["recommend_today"], "较昨日 +18%")
        self.stat_cards["adoption"].update_value(payload["adoption"], "目标值 ≥ 75%")

        self.sensor_overview.update_metrics(payload["sensor_overview"])
        self.recommend_overview.update_metrics(payload["recommend_overview"])
        self.activity_card.update_activities(payload["activities"])
        self.recommendation_overview_widget.set_records(payload.get("recommendation_records", []))

    def on_users_data_received(self, users_data):
        if users_data and "count" in users_data:
            self.stat_cards["users"].update_value(users_data["count"])

    def on_tasks_data_received(self, tasks_data):
        if not tasks_data:
            return

        total_tasks = tasks_data.get("count", 0)
        self.stat_cards["tasks"].update_value(total_tasks)

        tasks_list = tasks_data.get("results", [])
        status_counts = {}
        pending = 0
        for task in tasks_list:
            status = task.get("status", "planned")
            status_counts[status] = status_counts.get(status, 0) + 1
            if status in ["planned", "in_progress"]:
                pending += 1

        self.stat_cards["pending"].update_value(pending)
        self.task_status_card.update_status_counts(status_counts)

        if tasks_list:
            self.activity_card.update_activities(self.generate_recent_activities(tasks_data))

    def on_sensor_data_received(self, sensor_data):
        if sensor_data and "count" in sensor_data:
            total_sensor = sensor_data["count"]
            self.stat_cards["sensor"].update_value(total_sensor)

            pending_analysis = min(max(int(total_sensor * 0.12), 8), 200)
            self.stat_cards["pending_analysis"].update_value(pending_analysis, "依据待处理队列估算")

    def on_api_error(self, error_message):
        logger.warning(f"看板部分数据加载失败: {error_message}")

    def generate_recent_activities(self, tasks_data):
        activities = {"task": [], "analysis": [], "recommendation": []}
        if tasks_data and "results" in tasks_data:
            tasks = sorted(tasks_data["results"], key=lambda x: x.get("updated_at", ""), reverse=True)
            for task in tasks[:10]:
                task_code = task.get("task_code", "N/A")
                status_text = task.get("status_display", "状态更新")
                activities["task"].append(
                    {
                        "title": f"任务 {task_code} 状态更新",
                        "description": f"当前状态：{status_text}",
                        "time": task.get("updated_at", "")[:10],
                    }
                )
        return activities

    def start_refresh_timer(self):
        if not self.refresh_timer.isActive():
            self.refresh_timer.start(30000)

    def stop_refresh_timer(self):
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        self.cancel_active_workers()

    def cancel_active_workers(self):
        for worker in self.active_workers:
            try:
                if hasattr(worker, "cancel"):
                    worker.cancel()
                if worker.isRunning():
                    worker.quit()
                    worker.wait(1000)
            except Exception as e:
                logger.warning(f"取消异步任务失败: {e}")
        self.active_workers.clear()

    def closeEvent(self, event):
        self.stop_refresh_timer()
        super().closeEvent(event)

    def __del__(self):
        try:
            self.stop_refresh_timer()
        except Exception:
            pass

    def on_activated(self):
        self.refresh_data()

    def on_deactivated(self):
        self.cancel_active_workers()
