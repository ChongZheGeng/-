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
        
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        self._define_column_mapping()

        # --- 信号与槽连接 ---
        self.refresh_button.clicked.connect(self.populate_table)
        self.add_button.clicked.connect(self.add_task)
        
    def _define_column_mapping(self):
        """定义表格的列映射关系"""
        self.column_mapping = [
            {'key': 'task_code', 'header': '任务编码'},
            {'key': 'processing_type_display', 'header': '加工类型'},
            {'key': 'status_display', 'header': '状态'},
            {
                'key': 'tool_info', 
                'header': '刀具',
                'formatter': lambda tool_info: tool_info.get('code', 'N/A') if tool_info else 'N/A'
            },
            {
                'key': 'material_info', 
                'header': '构件',
                'formatter': lambda material_info: material_info.get('part_number', 'N/A') if material_info else 'N/A'
            },
            {'key': 'group_name', 'header': '任务分组', 'formatter': lambda group_name: group_name or '未分配'},
            {
                'key': 'operator_info', 
                'header': '操作员',
                'formatter': lambda operator_info: operator_info.get('full_name', 'N/A') if operator_info else 'N/A'
            },
            {
                'key': 'processing_time', 
                'header': '加工时间',
                'formatter': lambda processing_time: processing_time.replace('T', ' ').split('.')[0] if processing_time else 'N/A'
            },
            {
                'type': 'buttons',
                'header': '操作',
                'width': 280,
                'buttons': [
                    {'text': '查看', 'style': 'primary', 'callback': lambda task: self.viewDetailSignal.emit(task['id'])},
                    {'text': '编辑', 'style': 'default', 'callback': self.edit_task},
                    {'text': '复制', 'style': 'default', 'callback': lambda task: self.clone_task(task['id'])},
                    {'text': '删除', 'style': 'default', 'callback': lambda task: self.delete_task(task['id'])}
                ]
            }
        ]
        
    def populate_table(self, preserve_old_data=True):
        """ 异步从API获取数据并填充表格 """
        try:
            logger.debug("使用数据管理器加载加工任务数据")
            self.worker = interface_loader.load_for_interface(
                interface=self,
                data_type='processing_tasks',
                table_widget=self.table,
                force_refresh=not preserve_old_data,
                preserve_old_data=preserve_old_data,
                column_mapping=self.column_mapping
            )
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
        """处理接收到的加工任务数据（现在主要用于日志记录或额外操作）"""
        # 当使用了 column_mapping 自动填充时，表格填充已由 InterfaceDataLoader 自动处理
        # 这里只进行日志记录和任何需要的额外操作
        if hasattr(self, 'column_mapping') and self.column_mapping:
            total = response_data.get('count', 0)
            logger.info(f"TaskListWidget 成功接收并处理了 {total} 条加工任务数据。")
            return
        
        # 如果没有使用自动填充，则保留原有的手动处理逻辑
        # （这部分代码在当前实现中已经被移除，因为我们已经完全转向自动填充）
        logger.warning("TaskListWidget 未使用自动填充配置，但手动填充逻辑已被移除")
    
    def on_tasks_data_error(self, error_message):
        """处理加工任务数据加载错误"""
        # InfoBar 错误提示已由 InterfaceDataLoader 自动处理
        logger.error(f"加工任务数据加载失败: {error_message}")

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


class ProcessingTaskInterface(NavInterface):
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