# coding:utf-8
import logging
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
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
from .components.parameter_recommend_overview_component import (
    ParameterRecommendOverviewWidget,
)
from ..services.system_overview_linkage_manager import system_overview_linkage_manager
from .components.recent_activity_timeline_component import RecentActivityTimelineCard
from .components.warning_todo_center_widget import WarningTodoCenterWidget

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

    clicked = pyqtSignal()

    def __init__(self, title, value, icon, color="#0078d4", suffix="", parent=None):
        super().__init__(parent)
        self.suffix = suffix
        self.color = color
        self.setCursor(Qt.PointingHandCursor)
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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


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
    warningTodoNavigateRequested = pyqtSignal(str)
    statCardNavigateRequested = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("DashboardInterface")
        self.overview_manager = system_overview_linkage_manager
        self.latest_payload = {}

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(32, 24, 32, 24)
        self.main_layout.setSpacing(16)

        self._build_header()
        self._build_stat_cards()
        self._build_data_chain_view()
        self._build_warning_todo_center()
        self._build_analysis_overview()
        self._build_trend_and_summary()
        self._build_status_and_activity()
        self._build_recommendation_overview()
        self._build_quick_actions()
        self.main_layout.addStretch()

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)

    def _build_header(self):
        title = SubtitleLabel("系统概览 · 复合材料加工智能决策驾驶舱")
        setFont(title, 24)
        subtitle = CaptionLabel("答辩展示视角：数据库入库 → 传感器分析 → 参数推荐 → 闭环验证")
        subtitle.setStyleSheet("color:#6f6f6f;")

        self.badge_chain = PushButton("数据链路完整")
        self.badge_chain.setEnabled(False)
        self.badge_chain.setStyleSheet("background:#e8f8ee;color:#1f7a3f;border:1px solid #cdeed6;")
        self.badge_ai = PushButton("智能推荐引擎在线")
        self.badge_ai.setEnabled(False)
        self.badge_ai.setStyleSheet("background:#eef5ff;color:#3159c9;border:1px solid #dbe7ff;")

        title_row = QHBoxLayout()
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.addWidget(title)
        text_col.addWidget(subtitle)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(8)
        badge_row.addWidget(self.badge_chain)
        badge_row.addWidget(self.badge_ai)
        badge_row.addStretch()
        text_col.addLayout(badge_row)

        title_row.addLayout(text_col)
        title_row.addStretch()
        self.main_layout.addLayout(title_row)

    def _build_stat_cards(self):
        stat_grid = QGridLayout()
        stat_grid.setSpacing(12)

        self.stat_cards = {
            "users": StatCard("总用户数", "0", FIF.PEOPLE, "#0078d4"),
            "tasks": StatCard("总任务数", "0", FIF.CALENDAR, "#107c10"),
            "pending_recommend": StatCard("待推荐任务数", "0", FIF.DATE_TIME, "#ffaa44"),
            "sensor": StatCard("传感器数据", "0", FIF.IOT, "#8764b8"),
            "pending_analysis": StatCard("待分析数据数", "0", FIF.ALIGNMENT, "#008575"),
            "alerts": StatCard("异常预警数", "0", FIF.WARNING, "#d13438"),
            "recommend_today": StatCard("今日推荐次数", "0", FIF.ROBOT, "#5c2d91"),
            "adoption": StatCard("推荐采纳率", "0", FIF.ACCEPT_MEDIUM, "#0f7b0f", "%"),
        }

        self.stat_cards["pending_recommend"].clicked.connect(
            lambda: self._emit_stat_navigation("pending_recommend")
        )
        self.stat_cards["pending_analysis"].clicked.connect(
            lambda: self._emit_stat_navigation("pending_analysis")
        )

        keys = list(self.stat_cards.keys())
        for idx, key in enumerate(keys):
            row, col = divmod(idx, 4)
            stat_grid.addWidget(self.stat_cards[key], row, col)

        self.main_layout.addLayout(stat_grid)

    def _build_data_chain_view(self):
        card = ShadowCard(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        title = StrongBodyLabel("智能链路总览")
        setFont(title, 15)
        desc = CaptionLabel("突出数据库管理、传感器分析与参数推荐的一体化流程")
        desc.setStyleSheet("color:#6f6f6f;")
        layout.addWidget(title)
        layout.addWidget(desc)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.chain_items = {}
        configs = [
            ("db", FIF.DOCUMENT, "数据库接入", "任务与传感数据同步入库", "#1f7a3f"),
            ("analysis", FIF.SPEED_HIGH, "传感器分析", "特征提取与异常定位", "#0078d4"),
            ("recommend", FIF.ROBOT, "参数推荐", "模型推荐与闭环验证", "#5c2d91"),
        ]

        for index, (key, icon, name, hint, color) in enumerate(configs):
            block = QFrame(card)
            block.setStyleSheet("background:#f7fbf8;border:1px solid #e6efe8;border-radius:10px;")
            block_layout = QVBoxLayout(block)
            block_layout.setContentsMargins(12, 10, 12, 10)
            block_layout.setSpacing(4)

            top = QHBoxLayout()
            iw = IconWidget(icon, block)
            iw.setFixedSize(18, 18)
            iw.setStyleSheet(f"color:{color};")
            name_label = StrongBodyLabel(name)
            name_label.setStyleSheet(f"color:{color};")
            top.addWidget(iw)
            top.addWidget(name_label)
            top.addStretch()

            value = TitleLabel("0")
            setFont(value, 24)
            value.setStyleSheet(f"color:{color};")
            hint_label = CaptionLabel(hint)
            hint_label.setStyleSheet("color:#6f6f6f;")

            progress = ProgressBar(block)
            progress.setValue(0)
            progress.setFixedHeight(5)

            block_layout.addLayout(top)
            block_layout.addWidget(value)
            block_layout.addWidget(hint_label)
            block_layout.addWidget(progress)

            row.addWidget(block, 1)
            if index < len(configs) - 1:
                arrow = CaptionLabel("→")
                arrow.setStyleSheet("color:#8aa198;font-size:20px;font-weight:700;")
                row.addWidget(arrow)

            self.chain_items[key] = {"value": value, "progress": progress}

        layout.addLayout(row)
        self.main_layout.addWidget(card)

    def _build_warning_todo_center(self):
        self.warning_todo_center = WarningTodoCenterWidget(self)
        self.warning_todo_center.itemClicked.connect(self.warningTodoNavigateRequested.emit)
        self.main_layout.addWidget(self.warning_todo_center)

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

    def _build_trend_and_summary(self):
        row = QHBoxLayout()
        row.setSpacing(14)

        self.trend_card = ShadowCard(self)
        trend_layout = QVBoxLayout(self.trend_card)
        trend_layout.setContentsMargins(20, 18, 20, 18)
        trend_layout.setSpacing(10)
        trend_title = StrongBodyLabel("关键指标趋势")
        setFont(trend_title, 15)
        trend_layout.addWidget(trend_title)

        self.trend_items = {}
        for key, label_text, color in [
            ("analysis_quality", "分析有效率", "#0078d4"),
            ("recommend_confidence", "推荐置信度", "#5c2d91"),
            ("closed_loop", "闭环验证率", "#107c10"),
        ]:
            text_row = QHBoxLayout()
            name = BodyLabel(label_text)
            value = StrongBodyLabel("0%")
            value.setStyleSheet(f"color:{color};")
            text_row.addWidget(name)
            text_row.addStretch()
            text_row.addWidget(value)

            bar = ProgressBar(self.trend_card)
            bar.setFixedHeight(7)
            bar.setValue(0)

            trend_layout.addLayout(text_row)
            trend_layout.addWidget(bar)
            self.trend_items[key] = (value, bar)

        self.recommend_summary_card = ShadowCard(self)
        summary_layout = QVBoxLayout(self.recommend_summary_card)
        summary_layout.setContentsMargins(20, 18, 20, 18)
        summary_layout.setSpacing(10)

        summary_title = StrongBodyLabel("推荐摘要与答辩亮点")
        setFont(summary_title, 15)
        self.summary_task = BodyLabel("重点任务：-")
        self.summary_conf = BodyLabel("置信度：-")
        self.summary_effect = BodyLabel("预期效果：-")
        self.summary_warning = CaptionLabel("当前暂无高优先级预警")
        self.summary_warning.setStyleSheet("color:#d18400;background:#fff5db;padding:6px 10px;border-radius:8px;")

        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(self.summary_task)
        summary_layout.addWidget(self.summary_conf)
        summary_layout.addWidget(self.summary_effect)
        summary_layout.addWidget(self.summary_warning)
        summary_layout.addStretch()

        row.addWidget(self.trend_card, 3)
        row.addWidget(self.recommend_summary_card, 2)
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

    def _emit_stat_navigation(self, filter_key: str):
        payload = self.latest_payload.get("filters", {})
        target = payload.get(filter_key, {})
        route = target.get("route", "")
        spec = target.get("spec")
        if route:
            self.statCardNavigateRequested.emit(route, spec)

    def refresh_data(self):
        payload = self.overview_manager.load_dashboard_payload(use_mock=False)
        if not payload:
            payload = self.overview_manager.load_dashboard_payload(use_mock=True)
        self.latest_payload = payload
        self.apply_payload(payload)

    def apply_payload(self, payload):
        payload = payload or {}
        self.stat_cards["users"].update_value(payload.get("users", 0))
        self.stat_cards["tasks"].update_value(payload.get("tasks", 0))
        self.stat_cards["pending_recommend"].update_value(payload.get("pending_recommend", 0), "待进入参数推荐")
        self.stat_cards["sensor"].update_value(payload.get("sensor", 0))
        self.stat_cards["pending_analysis"].update_value(payload.get("pending_analysis", 0), "来自传感器待分析队列")
        self.stat_cards["alerts"].update_value(payload.get("alerts", 0), "需人工复核")
        self.stat_cards["recommend_today"].update_value(payload.get("recommend_today", 0), "来自统一推荐记录")
        self.stat_cards["adoption"].update_value(payload.get("adoption", 0), "目标值 ≥ 75%")

        self.warning_todo_center.set_data({
            "pending_analysis": payload.get("pending_analysis", 0),
            "alerts": payload.get("alerts", 0),
            "pending_recommend": payload.get("pending_recommend", 0),
            "unconfirmed_recommend": payload.get("unconfirmed_recommend", 0),
            "tool_wear_over_threshold": payload.get("tool_wear_over_threshold", 0),
        })

        self.task_status_card.update_status_counts(payload.get("task_status_counts", {}))
        self.sensor_overview.update_metrics(payload.get("sensor_overview", {}))
        self.recommend_overview.update_metrics(payload.get("recommend_overview", {}))
        self.activity_card.update_activities(payload.get("activities", {}))
        self.recommendation_overview_widget.set_records(payload.get("recommendation_records", []))

        self._update_chain(payload)
        self._update_trend_and_summary(payload)

    def _update_chain(self, payload):
        tasks = int(payload.get("tasks", 0) or 0)
        sensors = int(payload.get("sensor", 0) or 0)
        recommend_today = int(payload.get("recommend_today", 0) or 0)
        pending_analysis = int(payload.get("pending_analysis", 0) or 0)

        db_ratio = min(100, int(tasks * 4)) if tasks else 0
        analysis_ratio = max(0, min(100, 100 - int(pending_analysis * 100 / max(1, sensors))))
        rec_ratio = min(100, int(float(payload.get("adoption", 0) or 0)))

        self.chain_items["db"]["value"].setText(str(tasks))
        self.chain_items["db"]["progress"].setValue(db_ratio)
        self.chain_items["analysis"]["value"].setText(str(sensors))
        self.chain_items["analysis"]["progress"].setValue(analysis_ratio)
        self.chain_items["recommend"]["value"].setText(str(recommend_today))
        self.chain_items["recommend"]["progress"].setValue(rec_ratio)

    def _update_trend_and_summary(self, payload):
        sensor_overview = payload.get("sensor_overview", {})
        recommend_overview = payload.get("recommend_overview", {})

        quality_ratio = int((sensor_overview.get("quality") or {}).get("ratio", 0))
        conf_ratio = int((recommend_overview.get("confidence") or {}).get("ratio", 0))
        closed_ratio = int((recommend_overview.get("closed_loop") or {}).get("ratio", 0))

        self.trend_items["analysis_quality"][0].setText(f"{quality_ratio}%")
        self.trend_items["analysis_quality"][1].setValue(quality_ratio)
        self.trend_items["recommend_confidence"][0].setText(f"{conf_ratio}%")
        self.trend_items["recommend_confidence"][1].setValue(conf_ratio)
        self.trend_items["closed_loop"][0].setText(f"{closed_ratio}%")
        self.trend_items["closed_loop"][1].setValue(closed_ratio)

        records = payload.get("recommendation_records", [])
        top_record = records[0] if records else {}
        task_code = top_record.get("task_code", "暂无")
        confidence = float(top_record.get("confidence", 0) or 0)
        target_level = top_record.get("target_damage_level", "-")
        self.summary_task.setText(f"重点任务：{task_code}")
        self.summary_conf.setText(f"置信度：{confidence * 100:.1f}%  | 目标损伤等级：{target_level}")
        self.summary_effect.setText(
            f"预期效果：采纳率 {payload.get('adoption', 0)}% · 今日新增推荐 {payload.get('recommend_today', 0)} 次"
        )

        alerts = int(payload.get("alerts", 0) or 0)
        if alerts > 0:
            self.summary_warning.setText(f"预警提示：当前存在 {alerts} 条异常事件，建议优先复核传感器异常任务。")
        else:
            self.summary_warning.setText("当前暂无高优先级预警")

    def start_refresh_timer(self):
        if not self.refresh_timer.isActive():
            self.refresh_timer.start(30000)

    def stop_refresh_timer(self):
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()

    def cancel_active_workers(self):
        return

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
        pass
