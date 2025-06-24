# coding:utf-8
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGraphicsDropShadowEffect

from qfluentwidgets import (CardWidget, SubtitleLabel, BodyLabel, StrongBodyLabel, 
                            IconWidget, FluentIcon as FIF, InfoBar, ProgressBar, 
                            TitleLabel, CaptionLabel, setFont)

from ..api.api_client import api_client
import logging

# 设置logger
logger = logging.getLogger(__name__)

# 安全导入异步API
try:
    from ..api.async_api import async_api
    ASYNC_API_AVAILABLE = True
    logger.debug("异步API模块导入成功")
except ImportError as e:
    logger.warning(f"异步API模块导入失败: {e}")
    async_api = None
    ASYNC_API_AVAILABLE = False


class StatCard(CardWidget):
    """统计卡片组件"""
    
    def __init__(self, title, value, icon, color="#0078d4", parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 140)  # 固定大小，更美观
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        
        # 顶部布局：图标和标题
        top_layout = QHBoxLayout()
        
        self.icon_widget = IconWidget(icon, self)
        self.icon_widget.setFixedSize(28, 28)
        self.icon_widget.setStyleSheet(f"color: {color};")
        
        self.title_label = BodyLabel(title)
        self.title_label.setStyleSheet("color: #666; font-size: 14px;")
        
        top_layout.addWidget(self.icon_widget)
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()
        
        layout.addLayout(top_layout)
        
        # 数值显示
        self.value_label = TitleLabel(str(value))
        self.value_label.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: bold;")
        setFont(self.value_label, 32)
        layout.addWidget(self.value_label)
        
        layout.addStretch()
        
        # 添加阴影效果
        self.setShadowEffect()
    
    def setShadowEffect(self):
        """添加阴影效果"""
        shadowEffect = QGraphicsDropShadowEffect(self)
        shadowEffect.setColor(QColor(0, 0, 0, 15))
        shadowEffect.setBlurRadius(10)
        shadowEffect.setOffset(0, 0)
        self.setGraphicsEffect(shadowEffect)
    
    def update_value(self, value):
        """更新数值"""
        self.value_label.setText(str(value))


class TaskStatusCard(CardWidget):
    """任务状态卡片"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 240)  # 固定大小
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 标题
        title_layout = QHBoxLayout()
        icon_widget = IconWidget(FIF.CALENDAR, self)
        icon_widget.setFixedSize(24, 24)
        title_label = StrongBodyLabel("任务状态分布")
        setFont(title_label, 16)
        
        title_layout.addWidget(icon_widget)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # 状态项
        self.status_items = []
        status_configs = [
            ("计划中", "#0078d4", "planned"),
            ("进行中", "#107c10", "in_progress"),
            ("已完成", "#0a805e", "completed"),
            ("已暂停", "#ffaa44", "paused"),
            ("已中止", "#d13438", "aborted")
        ]
        
        for status_name, color, status_key in status_configs:
            item_layout = QHBoxLayout()
            item_layout.setSpacing(12)
            
            # 状态指示器
            indicator = QWidget()
            indicator.setFixedSize(14, 14)
            indicator.setStyleSheet(f"background-color: {color}; border-radius: 7px;")
            
            # 状态名称
            name_label = BodyLabel(status_name)
            name_label.setFixedWidth(80)
            setFont(name_label, 14)
            
            # 数量
            count_label = BodyLabel("0")
            count_label.setStyleSheet(f"color: {color}; font-weight: bold;")
            setFont(count_label, 14)
            
            item_layout.addWidget(indicator)
            item_layout.addWidget(name_label)
            item_layout.addStretch()
            item_layout.addWidget(count_label)
            
            layout.addLayout(item_layout)
            self.status_items.append((status_key, count_label))
        
        # 添加阴影效果
        self.setShadowEffect()
    
    def setShadowEffect(self):
        """添加阴影效果"""
        shadowEffect = QGraphicsDropShadowEffect(self)
        shadowEffect.setColor(QColor(0, 0, 0, 15))
        shadowEffect.setBlurRadius(10)
        shadowEffect.setOffset(0, 0)
        self.setGraphicsEffect(shadowEffect)
    
    def update_status_counts(self, status_counts):
        """更新状态统计"""
        for status_key, count_label in self.status_items:
            count = status_counts.get(status_key, 0)
            count_label.setText(str(count))


class RecentActivityCard(CardWidget):
    """最近活动卡片"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 240)  # 固定大小
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 标题
        title_layout = QHBoxLayout()
        icon_widget = IconWidget(FIF.HISTORY, self)
        icon_widget.setFixedSize(24, 24)
        title_label = StrongBodyLabel("最近活动")
        setFont(title_label, 16)
        
        title_layout.addWidget(icon_widget)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # 活动列表容器
        self.activity_layout = QVBoxLayout()
        self.activity_layout.setSpacing(8)
        layout.addLayout(self.activity_layout)
        
        layout.addStretch()
        
        # 添加阴影效果
        self.setShadowEffect()
    
    def setShadowEffect(self):
        """添加阴影效果"""
        shadowEffect = QGraphicsDropShadowEffect(self)
        shadowEffect.setColor(QColor(0, 0, 0, 15))
        shadowEffect.setBlurRadius(10)
        shadowEffect.setOffset(0, 0)
        self.setGraphicsEffect(shadowEffect)
    
    def update_activities(self, activities):
        """更新活动列表"""
        # 清空现有活动
        while self.activity_layout.count():
            child = self.activity_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 添加新活动
        for activity in activities[:5]:  # 只显示最近5条
            activity_layout = QHBoxLayout()
            activity_layout.setSpacing(12)
            
            # 活动图标
            icon = FIF.ACCEPT if activity.get('type') == 'completed' else FIF.EDIT
            icon_widget = IconWidget(icon, self)
            icon_widget.setFixedSize(18, 18)
            
            # 活动描述
            desc_label = BodyLabel(activity.get('description', ''))
            desc_label.setStyleSheet("color: #333;")
            setFont(desc_label, 13)
            
            # 时间
            time_label = CaptionLabel(activity.get('time', ''))
            time_label.setStyleSheet("color: #999;")
            setFont(time_label, 12)
            
            activity_layout.addWidget(icon_widget)
            activity_layout.addWidget(desc_label)
            activity_layout.addStretch()
            activity_layout.addWidget(time_label)
            
            self.activity_layout.addLayout(activity_layout)


class DashboardInterface(QWidget):
    """看板界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("DashboardInterface")
        
        # 异步任务管理
        self.active_workers = []
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(40, 30, 40, 30)
        self.main_layout.setSpacing(30)
        
        # 标题
        title_label = SubtitleLabel("系统概览")
        setFont(title_label, 24)
        self.main_layout.addWidget(title_label)
        
        # 统计卡片网格
        self.create_stat_cards()
        
        # 详细信息卡片
        self.create_detail_cards()
        
        # 定时刷新 - 但不立即启动
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        
        # 延迟初始加载数据，避免启动时的问题
        self.init_timer = QTimer()
        self.init_timer.setSingleShot(True)
        self.init_timer.timeout.connect(self.delayed_refresh_data)
        self.init_timer.start(1000)  # 1秒后加载数据
    
    def create_stat_cards(self):
        """创建统计卡片"""
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        # 创建统计卡片
        self.user_card = StatCard("总用户数", "0", FIF.PEOPLE, "#0078d4")
        self.task_card = StatCard("总任务数", "0", FIF.CALENDAR, "#107c10")
        self.pending_card = StatCard("待处理任务", "0", FIF.DATE_TIME, "#ffaa44")
        self.sensor_card = StatCard("传感器数据", "0", FIF.IOT, "#8764b8")
        
        # 添加到布局
        stats_layout.addWidget(self.user_card)
        stats_layout.addWidget(self.task_card)
        stats_layout.addWidget(self.pending_card)
        stats_layout.addWidget(self.sensor_card)
        stats_layout.addStretch()
        
        self.main_layout.addLayout(stats_layout)
    
    def create_detail_cards(self):
        """创建详细信息卡片"""
        detail_layout = QHBoxLayout()
        detail_layout.setSpacing(20)
        
        # 任务状态卡片
        self.task_status_card = TaskStatusCard()
        detail_layout.addWidget(self.task_status_card)
        
        # 最近活动卡片
        self.activity_card = RecentActivityCard()
        detail_layout.addWidget(self.activity_card)
        
        detail_layout.addStretch()
        
        self.main_layout.addLayout(detail_layout)
        
        # 添加弹性空间
        self.main_layout.addStretch()
    
    def refresh_data(self):
        """刷新数据（优先使用异步，回退到同步）"""
        try:
            # 取消之前的异步任务
            self.cancel_active_workers()
            
            if ASYNC_API_AVAILABLE and async_api:
                logger.debug("开始异步刷新看板数据")
                
                # 异步获取用户统计
                worker1 = async_api.get_users_async(
                    success_callback=self.on_users_data_received,
                    error_callback=self.on_api_error
                )
                if worker1:
                    self.active_workers.append(worker1)
                
                # 异步获取任务统计
                worker2 = async_api.get_processing_tasks_async(
                    success_callback=self.on_tasks_data_received,
                    error_callback=self.on_api_error
                )
                if worker2:
                    self.active_workers.append(worker2)
                
                # 异步获取传感器数据统计
                worker3 = async_api.get_sensor_data_async(
                    success_callback=self.on_sensor_data_received,
                    error_callback=self.on_api_error
                )
                if worker3:
                    self.active_workers.append(worker3)
            else:
                logger.debug("回退到同步刷新看板数据")
                self.refresh_data_sync()
                
        except Exception as e:
            import traceback
            error_msg = f"看板数据刷新失败: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            # 回退到同步调用
            try:
                self.refresh_data_sync()
            except Exception as sync_e:
                logger.error(f"同步刷新也失败: {sync_e}")
    
    def refresh_data_sync(self):
        """同步刷新数据（备用方案）"""
        try:
            logger.debug("执行同步数据刷新")
            
            # 获取用户统计
            users_data = api_client.get_users()
            self.on_users_data_received(users_data)
            
            # 获取任务统计
            tasks_data = api_client.get_processing_tasks()
            self.on_tasks_data_received(tasks_data)
            
            # 获取传感器数据统计
            sensor_data = api_client.get_sensor_data()
            self.on_sensor_data_received(sensor_data)
            
        except Exception as e:
            import traceback
            error_msg = f"同步刷新失败: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self.on_api_error(str(e))
    
    def on_users_data_received(self, users_data):
        """处理用户数据"""
        try:
            if not self or not hasattr(self, 'user_card') or not self.user_card:
                logger.warning("用户数据回调时界面已销毁")
                return
                
            if users_data and 'count' in users_data:
                self.user_card.update_value(users_data['count'])
                logger.debug(f"用户数据更新: {users_data['count']}")
        except Exception as e:
            logger.error(f"处理用户数据时出错: {e}")
    
    def on_tasks_data_received(self, tasks_data):
        """处理任务数据"""
        try:
            if not self or not hasattr(self, 'task_card') or not self.task_card:
                logger.warning("任务数据回调时界面已销毁")
                return
                
            if tasks_data:
                total_tasks = tasks_data.get('count', 0)
                self.task_card.update_value(total_tasks)
                
                # 统计各状态任务数量
                tasks_list = tasks_data.get('results', [])
                status_counts = {}
                pending_count = 0
                
                for task in tasks_list:
                    status = task.get('status', 'planned')
                    status_counts[status] = status_counts.get(status, 0) + 1
                    
                    # 计算待处理任务（计划中+进行中）
                    if status in ['planned', 'in_progress']:
                        pending_count += 1
                
                if hasattr(self, 'pending_card') and self.pending_card:
                    self.pending_card.update_value(pending_count)
                if hasattr(self, 'task_status_card') and self.task_status_card:
                    self.task_status_card.update_status_counts(status_counts)
                
                # 生成最近活动
                if hasattr(self, 'activity_card') and self.activity_card:
                    activities = self.generate_recent_activities(tasks_data)
                    self.activity_card.update_activities(activities)
                
                logger.debug(f"任务数据更新: 总数={total_tasks}, 待处理={pending_count}")
        except Exception as e:
            logger.error(f"处理任务数据时出错: {e}")
    
    def on_sensor_data_received(self, sensor_data):
        """处理传感器数据"""
        try:
            if not self or not hasattr(self, 'sensor_card') or not self.sensor_card:
                logger.warning("传感器数据回调时界面已销毁")
                return
                
            if sensor_data and 'count' in sensor_data:
                self.sensor_card.update_value(sensor_data['count'])
                logger.debug(f"传感器数据更新: {sensor_data['count']}")
        except Exception as e:
            logger.error(f"处理传感器数据时出错: {e}")
    
    def on_api_error(self, error_message):
        """处理API错误"""
        try:
            logger.error(f"看板数据加载失败: {error_message}")
        except Exception as e:
            logger.error(f"处理API错误时出错: {e}")
    
    def generate_recent_activities(self, tasks_data):
        """生成最近活动列表"""
        activities = []
        
        if tasks_data and 'results' in tasks_data:
            # 按更新时间排序，取最近的几条
            tasks_list = sorted(
                tasks_data['results'], 
                key=lambda x: x.get('updated_at', ''), 
                reverse=True
            )
            
            for task in tasks_list[:5]:
                activity = {
                    'type': task.get('status', 'planned'),
                    'description': f"任务 {task.get('task_code', 'N/A')} - {task.get('status_display', 'N/A')}",
                    'time': task.get('updated_at', '')[:10] if task.get('updated_at') else ''
                }
                activities.append(activity)
        
        return activities
    
    def delayed_refresh_data(self):
        """延迟刷新数据"""
        logger.debug("延迟刷新数据被触发")
        try:
            self.refresh_data()
        except Exception as e:
            logger.error(f"延迟刷新失败: {e}")
    
    def start_refresh_timer(self):
        """启动定时刷新"""
        if not self.refresh_timer.isActive():
            self.refresh_timer.start(30000)  # 每30秒刷新一次
            logger.debug("看板定时刷新已启动")
    
    def stop_refresh_timer(self):
        """停止定时刷新"""
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
            logger.debug("看板定时刷新已停止")
        
        # 取消所有活跃的异步任务
        self.cancel_active_workers()
    
    def cancel_active_workers(self):
        """取消所有活跃的异步工作线程"""
        for worker in self.active_workers:
            try:
                if hasattr(worker, 'cancel'):
                    worker.cancel()
                if worker.isRunning():
                    worker.quit()
                    worker.wait(1000)  # 等待最多1秒
            except Exception as e:
                logger.warning(f"取消异步任务时出错: {e}")
        
        self.active_workers.clear()
        logger.debug("已取消所有活跃的异步任务")
    
    def closeEvent(self, event):
        """界面关闭时的清理"""
        try:
            self.stop_refresh_timer()
            self.cancel_active_workers()
            logger.debug("看板界面已清理")
        except Exception as e:
            logger.error(f"看板界面清理时出错: {e}")
        finally:
            super().closeEvent(event)
    
    def __del__(self):
        """析构函数清理"""
        try:
            if hasattr(self, 'refresh_timer') and self.refresh_timer:
                self.refresh_timer.stop()
            if hasattr(self, 'active_workers'):
                self.cancel_active_workers()
        except:
            pass  # 析构时忽略所有异常
    
 