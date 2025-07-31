# coding:utf-8
from PyQt5.QtCore import Qt, QDateTime, pyqtSignal, QModelIndex
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QAbstractItemView, QStackedWidget, QGridLayout,
                             QAction, QSplitter)

from qfluentwidgets import (TableWidget, PushButton, StrongBodyLabel, LineEdit, ComboBox,
                            TextEdit, PrimaryPushButton, MessageBox, InfoBar, MessageBoxBase, SubtitleLabel,
                            DateTimeEdit, FluentIcon as FIF, CardWidget, BodyLabel, TransparentPushButton,
                            ScrollArea, TreeView, RoundMenu)

from ..api.api_client import api_client
from ..api.data_manager import interface_loader
from .nav_interface import NavInterface
import logging

# 设置logger
logger = logging.getLogger(__name__)

from .task_detail_interface import TaskDetailInterface
from .components.processing_task_component import TaskListWidget


class ProcessingTaskInterface(NavInterface):
    """ 加工任务管理主界面 """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("ProcessingTaskInterface")

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(40, 30, 40, 30)
        self.main_layout.setSpacing(30)
        
        self.title_label = SubtitleLabel("加工任务管理")
        self.main_layout.addWidget(self.title_label)
        
        self.stackWidget = QStackedWidget(self)
        self.task_list_widget = TaskListWidget(self)
        self.task_detail_interface = TaskDetailInterface(self)
        
        self.stackWidget.addWidget(self.task_list_widget)
        self.stackWidget.addWidget(self.task_detail_interface)
        self.main_layout.addWidget(self.stackWidget)
        
        # --- 信号连接 ---
        self.task_list_widget.viewDetailSignal.connect(self.show_task_detail)
        self.task_detail_interface.backRequested.connect(self.show_task_list)

    def on_activated(self):
        """界面激活时的回调方法 - 按需加载数据"""
        try:
            interface_loader.load_for_interface(
                interface=self.task_list_widget,
                data_type='processing_tasks',
                table_widget=self.task_list_widget.table,
                force_refresh=True,
                preserve_old_data=True,
                column_mapping=self.task_list_widget.column_mapping
            )
        except Exception as e:
            logger.error(f"激活加工任务界面时加载数据出错: {e}")
            self.task_list_widget.on_tasks_data_error(str(e))

    def on_deactivated(self):
        """
        当界面被切换离开时调用。
        可以在此处进行一些清理工作，如取消正在进行的请求。
        """
        if hasattr(self.task_list_widget, 'worker') and self.task_list_widget.worker:
            self.task_list_widget.worker.cancel()
            logger.debug("ProcessingTaskInterface 被切换离开，已取消数据加载请求")

    def show_task_detail(self, task_id: int):
        """ 切换到任务详情页 """
        self.task_detail_interface.load_task_details(task_id)
        self.stackWidget.setCurrentWidget(self.task_detail_interface)

    def show_task_list(self):
        """ 切换回任务列表页 """
        self.stackWidget.setCurrentWidget(self.task_list_widget)
        # 刷新任务列表数据
        self.task_list_widget.populate_table() 