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
import logging

# 设置logger
logger = logging.getLogger(__name__)

# 导入数据管理器
try:
    from ..api.data_manager import interface_loader
    DATA_MANAGER_AVAILABLE = True
    logger.debug("数据管理器导入成功")
except ImportError as e:
    logger.warning(f"数据管理器导入失败，回退到原始异步API: {e}")
    # 安全导入异步API作为回退
    try:
        from ..api.async_api import async_api
        ASYNC_API_AVAILABLE = True
        logger.debug("异步API模块导入成功")
    except ImportError as e2:
        logger.warning(f"异步API模块导入失败: {e2}")
        async_api = None
        ASYNC_API_AVAILABLE = False
    DATA_MANAGER_AVAILABLE = False

from .task_detail_interface import TaskDetailInterface


class GroupNameDialog(MessageBoxBase):
    """ 用于输入任务组名称的对话框 """
    def __init__(self, title, initial_text="", parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(title, self)
        self.lineEdit = LineEdit(self)
        self.lineEdit.setText(initial_text)
        self.lineEdit.setPlaceholderText("请输入名称...")
        
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.lineEdit)
        
        self.widget.setMinimumWidth(350)
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")

    def getName(self):
        return self.lineEdit.text().strip()


class ParameterWidget(QWidget):
    """用于动态管理加工参数的独立小部件"""
    def __init__(self, parameters=None, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)
        
        # --- 参数滚动区域 ---
        self.scroll_area = ScrollArea(self)
        self.scroll_widget = QWidget()
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(150)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: transparent; border: 1px solid #444; }")
        self.scroll_widget.setStyleSheet("QWidget { background-color: transparent; }")
        
        self.param_layout = QVBoxLayout(self.scroll_widget)
        self.param_layout.setSpacing(10)
        self.param_layout.setAlignment(Qt.AlignTop)

        # --- 添加按钮 ---
        self.add_param_button = PushButton("添加参数")
        self.add_param_button.setIcon(FIF.ADD)
        self.add_param_button.clicked.connect(self.add_parameter_row)
        
        # --- 主布局装配 ---
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addWidget(self.add_param_button)
        
        if parameters:
            for param in parameters:
                self.add_parameter_row(param)

    def add_parameter_row(self, param_data=None):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 5, 0, 5)

        name_edit = LineEdit(self)
        name_edit.setPlaceholderText("参数名称 (如: 主轴转速)")
        
        value_edit = LineEdit(self)
        value_edit.setPlaceholderText("参数值 (如: 3000)")
        
        unit_edit = LineEdit(self)
        unit_edit.setPlaceholderText("单位 (如: rpm)")

        remove_button = TransparentPushButton(parent=row_widget)
        remove_button.setIcon(FIF.REMOVE)
        
        if param_data:
            name_edit.setText(param_data.get('parameter_name', ''))
            value_edit.setText(str(param_data.get('parameter_value', '')))
            unit_edit.setText(param_data.get('unit', ''))

        remove_button.clicked.connect(lambda: self.remove_parameter_row(row_widget))

        row_layout.addWidget(name_edit)
        row_layout.addWidget(value_edit)
        row_layout.addWidget(unit_edit)
        row_layout.addWidget(remove_button)
        
        self.param_layout.addWidget(row_widget)

    def remove_parameter_row(self, row_widget):
        self.param_layout.removeWidget(row_widget)
        row_widget.deleteLater()

    def get_parameters(self):
        params = []
        for i in range(self.param_layout.count()):
            row_widget = self.param_layout.itemAt(i).widget()
            if row_widget:
                layout = row_widget.layout()
                name = layout.itemAt(0).widget().text().strip()
                value = layout.itemAt(1).widget().text().strip()
                unit = layout.itemAt(2).widget().text().strip()
                
                if name and value:
                    params.append({
                        "parameter_name": name,
                        "parameter_value": value,
                        "unit": unit
                    })
        return params


class ProcessingTaskEditDialog(MessageBoxBase):
    """ 用于编辑或添加加工任务的自定义对话框 """
    TASK_TYPE_CHOICES = [
        ('drilling', '钻孔'), ('milling', '铣削'), ('cutting', '切割'),
        ('trimming', '修边'), ('other', '其他'),
    ]
    TASK_STATUS_CHOICES = [
        ('planned', '计划中'), ('in_progress', '进行中'), ('completed', '已完成'),
        ('paused', '已暂停'), ('aborted', '已中止'),
    ]

    def __init__(self, parent=None, task_data=None, group_to_select=None):
        super().__init__(parent)
        self.task_data = task_data
        is_edit_mode = task_data is not None

        # 设置标题
        self.titleLabel = SubtitleLabel("编辑任务" if is_edit_mode else "新增任务", self)

        # --- 创建输入字段 ---
        self.task_code_edit = LineEdit(self)
        self.processing_time_edit = DateTimeEdit(self)
        self.processing_time_edit.setDateTime(QDateTime.currentDateTime())
        self.processing_type_combo = ComboBox(self)
        self.tool_combo = ComboBox(self)
        self.material_combo = ComboBox(self)
        self.status_combo = ComboBox(self)
        self.duration_edit = LineEdit(self) # 预计持续时间
        self.operator_combo = ComboBox(self)
        self.notes_edit = TextEdit(self)
        self.notes_edit.setMinimumHeight(60)
        self.group_combo = ComboBox(self)

        # --- 填充下拉框 ---
        for _, display in self.TASK_TYPE_CHOICES: self.processing_type_combo.addItem(display)
        for _, display in self.TASK_STATUS_CHOICES: self.status_combo.addItem(display)
        
        # 动态加载刀具、材料和人员
        self.load_tools()
        self.load_materials()
        self.load_operators()
        self.load_groups()

        # --- 如果是编辑模式，则填充现有数据 ---
        parameters = []
        if is_edit_mode:
            self.task_code_edit.setText(task_data.get('task_code', ''))
            proc_time = QDateTime.fromString(task_data.get('processing_time', ''), Qt.ISODate)
            if proc_time.isValid():
                self.processing_time_edit.setDateTime(proc_time)
            
            # 设置下拉框的选中项
            self.set_combo_by_value(self.processing_type_combo, self.TASK_TYPE_CHOICES, task_data.get('processing_type'))
            self.set_combo_by_data(self.tool_combo, task_data.get('tool_info', {}).get('id'))
            self.set_combo_by_data(self.material_combo, task_data.get('material_info', {}).get('id'))
            self.set_combo_by_data(self.operator_combo, task_data.get('operator_info', {}).get('id'))
            self.set_combo_by_data(self.group_combo, task_data.get('group'))
            
            self.duration_edit.setText(str(task_data.get('duration', '')))
            self.notes_edit.setText(task_data.get('notes', ''))
            parameters = task_data.get('parameters', [])
        elif group_to_select:
            self.set_combo_by_data(self.group_combo, group_to_select)

        # --- 优化后的紧凑布局 ---
        content_layout = QVBoxLayout()
        content_layout.setSpacing(15)

        # 网格布局用于顶部字段
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(3, 1)

        grid_layout.addWidget(StrongBodyLabel("任务编码:"), 0, 0)
        grid_layout.addWidget(self.task_code_edit, 0, 1)
        grid_layout.addWidget(StrongBodyLabel("操作员:"), 0, 2)
        grid_layout.addWidget(self.operator_combo, 0, 3)

        grid_layout.addWidget(StrongBodyLabel("加工时间:"), 1, 0)
        grid_layout.addWidget(self.processing_time_edit, 1, 1)
        grid_layout.addWidget(StrongBodyLabel("预计耗时(分钟):"), 1, 2)
        grid_layout.addWidget(self.duration_edit, 1, 3)

        grid_layout.addWidget(StrongBodyLabel("加工类型:"), 2, 0)
        grid_layout.addWidget(self.processing_type_combo, 2, 1)
        grid_layout.addWidget(StrongBodyLabel("任务状态:"), 2, 2)
        grid_layout.addWidget(self.status_combo, 2, 3)

        grid_layout.addWidget(StrongBodyLabel("所属分组:"), 3, 0)
        grid_layout.addWidget(self.group_combo, 3, 1)
        
        content_layout.addLayout(grid_layout)

        # 单独一行的字段
        content_layout.addWidget(StrongBodyLabel("选用刀具:"))
        content_layout.addWidget(self.tool_combo)
        content_layout.addWidget(StrongBodyLabel("加工构件:"))
        content_layout.addWidget(self.material_combo)
        
        # 加工参数
        content_layout.addWidget(StrongBodyLabel("加工参数:"))
        self.parameter_widget = ParameterWidget(parameters, self)
        content_layout.addWidget(self.parameter_widget)
        
        # 备注
        content_layout.addWidget(StrongBodyLabel("备注:"))
        content_layout.addWidget(self.notes_edit)

        # 将内容布局添加到对话框的主视图中
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addLayout(content_layout)

        # --- 按钮和尺寸 ---
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(750)

    def add_widget_pair(self, label_text, widget):
        self.viewLayout.addWidget(StrongBodyLabel(label_text, self))
        self.viewLayout.addWidget(widget)

    def load_tools(self):
        tools = api_client.get_tools()
        if tools and 'results' in tools:
            for tool in tools['results']:
                self.tool_combo.addItem(f"{tool['code']} ({tool['tool_type']})", userData=tool['id'])

    def load_materials(self):
        materials = api_client.get_composite_materials()
        if materials and 'results' in materials:
            for material in materials['results']:
                self.material_combo.addItem(f"{material['part_number']}", userData=material['id'])

    def load_operators(self):
        """加载操作员列表 (从用户列表获取)"""
        users = api_client.get_users()
        if users and 'results' in users:
            for user in users['results']:
                # 使用 full_name，如果不存在则使用 username
                display_name = user.get('full_name') or user.get('username', '')
                if display_name:
                    self.operator_combo.addItem(display_name, userData=user['id'])

    def load_groups(self):
        self.group_combo.clear()
        self.group_combo.addItem("无分组", userData=None)
        response = api_client.get_task_groups()
        if response and 'results' in response:
            for group in response['results']:
                self.group_combo.addItem(group['name'], userData=group['id'])

    def set_combo_by_value(self, combo, choices, value_to_find):
        for index, (val, _) in enumerate(choices):
            if val == value_to_find:
                combo.setCurrentIndex(index)
                return
    
    def set_combo_by_data(self, combo, data_to_find):
        """ 根据 a-zA-Z0-9_  找到并选中 combox 里的项目 """
        for i in range(combo.count()):
            if combo.itemData(i) == data_to_find:
                combo.setCurrentIndex(i)
                return

    def get_data(self):
        """ 获取表单中的数据 """
        try:
            # 检查必填字段
            if not self.task_code_edit.text().strip(): return None, "任务编码不能为空"
            if not self.operator_combo.currentText().strip(): return None, "操作员不能为空"
            if self.tool_combo.currentIndex() < 0: return None, "请选择刀具"
            if self.material_combo.currentIndex() < 0: return None, "请选择构件"

            # 获取数据
            proc_type = self.TASK_TYPE_CHOICES[self.processing_type_combo.currentIndex()][0]
            status = self.TASK_STATUS_CHOICES[self.status_combo.currentIndex()][0]
            tool_id = self.tool_combo.currentData()
            material_id = self.material_combo.currentData()
            operator_id = self.operator_combo.currentData()
            group_id = self.group_combo.currentData()
            
            duration = self.duration_edit.text().strip()
            if duration and not duration.isdigit():
                return None, "预计耗时必须是整数"

            # 获取加工参数
            params = self.parameter_widget.get_parameters()

            # 构建任务数据
            task_data = {
                "task_code": self.task_code_edit.text().strip(),
                "processing_time": self.processing_time_edit.dateTime().toString(Qt.ISODate),
                "processing_type": proc_type,
                "tool": tool_id,
                "composite_material": material_id,
                "status": status,
                "duration": int(duration) if duration else None,
                "operator": operator_id,
                "notes": self.notes_edit.toPlainText().strip(),
                "parameters": params,
            }
            
            # 仅在选择了有效分组时才添加 group 字段
            if group_id is not None:
                task_data['group'] = group_id
            else: # 如果选择的是"无分组", 则发送 null
                task_data['group'] = None

            return task_data, None

        except (ValueError, IndexError) as e:
            return None, f"数据格式错误: {str(e)}"

    def validate(self):
        data, error_msg = self.get_data()
        if data is None:
            InfoBar.warning("提示", error_msg, duration=3000, parent=self)
            return False
        return True


class TaskListWidget(QWidget):
    """ 显示任务列表的专用小部件 """
    viewDetailSignal = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.worker = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # --- 工具栏 ---
        toolbar_layout = QHBoxLayout()
        self.add_button = PrimaryPushButton("新增任务")
        self.refresh_button = PushButton("刷新数据")
        toolbar_layout.addWidget(self.add_button)
        toolbar_layout.addWidget(self.refresh_button)
        toolbar_layout.addStretch(1)
        layout.addLayout(toolbar_layout)

        # --- 数据表格 ---
        self.table = TableWidget(self)
        layout.addWidget(self.table)
        
        # --- 应用官方示例样式 ---
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)
        # --- 样式应用结束 ---
        
        self.table.setColumnCount(9)
        headers = ["任务编码", "加工类型", "状态", "刀具", "构件", "任务分组", "操作员", "加工时间", "操作"]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # 列宽设置：数据列可调整，操作列固定宽度，倒数第二列拉伸
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)  # 数据列可调整
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)  # 加工时间列拉伸以铺满
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.Fixed)  # 操作列固定宽度
        # 初始设置操作列宽度（数据加载后会重新计算）
        self.table.horizontalHeader().resizeSection(8, 280)
        self.table.setAlternatingRowColors(True)

        # --- 信号与槽连接 ---
        self.refresh_button.clicked.connect(self.populate_table)
        self.add_button.clicked.connect(self.add_task)
        
    def populate_table(self, preserve_old_data=True):
        """ 异步从API获取数据并填充表格 """
        try:
            if DATA_MANAGER_AVAILABLE:
                logger.debug("使用数据管理器加载加工任务数据")
                # 使用新的数据管理器
                interface_loader.load_for_interface(
                    interface=self,
                    data_type='processing_tasks',
                    table_widget=self.table,
                    force_refresh=True,
                    preserve_old_data=preserve_old_data
                )
            elif ASYNC_API_AVAILABLE and async_api:
                # 回退到原始异步API
                logger.debug("回退到原始异步API加载加工任务数据")
                if self.worker and self.worker.isRunning():
                    self.worker.cancel()
                
                if not preserve_old_data:
                    self.table.setRowCount(0)
                self.worker = async_api.get_processing_tasks_async(
                    success_callback=self.on_tasks_data_received,
                    error_callback=self.on_tasks_data_error
                )
            else:
                # 最终回退到同步加载
                logger.warning("异步API不可用，回退到同步加载")
                if not preserve_old_data:
                    self.table.setRowCount(0)
                try:
                    response_data = api_client.get_processing_tasks()
                    self.on_tasks_data_received(response_data)
                except Exception as e:
                    self.on_tasks_data_error(str(e))
        except Exception as e:
            logger.error(f"加载加工任务数据时出错: {e}")
            self.on_tasks_data_error(str(e))
    
    def on_processing_tasks_data_received(self, response_data):
        """数据管理器使用的标准回调方法"""
        self.on_tasks_data_received(response_data)
    
    def on_processing_tasks_data_error(self, error):
        """数据管理器使用的标准错误回调方法"""
        self.on_tasks_data_error(error)
    
    def on_tasks_data_received(self, response_data):
        """处理接收到的加工任务数据"""
        try:
            if not self or not hasattr(self, 'table') or not self.table:
                logger.warning("加工任务数据回调时界面已销毁")
                return
                
            if response_data is None:
                return

            tasks_data = response_data.get('results', [])
            logger.debug(f"接收到 {len(tasks_data)} 个加工任务数据")
            
            # 清空表格以避免重复数据
            self.table.setRowCount(0)
            
            for task in tasks_data:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(task['task_code']))
                self.table.setItem(row, 1, QTableWidgetItem(task.get('processing_type_display', 'N/A')))
                self.table.setItem(row, 2, QTableWidgetItem(task.get('status_display', 'N/A')))
                self.table.setItem(row, 3, QTableWidgetItem(task.get('tool_info', {}).get('code', 'N/A')))
                self.table.setItem(row, 4, QTableWidgetItem(task.get('material_info', {}).get('part_number', 'N/A')))
                self.table.setItem(row, 5, QTableWidgetItem(task.get('group_name', '未分配')))
                self.table.setItem(row, 6, QTableWidgetItem(task.get('operator_info', {}).get('full_name', 'N/A')))
                
                proc_time_str = task.get('processing_time', '').replace('T', ' ').split('.')[0]
                self.table.setItem(row, 7, QTableWidgetItem(proc_time_str))

                # --- 操作按钮 ---
                buttons_widget = QWidget()
                buttons_layout = QHBoxLayout(buttons_widget)
                buttons_layout.setContentsMargins(2, 2, 2, 2)
                buttons_layout.setSpacing(6)
                
                view_button = PrimaryPushButton("查看")
                edit_button = PushButton("编辑")
                clone_button = PushButton("复制")
                delete_button = PushButton("删除")

                view_button.clicked.connect(lambda _, t=task['id']: self.viewDetailSignal.emit(t))
                edit_button.clicked.connect(lambda _, t=task: self.edit_task(t))
                clone_button.clicked.connect(lambda _, t_id=task['id']: self.clone_task(t_id))
                delete_button.clicked.connect(lambda _, t_id=task['id']: self.delete_task(t_id))
                
                buttons_layout.addWidget(view_button)
                buttons_layout.addWidget(edit_button)
                buttons_layout.addWidget(clone_button)
                buttons_layout.addWidget(delete_button)
                self.table.setCellWidget(row, 8, buttons_widget)
            
            # 根据按钮数量动态调整操作列宽度 (4个按钮)
            button_width = 65  # 每个按钮约65px
            spacing = 6  # 按钮间距
            margin = 6  # 边距
            total_width = 4 * button_width + 3 * spacing + 2 * margin
            self.table.horizontalHeader().resizeSection(8, total_width)
            
        except Exception as e:
            logger.error(f"处理加工任务数据时出错: {e}")
    
    def on_tasks_data_error(self, error_message):
        """处理加工任务数据加载错误"""
        try:
            logger.error(f"加工任务数据加载失败: {error_message}")
            if self and hasattr(self, 'parent') and self.parent():
                InfoBar.error("加载失败", f"加工任务数据加载失败: {error_message}", parent=self)
        except Exception as e:
            logger.error(f"处理加工任务数据错误时出错: {e}")


    def add_task(self):
        """ 新增任务 """
        dialog = ProcessingTaskEditDialog(self.window())
        if dialog.exec():
            data, error_msg = dialog.get_data()
            if data:
                response = api_client.add_processing_task(data)
                if response:
                    InfoBar.success("成功", "新任务已添加。", duration=3000, parent=self)
                    self.populate_table(preserve_old_data=False)
                else:
                    InfoBar.error("失败", f"添加任务失败: {response}", duration=5000, parent=self)

    def edit_task(self, task_data):
        """ 编辑任务 """
        dialog = ProcessingTaskEditDialog(self.window(), task_data)
        if dialog.exec():
            data, error_msg = dialog.get_data()
            if data:
                response = api_client.update_processing_task(task_data['id'], data)
                if response:
                    InfoBar.success("成功", "任务已更新。", duration=3000, parent=self)
                    self.populate_table(preserve_old_data=False)
                else:
                    InfoBar.error("失败", f"更新任务失败: {response}", duration=5000, parent=self)

    def clone_task(self, task_id):
        """ 克隆任务 """
        response = api_client.clone_processing_task(task_id)
        if response:
            InfoBar.success("成功", "任务已复制。", parent=self.window())
            self.populate_table(preserve_old_data=False)
        else:
            InfoBar.error("失败", "复制任务失败。", parent=self.window())

    def delete_task(self, task_id):
        """ 删除任务 """
        title = "确认删除"
        content = f"您确定要删除ID为 {task_id} 的任务吗？此操作不可撤销。"
        w = MessageBox(title, content, self.window())
        
        if w.exec():
            success, message = api_client.delete_processing_task(task_id)
            if success:
                InfoBar.success("成功", "任务已删除。", duration=3000, parent=self)
                self.populate_table(preserve_old_data=False)
            else:
                InfoBar.error("失败", f"删除失败: {message}", duration=5000, parent=self)

    def __del__(self):
        """ 确保在销毁时取消工作线程 """
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel()

    def clear_table(self):
        self.table.setRowCount(0)


class ProcessingTaskInterface(QWidget):
    """ 加工任务管理主界面 """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("ProcessingTaskInterface")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
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

        # --- 初始化时不自动加载数据，改为按需加载 ---
        # self.task_list_widget.populate_table()  # 注释掉自动加载

    def show_task_detail(self, task_id: int):
        """ 切换到任务详情页 """
        self.task_detail_interface.load_task_details(task_id)
        self.stackWidget.setCurrentWidget(self.task_detail_interface)

    def show_task_list(self):
        """ 切换回任务列表页 """
        self.stackWidget.setCurrentWidget(self.task_list_widget)
        # 刷新任务列表数据
        self.task_list_widget.populate_table() 