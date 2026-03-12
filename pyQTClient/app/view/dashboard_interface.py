# coding:utf-8
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGraphicsDropShadowEffect

from qfluentwidgets import (
    CardWidget,
    SubtitleLabel,
    BodyLabel,
    StrongBodyLabel,
    IconWidget,
    FluentIcon as FIF,
    TitleLabel,
    CaptionLabel,
    PushButton,
    setFont,
)

from .nav_interface import NavInterface
from ..api.data_manager import data_manager
import logging

logger = logging.getLogger(__name__)


def get_fluent_icon(icon_names):
    """按优先级安全获取 FluentIcon，避免因版本差异崩溃。"""
    available_names = []
    try:
        members = getattr(FIF, "__members__", None)
        if isinstance(members, dict):
            available_names = list(members.keys())
    except Exception:
        available_names = []

    for name in icon_names:
        icon = getattr(FIF, name, None)
        if icon is not None:
            if name != icon_names[0]:
                logger.warning("[dashboard] icon %s not found, fallback to %s", icon_names[0], name)
            return icon

    if available_names:
        fallback_name = available_names[0]
        logger.warning("[dashboard] icons %s not found, fallback to first available icon %s", icon_names, fallback_name)
        return getattr(FIF, fallback_name)

    logger.warning("[dashboard] icons %s not found and no fallback available, use INFO placeholder", icon_names)
    return getattr(FIF, "INFO", getattr(FIF, "__members__", {}).get(next(iter(getattr(FIF, "__members__", {"": None})), "")))


class CompactStatCard(CardWidget):
    """紧凑统计卡片"""

    def __init__(self, title, value, icon, description="", color="#0078d4", parent=None):
        super().__init__(parent)
        self.setMinimumWidth(170)
        self.setMaximumWidth(220)
        self.setFixedHeight(116)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)

        self.icon_widget = IconWidget(icon, self)
        self.icon_widget.setFixedSize(18, 18)
        self.icon_widget.setStyleSheet(f"color: {color};")

        self.title_label = CaptionLabel(title)
        self.title_label.setStyleSheet("color: #666;")
        setFont(self.title_label, 11)

        top_layout.addWidget(self.icon_widget)
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()

        self.value_label = TitleLabel(str(value))
        self.value_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        setFont(self.value_label, 24)

        self.desc_label = CaptionLabel(description)
        self.desc_label.setStyleSheet("color: #8a8a8a;")
        setFont(self.desc_label, 10)

        layout.addLayout(top_layout)
        layout.addWidget(self.value_label)
        layout.addWidget(self.desc_label)

        self.setShadowEffect()

    def setShadowEffect(self):
        shadowEffect = QGraphicsDropShadowEffect(self)
        shadowEffect.setColor(QColor(0, 0, 0, 12))
        shadowEffect.setBlurRadius(8)
        shadowEffect.setOffset(0, 0)
        self.setGraphicsEffect(shadowEffect)

    def update_value(self, value):
        self.value_label.setText(str(value))


class TaskOverviewCard(CardWidget):
    """任务概览：任务状态分布 + 最近活动"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(248)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title_layout = QHBoxLayout()
        icon_widget = IconWidget(get_fluent_icon(["CALENDAR", "DATE_TIME", "INFO"]), self)
        icon_widget.setFixedSize(18, 18)
        title_label = StrongBodyLabel("任务概览")
        setFont(title_label, 15)
        title_layout.addWidget(icon_widget)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # 左：状态分布
        status_layout = QVBoxLayout()
        status_layout.setSpacing(6)
        status_title = CaptionLabel("任务状态分布")
        status_title.setStyleSheet("color: #666;")
        setFont(status_title, 11)
        status_layout.addWidget(status_title)

        self.status_items = []
        status_configs = [
            ("计划中", "#0078d4", "planned"),
            ("进行中", "#107c10", "in_progress"),
            ("已完成", "#0a805e", "completed"),
            ("已暂停", "#ffaa44", "paused"),
            ("已中止", "#d13438", "aborted"),
        ]
        for status_name, color, status_key in status_configs:
            item_layout = QHBoxLayout()
            item_layout.setSpacing(8)

            indicator = QWidget()
            indicator.setFixedSize(10, 10)
            indicator.setStyleSheet(f"background-color: {color}; border-radius: 5px;")

            name_label = CaptionLabel(status_name)
            name_label.setStyleSheet("color: #666;")
            name_label.setFixedWidth(56)
            setFont(name_label, 11)

            count_label = BodyLabel("0")
            count_label.setStyleSheet(f"color: {color}; font-weight: 600;")
            setFont(count_label, 12)

            item_layout.addWidget(indicator)
            item_layout.addWidget(name_label)
            item_layout.addStretch()
            item_layout.addWidget(count_label)
            status_layout.addLayout(item_layout)
            self.status_items.append((status_key, count_label))

        # 右：最近活动
        activity_layout = QVBoxLayout()
        activity_layout.setSpacing(6)
        activity_title = CaptionLabel("最近活动")
        activity_title.setStyleSheet("color: #666;")
        setFont(activity_title, 11)
        activity_layout.addWidget(activity_title)

        self.recent_activity_layout = QVBoxLayout()
        self.recent_activity_layout.setSpacing(5)
        activity_layout.addLayout(self.recent_activity_layout)

        content_layout.addLayout(status_layout, 4)
        content_layout.addLayout(activity_layout, 6)

        layout.addLayout(title_layout)
        layout.addLayout(content_layout)

    def update_status_counts(self, status_counts):
        for status_key, count_label in self.status_items:
            count_label.setText(str(status_counts.get(status_key, 0)))

    def update_activities(self, activities):
        while self.recent_activity_layout.count():
            child = self.recent_activity_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not activities:
            empty_label = CaptionLabel("暂无最近活动")
            empty_label.setStyleSheet("color: #999;")
            setFont(empty_label, 11)
            self.recent_activity_layout.addWidget(empty_label)
            return

        for activity in activities[:4]:
            row = QHBoxLayout()
            row.setSpacing(6)

            icon = get_fluent_icon(["ACCEPT", "INFO", "CALENDAR"]) if activity.get("type") == "completed" else get_fluent_icon(["EDIT", "INFO", "CALENDAR"])
            icon_widget = IconWidget(icon, self)
            icon_widget.setFixedSize(14, 14)

            desc = CaptionLabel(activity.get("description", ""))
            desc.setStyleSheet("color: #444;")
            setFont(desc, 11)

            time_label = CaptionLabel(activity.get("time", ""))
            time_label.setStyleSheet("color: #999;")
            setFont(time_label, 10)

            row.addWidget(icon_widget)
            row.addWidget(desc)
            row.addStretch()
            row.addWidget(time_label)
            self.recent_activity_layout.addLayout(row)


class SmartEntryCard(CardWidget):
    """智能能力入口小卡片"""

    def __init__(self, title, description, status_text, button_text, button_icon, click_callback, icon, parent=None):
        super().__init__(parent)
        self.setFixedHeight(116)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        top_layout = QHBoxLayout()
        icon_widget = IconWidget(icon, self)
        icon_widget.setFixedSize(18, 18)
        name_label = StrongBodyLabel(title)
        setFont(name_label, 13)

        status_label = CaptionLabel(status_text)
        status_label.setStyleSheet("background:#0a805e; color:white; border-radius: 7px; padding:2px 8px;")

        top_layout.addWidget(icon_widget)
        top_layout.addWidget(name_label)
        top_layout.addStretch()
        top_layout.addWidget(status_label)

        desc_label = CaptionLabel(description)
        desc_label.setStyleSheet("color:#666;")
        setFont(desc_label, 11)

        button = PushButton(button_text)
        button.setIcon(button_icon)
        button.clicked.connect(click_callback)

        layout.addLayout(top_layout)
        layout.addWidget(desc_label)
        layout.addStretch()
        layout.addWidget(button, alignment=Qt.AlignLeft)


class DashboardInterface(NavInterface):
    """看板界面"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("DashboardInterface")
        self.active_workers = []

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(28, 18, 28, 18)
        self.main_layout.setSpacing(12)

        self.create_header()
        self.create_stat_cards()
        self.create_main_content()

        self.main_layout.addStretch(1)

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)

    def create_header(self):
        title_label = SubtitleLabel("系统概览")
        setFont(title_label, 22)
        subtitle_label = BodyLabel("复合材料加工数据管理与智能分析平台")
        subtitle_label.setStyleSheet("color: #666;")
        setFont(subtitle_label, 13)

        self.main_layout.addWidget(title_label)
        self.main_layout.addWidget(subtitle_label)

    def create_stat_cards(self):
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)

        self.user_card = CompactStatCard("总用户数", "0", get_fluent_icon(["PEOPLE", "CONTACT", "INFO"]), "平台用户", "#0078d4")
        self.task_card = CompactStatCard("总任务数", "0", get_fluent_icon(["CALENDAR", "DATE_TIME", "INFO"]), "累计任务", "#107c10")
        self.pending_card = CompactStatCard("待处理任务", "0", get_fluent_icon(["IMPORTANT", "INFO", "CALENDAR"]), "计划中+进行中", "#ffaa44")
        self.sensor_card = CompactStatCard("传感器数据量", "0", get_fluent_icon(["IOT", "ROBOT", "INFO"]), "已入库数据", "#8764b8")
        self.recommendation_card = CompactStatCard("参数推荐次数", "0", get_fluent_icon(["ROBOT", "INFO", "IOT"]), "推荐调用", "#0a805e")
        self.analysis_card = CompactStatCard("数据分析记录数", "0", get_fluent_icon(["DOCUMENT", "BOOK_SHELF", "INFO"]), "分析处理", "#5c2d91")

        for card in [
            self.user_card,
            self.task_card,
            self.pending_card,
            self.sensor_card,
            self.recommendation_card,
            self.analysis_card,
        ]:
            stats_layout.addWidget(card)

        self.main_layout.addLayout(stats_layout)

    def create_main_content(self):
        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        self.task_overview_card = TaskOverviewCard()
        body_layout.addWidget(self.task_overview_card, 3)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)

        right_title = StrongBodyLabel("智能能力概览")
        setFont(right_title, 14)
        right_layout.addWidget(right_title)

        self.recommendation_entry_card = SmartEntryCard(
            "参数推荐",
            "基于目标损伤等级与工艺条件进行参数推荐。",
            "可用",
            "进入参数推荐",
            get_fluent_icon(["ROBOT", "IOT", "INFO"]),
            self.goto_recommendation_page,
            get_fluent_icon(["ROBOT", "IOT", "INFO"]),
        )

        self.sensor_entry_card = SmartEntryCard(
            "传感器处理",
            "支持波形处理、特征提取与分析结果管理。",
            "已集成",
            "进入传感器处理",
            get_fluent_icon(["IOT", "ROBOT", "INFO"]),
            self.goto_sensor_processing_page,
            get_fluent_icon(["IOT", "ROBOT", "INFO"]),
        )

        right_layout.addWidget(self.recommendation_entry_card)
        right_layout.addWidget(self.sensor_entry_card)
        right_layout.addStretch(1)

        body_layout.addLayout(right_layout, 2)
        self.main_layout.addLayout(body_layout)

    def refresh_data(self):
        try:
            self.cancel_active_workers()
            logger.debug("使用数据管理器刷新看板数据")

            worker1 = data_manager.get_data_async(
                data_type="users",
                success_callback=self.on_users_data_received,
                error_callback=self.on_api_error,
            )
            if worker1:
                self.active_workers.append(worker1)

            worker2 = data_manager.get_data_async(
                data_type="processing_tasks",
                success_callback=self.on_tasks_data_received,
                error_callback=self.on_api_error,
            )
            if worker2:
                self.active_workers.append(worker2)

            worker3 = data_manager.get_data_async(
                data_type="sensor_data",
                success_callback=self.on_sensor_data_received,
                error_callback=self.on_api_error,
            )
            if worker3:
                self.active_workers.append(worker3)

            self.load_ai_metrics_fallback()
        except Exception as e:
            import traceback

            error_msg = f"看板数据刷新失败: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self.on_api_error(f"刷新失败: {e}")

    def load_ai_metrics_fallback(self):
        """参数推荐与分析记录当前无后端接口，使用缓存稳定回填。"""
        try:
            recommendation_data = data_manager.get_cached_data("recommendations")
            analysis_data = data_manager.get_cached_data("sensor_analysis")

            recommendation_count = recommendation_data.get("count", 0) if isinstance(recommendation_data, dict) else 0
            analysis_count = analysis_data.get("count", 0) if isinstance(analysis_data, dict) else 0

            self.recommendation_card.update_value(recommendation_count)
            self.analysis_card.update_value(analysis_count)
        except Exception as e:
            logger.warning(f"加载智能统计 fallback 失败，使用0: {e}")
            self.recommendation_card.update_value(0)
            self.analysis_card.update_value(0)

    def on_users_data_received(self, users_data):
        try:
            if not self or not hasattr(self, "user_card") or not self.user_card:
                logger.warning("用户数据回调时界面已销毁")
                return

            if users_data and "count" in users_data:
                self.user_card.update_value(users_data["count"])
                logger.debug(f"用户数据更新: {users_data['count']}")
        except Exception as e:
            logger.error(f"处理用户数据时出错: {e}")

    def on_tasks_data_received(self, tasks_data):
        try:
            if not self or not hasattr(self, "task_card") or not self.task_card:
                logger.warning("任务数据回调时界面已销毁")
                return

            if tasks_data:
                total_tasks = tasks_data.get("count", 0)
                self.task_card.update_value(total_tasks)

                tasks_list = tasks_data.get("results", [])
                status_counts = {}
                pending_count = 0

                for task in tasks_list:
                    status = task.get("status", "planned")
                    status_counts[status] = status_counts.get(status, 0) + 1
                    if status in ["planned", "in_progress"]:
                        pending_count += 1

                if hasattr(self, "pending_card") and self.pending_card:
                    self.pending_card.update_value(pending_count)
                if hasattr(self, "task_overview_card") and self.task_overview_card:
                    self.task_overview_card.update_status_counts(status_counts)

                if hasattr(self, "task_overview_card") and self.task_overview_card:
                    activities = self.generate_recent_activities(tasks_data)
                    self.task_overview_card.update_activities(activities)

                logger.debug(f"任务数据更新: 总数={total_tasks}, 待处理={pending_count}")
        except Exception as e:
            logger.error(f"处理任务数据时出错: {e}")

    def on_sensor_data_received(self, sensor_data):
        try:
            if not self or not hasattr(self, "sensor_card") or not self.sensor_card:
                logger.warning("传感器数据回调时界面已销毁")
                return

            if sensor_data and "count" in sensor_data:
                self.sensor_card.update_value(sensor_data["count"])
                logger.debug(f"传感器数据更新: {sensor_data['count']}")
        except Exception as e:
            logger.error(f"处理传感器数据时出错: {e}")

    def on_api_error(self, error_message):
        try:
            logger.error(f"看板数据加载失败: {error_message}")
        except Exception as e:
            logger.error(f"处理API错误时出错: {e}")

    def goto_recommendation_page(self):
        main_window = self.window()
        if hasattr(main_window, "switchTo") and hasattr(main_window, "recommendation_interface"):
            main_window.switchTo(main_window.recommendation_interface)

    def goto_sensor_processing_page(self):
        main_window = self.window()
        if hasattr(main_window, "switchTo") and hasattr(main_window, "sensor_processing_interface"):
            main_window.switchTo(main_window.sensor_processing_interface)

    def generate_recent_activities(self, tasks_data):
        activities = []
        if tasks_data and "results" in tasks_data:
            tasks_list = sorted(tasks_data["results"], key=lambda x: x.get("updated_at", ""), reverse=True)
            for task in tasks_list[:5]:
                activity = {
                    "type": task.get("status", "planned"),
                    "description": f"任务 {task.get('task_code', 'N/A')} - {task.get('status_display', 'N/A')}",
                    "time": task.get("updated_at", "")[:10] if task.get("updated_at") else "",
                }
                activities.append(activity)
        return activities

    def start_refresh_timer(self):
        if not self.refresh_timer.isActive():
            self.refresh_timer.start(30000)
            logger.debug("看板定时刷新已启动")

    def stop_refresh_timer(self):
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
            logger.debug("看板定时刷新已停止")
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
                logger.warning(f"取消异步任务时出错: {e}")

        self.active_workers.clear()
        logger.debug("已取消所有活跃的异步任务")

    def closeEvent(self, event):
        try:
            self.stop_refresh_timer()
            self.cancel_active_workers()
            logger.debug("看板界面已清理")
        except Exception as e:
            logger.error(f"看板界面清理时出错: {e}")
        finally:
            super().closeEvent(event)

    def __del__(self):
        try:
            if hasattr(self, "refresh_timer") and self.refresh_timer:
                self.refresh_timer.stop()
            if hasattr(self, "active_workers"):
                self.cancel_active_workers()
        except Exception:
            pass

    def on_activated(self):
        logger.debug("DashboardInterface 被激活，开始加载数据")
        self.refresh_data()

    def on_deactivated(self):
        self.cancel_active_workers()
        logger.debug("DashboardInterface 被切换离开，已取消所有活跃的数据加载请求")
