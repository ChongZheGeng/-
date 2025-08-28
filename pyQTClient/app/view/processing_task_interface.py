# coding:utf-8
from PyQt5.QtCore import Qt, QDateTime, pyqtSignal, QModelIndex, QThread, QTimer
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QStackedWidget, QGridLayout, QScrollArea, QLabel, QFrame,
                             QAction, QSplitter)

from qfluentwidgets import (TableWidget, PushButton, StrongBodyLabel, LineEdit, ComboBox,
                            TextEdit, PrimaryPushButton, MessageBox, InfoBar, MessageBoxBase, SubtitleLabel,
                            DateTimeEdit, FluentIcon as FIF, CardWidget, BodyLabel, TransparentPushButton,
                            ScrollArea, TreeView, RoundMenu, ToolButton)

from ..api.api_client import api_client
from ..api.data_manager import interface_loader
from .nav_interface import NavInterface
import logging

# 设置logger
logger = logging.getLogger(__name__)

from .task_detail_interface import TaskDetailInterface
from .components.processing_task_component import TaskListWidget
from .components.processing_task_component import ProcessingTaskEditDialog  # 确保导入这个类


class TaskCard(CardWidget):
    """单个任务的卡片组件"""
    viewDetailSignal = pyqtSignal(int)
    editSignal = pyqtSignal(dict)
    cloneSignal = pyqtSignal(int)
    deleteSignal = pyqtSignal(int)

    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.task_id = task_data['id']

        # 修复：用样式表替代setRadius等方法（兼容不同版本Qfluentwidgets）
        self.setStyleSheet("""
            TaskCard {
                border-radius: 8px;
                border: 1px solid #ddd;
                background-color: white;
            }
        """)
        self.setMinimumHeight(180)
        self.setMaximumHeight(220)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(10)

        # 顶部：任务编码和操作按钮
        top_layout = QHBoxLayout()

        # 任务编码
        self.task_code_label = StrongBodyLabel(task_data.get('task_code', '未知任务'))
        top_layout.addWidget(self.task_code_label)

        # 操作按钮 - 修复：使用正确的FluentIcon枚举值
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        # 修复：FIF.EYE不存在，替换为FIF.VIEW
        self.view_btn = ToolButton(FIF.VIEW, self)
        self.view_btn.setToolTip("查看详情")
        self.view_btn.clicked.connect(lambda: self.viewDetailSignal.emit(self.task_id))

        self.edit_btn = ToolButton(FIF.EDIT, self)
        self.edit_btn.setToolTip("编辑")
        self.edit_btn.clicked.connect(lambda: self.editSignal.emit(self.task_data))

        self.clone_btn = ToolButton(FIF.COPY, self)
        self.clone_btn.setToolTip("复制")
        self.clone_btn.clicked.connect(lambda: self.cloneSignal.emit(self.task_id))

        self.delete_btn = ToolButton(FIF.DELETE, self)
        self.delete_btn.setToolTip("删除")
        self.delete_btn.clicked.connect(lambda: self.deleteSignal.emit(self.task_id))

        button_layout.addWidget(self.view_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.clone_btn)
        button_layout.addWidget(self.delete_btn)

        top_layout.addLayout(button_layout)
        main_layout.addLayout(top_layout)

        # 中间：任务基本信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        # 加工类型和状态
        type_status_layout = QHBoxLayout()
        type_layout = QHBoxLayout()
        type_layout.addWidget(BodyLabel("加工类型:"))
        type_layout.addWidget(BodyLabel(self._get_processing_type_display(task_data.get('processing_type'))))
        type_layout.addSpacing(20)

        status_layout = QHBoxLayout()
        status_layout.addWidget(BodyLabel("状态:"))
        status_label = BodyLabel(self._get_status_display(task_data.get('status')))
        # 根据状态设置不同颜色
        status_label.setStyleSheet(self._get_status_style(task_data.get('status')))
        status_layout.addWidget(status_label)

        type_status_layout.addLayout(type_layout)
        type_status_layout.addLayout(status_layout)
        type_status_layout.addStretch(1)

        # 刀具和构件
        tool_material_layout = QHBoxLayout()
        tool_layout = QHBoxLayout()
        tool_layout.addWidget(BodyLabel("刀具:"))
        tool_layout.addWidget(BodyLabel(task_data.get('tool_display', 'N/A')))
        tool_layout.addSpacing(20)

        material_layout = QHBoxLayout()
        material_layout.addWidget(BodyLabel("构件:"))
        material_layout.addWidget(BodyLabel(task_data.get('material_display', 'N/A')))

        tool_material_layout.addLayout(tool_layout)
        tool_material_layout.addLayout(material_layout)
        tool_material_layout.addStretch(1)

        # 操作员和时间
        operator_time_layout = QHBoxLayout()
        operator_layout = QHBoxLayout()
        operator_layout.addWidget(BodyLabel("操作员:"))
        operator_layout.addWidget(BodyLabel(task_data.get('operator_display', 'N/A')))
        operator_layout.addSpacing(20)

        time_layout = QHBoxLayout()
        time_layout.addWidget(BodyLabel("时间:"))
        processing_time = task_data.get('processing_time', '')
        display_time = processing_time.replace('T', ' ').split('.')[0] if processing_time else 'N/A'
        time_layout.addWidget(BodyLabel(display_time))

        operator_time_layout.addLayout(operator_layout)
        operator_time_layout.addLayout(time_layout)
        operator_time_layout.addStretch(1)

        # 添加到信息布局
        info_layout.addLayout(type_status_layout)
        info_layout.addLayout(tool_material_layout)
        info_layout.addLayout(operator_time_layout)

        main_layout.addLayout(info_layout)

        # 底部：分组信息
        group_layout = QHBoxLayout()
        group_layout.addWidget(BodyLabel("任务分组:"))
        group_layout.addWidget(BodyLabel(task_data.get('group_display', '未分配')))
        group_layout.addStretch(1)

        main_layout.addLayout(group_layout)

        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #eee;")

        main_layout.addWidget(line)

    def _get_processing_type_display(self, processing_type):
        """获取加工类型的显示文本"""
        for val, disp in ProcessingTaskEditDialog.TASK_TYPE_CHOICES:
            if val == processing_type:
                return disp
        return '未知'

    def _get_status_display(self, status):
        """获取状态的显示文本"""
        for val, disp in ProcessingTaskEditDialog.TASK_STATUS_CHOICES:
            if val == status:
                return disp
        return '未知'

    def _get_status_style(self, status):
        """根据状态返回不同的样式"""
        styles = {
            'planned': "color: #1E88E5;",  # 计划中 - 蓝色
            'in_progress': "color: #FF9800;",  # 进行中 - 橙色
            'completed': "color: #4CAF50;",  # 已完成 - 绿色
            'paused': "color: #9E9E9E;",  # 已暂停 - 灰色
            'aborted': "color: #F44336;"  # 已中止 - 红色
        }
        return styles.get(status, "")


class ProcessingTaskInterface(NavInterface):
    """ 加工任务管理主界面 """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("ProcessingTaskInterface")

        # 添加刷新按钮
        self.refresh_button = PushButton("刷新数据", self)
        self.refresh_button.setIcon(FIF.SYNC)
        self.refresh_button.clicked.connect(self.refresh_task_data)

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(40, 30, 40, 30)
        self.main_layout.setSpacing(30)

        # 标题和刷新按钮布局
        title_layout = QHBoxLayout()
        self.title_label = SubtitleLabel("加工任务管理")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.refresh_button)
        self.main_layout.addLayout(title_layout)

        self.stackWidget = QStackedWidget(self)
        self.task_list_widget = TaskListWidget(self)
        self.task_detail_interface = TaskDetailInterface(self)

        self.stackWidget.addWidget(self.task_list_widget)
        self.stackWidget.addWidget(self.task_detail_interface)
        self.main_layout.addWidget(self.stackWidget)

        # --- 信号连接 ---
        self.task_list_widget.viewDetailSignal.connect(self.show_task_detail)
        self.task_detail_interface.backRequested.connect(self.show_task_list)

        # 修复：使用加载状态标志替代请求对象跟踪
        self.is_loading = False  # 标记是否正在加载数据

    def on_activated(self):
        """界面激活时的回调方法 - 加载数据"""
        logger.debug("ProcessingTaskInterface 被激活，开始加载任务数据")
        # 使用定时器延迟发起请求，避免与界面切换的取消逻辑冲突
        QTimer.singleShot(300, self.refresh_task_data)

    def refresh_task_data(self):
        """刷新任务数据的方法 - 适配API返回字典的情况"""
        try:
            # 标记为加载中
            self.is_loading = True
            logger.debug("直接发起API调用: get_processing_tasks")

            # 修复：API返回的是数据字典而非请求对象
            data = api_client.get_processing_tasks()

            # 直接处理返回的数据
            if isinstance(data, dict) and 'results' in data:
                # 假设API返回格式为{"results": [...]}
                self.on_data_received(data['results'])
            else:
                # 兼容直接返回列表的情况
                self.on_data_received(data)

        except Exception as e:
            logger.error(f"加载加工任务数据出错: {e}")
            self.on_data_error(str(e))
        finally:
            # 无论成功失败，都标记为加载完成
            self.is_loading = False

    def on_data_received(self, data):
        """数据接收成功后的处理"""
        logger.debug(f"成功接收加工任务数据，共 {len(data)} 条记录")
        # 直接更新任务列表组件
        self.task_list_widget.update_data(data)
        self.task_list_widget.populate_table()

    def on_data_error(self, error):
        """数据接收错误处理"""
        logger.error(f"接收加工任务数据时发生错误: {error}")
        self.task_list_widget.on_processing_tasks_data_error(str(error))

    def on_deactivated(self):
        """当界面被切换离开时调用 - 修复请求状态判断逻辑"""
        # 修复：使用加载状态标志替代请求对象判断
        if self.is_loading and self.stackWidget.currentWidget() == self.task_list_widget:
            logger.debug("ProcessingTaskInterface 被切换离开，数据加载中")
            # 对于同步请求，无法取消，仅记录日志

    def show_task_detail(self, task_id: int):
        """ 切换到任务详情页 """
        self.task_detail_interface.load_task_details(task_id)
        self.stackWidget.setCurrentWidget(self.task_detail_interface)

    def show_task_list(self):
        """ 切换回任务列表页并刷新数据 """
        self.stackWidget.setCurrentWidget(self.task_list_widget)
        # 返回列表时刷新数据
        self.refresh_task_data()
