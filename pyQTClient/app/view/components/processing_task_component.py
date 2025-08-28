# coding:utf-8
import logging

from PyQt5.QtCore import Qt, QDateTime, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QAbstractItemView,
                             QGridLayout, QScrollArea, QLabel, QFrame)
from qfluentwidgets import (TableWidget, PushButton, StrongBodyLabel, LineEdit, ComboBox,
                            TextEdit, PrimaryPushButton, MessageBox, InfoBar, MessageBoxBase, SubtitleLabel,
                            DateTimeEdit, FluentIcon as FIF, TransparentPushButton,
                            ScrollArea, ToolButton)

from ...api.api_client import api_client
from ...api.data_manager import interface_loader

# 设置logger
logger = logging.getLogger(__name__)


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
        self.duration_edit = LineEdit(self)  # 预计持续时间
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
            self.set_combo_by_value(self.processing_type_combo, self.TASK_TYPE_CHOICES,
                                    task_data.get('processing_type'))
            self.set_combo_by_data(self.tool_combo, task_data.get('tool'))
            self.set_combo_by_data(self.material_combo, task_data.get('composite_material'))
            self.set_combo_by_data(self.operator_combo, task_data.get('operator'))
            self.set_combo_by_data(self.group_combo, task_data.get('group'))

            self.duration_edit.setText(str(task_data.get('duration', '')))
            self.notes_edit.setText(task_data.get('notes', ''))
            parameters = task_data.get('parameters', [])
        elif group_to_select:
            self.set_combo_by_data(self.group_combo, group_to_select)

        # --- 创建滚动区域 ---
        self.scroll_area = ScrollArea(self)
        self.scroll_content = QWidget()
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        self.scroll_content.setStyleSheet("QWidget { background-color: transparent; }")

        # 滚动区域内的内容布局
        content_layout = QVBoxLayout(self.scroll_content)
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

        # 添加一个伸缩项，确保内容不会被拉伸
        content_layout.addStretch(1)

        # 将滚动区域添加到对话框的主视图中
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.scroll_area)

        # --- 按钮和尺寸 ---
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(750)
        # 设置最大高度，确保滚动区域在内容过多时生效
        self.widget.setMaximumHeight(600)

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
        """ 根据数据找到并选中 combox 里的项目 """
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
            else:  # 如果选择的是"无分组", 则发送 null
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
    """ 显示任务列表的专用小部件 - 卡片式布局 """
    viewDetailSignal = pyqtSignal(int)
    editSignal = pyqtSignal(dict)
    cloneSignal = pyqtSignal(int)
    deleteSignal = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.worker = None
        self.cards = []  # 存储所有任务卡片的引用

        # 关联数据缓存
        self.tool_cache = {}  # tool_id -> tool_code
        self.material_cache = {}  # material_id -> part_number
        self.operator_cache = {}  # operator_id -> full_name
        self.group_cache = {}  # group_id -> group_name

        # 初始化时加载缓存数据
        self.load_cached_data()

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

        # --- 卡片容器 ---
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        self.scroll_widget = QWidget()
        self.scroll_widget.setStyleSheet("QWidget { background-color: transparent; }")
        self.scroll_area.setWidget(self.scroll_widget)

        # 使用网格布局排列卡片，每行显示3个卡片
        self.cards_layout = QGridLayout(self.scroll_widget)
        self.cards_layout.setSpacing(20)
        self.cards_layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(self.scroll_area)

        self._define_column_mapping()

        # --- 信号与槽连接 ---
        self.refresh_button.clicked.connect(self.populate_table)
        self.add_button.clicked.connect(self.add_task)

    def load_cached_data(self):
        """预加载关联数据的ID→名称映射"""
        # 1. 加载刀具
        try:
            tools = api_client.get_tools()
            if tools and 'results' in tools:
                for tool in tools['results']:
                    self.tool_cache[tool['id']] = tool['code']
            logger.debug(f"已加载刀具缓存: {len(self.tool_cache)} 条记录")
        except Exception as e:
            logger.error(f"加载刀具缓存失败: {e}")

        # 2. 加载构件
        try:
            materials = api_client.get_composite_materials()
            if materials and 'results' in materials:
                for mat in materials['results']:
                    self.material_cache[mat['id']] = mat['part_number']
            logger.debug(f"已加载构件缓存: {len(self.material_cache)} 条记录")
        except Exception as e:
            logger.error(f"加载构件缓存失败: {e}")

        # 3. 加载操作员（从用户列表）
        try:
            users = api_client.get_users()
            if users and 'results' in users:
                for user in users['results']:
                    display_name = user.get('full_name') or user.get('username', '')
                    self.operator_cache[user['id']] = display_name
            logger.debug(f"已加载操作员缓存: {len(self.operator_cache)} 条记录")
        except Exception as e:
            logger.error(f"加载操作员缓存失败: {e}")

        # 4. 加载任务分组
        try:
            groups = api_client.get_task_groups()
            if groups and 'results' in groups:
                for group in groups['results']:
                    self.group_cache[group['id']] = group['name']
            logger.debug(f"已加载任务分组缓存: {len(self.group_cache)} 条记录")
        except Exception as e:
            logger.error(f"加载任务分组缓存失败: {e}")

    def _define_column_mapping(self):
        """定义数据映射关系（保持与表格版本兼容）"""
        self.column_mapping = [
            {'key': 'task_code', 'header': '任务编码'},
            {
                'key': 'processing_type',
                'header': '加工类型',
                'formatter': lambda val: next(
                    (disp for (v, disp) in ProcessingTaskEditDialog.TASK_TYPE_CHOICES if v == val),
                    '未知'
                )
            },
            {
                'key': 'status',
                'header': '状态',
                'formatter': lambda val: next(
                    (disp for (v, disp) in ProcessingTaskEditDialog.TASK_STATUS_CHOICES if v == val),
                    '未知'
                )
            },
            {
                'key': 'tool',
                'header': '刀具',
                'formatter': lambda tool_id: self.tool_cache.get(tool_id, 'N/A')
            },
            {
                'key': 'composite_material',
                'header': '构件',
                'formatter': lambda mat_id: self.material_cache.get(mat_id, 'N/A')
            },
            {
                'key': 'group',
                'header': '任务分组',
                'formatter': lambda group_id: self.group_cache.get(group_id, '未分配')
            },
            {
                'key': 'operator',
                'header': '操作员',
                'formatter': lambda op_id: self.operator_cache.get(op_id, 'N/A')
            },
            {
                'key': 'processing_time',
                'header': '加工时间',
                'formatter': lambda processing_time: processing_time.replace('T', ' ').split('.')[
                    0] if processing_time else 'N/A'
            }
        ]

    def populate_table(self, preserve_old_data=True):
        """ 异步从API获取数据并填充卡片 """
        try:
            logger.debug("使用数据管理器加载加工任务数据")
            # 修复：移除不被支持的use_table参数
            self.worker = interface_loader.load_for_interface(
                interface=self,
                data_type='processing_tasks',
                force_refresh=not preserve_old_data,
                preserve_old_data=preserve_old_data,
                column_mapping=self.column_mapping
            )
        except Exception as e:
            logger.error(f"加载加工任务数据时出错: {e}")
            self.on_processing_tasks_data_error(str(e))

    def on_processing_tasks_data_received(self, response_data):
        """处理接收到的加工任务数据，创建卡片"""
        # 清除现有卡片
        for card in self.cards:
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self.cards.clear()

        # 获取任务列表
        tasks = response_data.get('results', [])
        logger.debug(f"接收到加工任务数据: {len(tasks)} 条记录，正在创建卡片")

        # 为每个任务创建卡片
        for i, task in enumerate(tasks):
            # 添加显示用的数据
            task['tool_display'] = self.tool_cache.get(task.get('tool'), 'N/A')
            task['material_display'] = self.material_cache.get(task.get('composite_material'), 'N/A')
            task['operator_display'] = self.operator_cache.get(task.get('operator'), 'N/A')
            task['group_display'] = self.group_cache.get(task.get('group'), '未分配')

            # 创建卡片
            from ..processing_task_interface import TaskCard  # 避免循环导入
            card = TaskCard(task)

            # 连接卡片信号
            card.viewDetailSignal.connect(self.viewDetailSignal.emit)
            card.editSignal.connect(self.edit_task)
            card.cloneSignal.connect(self.clone_task)
            card.deleteSignal.connect(self.delete_task)

            # 计算网格位置（每行3个卡片）
            row = i // 3
            col = i % 3

            # 添加到布局
            self.cards_layout.addWidget(card, row, col)
            self.cards.append(card)

    def on_processing_tasks_data_error(self, error):
        """数据管理器使用的标准错误回调方法"""
        logger.error(f"加载任务数据出错: {error}")
        InfoBar.error(
            "数据加载失败",
            f"无法加载加工任务数据: {error}",
            duration=5000,
            parent=self
        )

    def on_tasks_data_received(self, response_data):
        """处理接收到的加工任务数据（现在主要用于日志记录）"""
        logger.debug(f"接收到加工任务数据: {len(response_data.get('results', []))} 条记录")

    def add_task(self):
        """添加新任务"""
        dialog = ProcessingTaskEditDialog(parent=self)
        if dialog.exec_():
            task_data, error = dialog.get_data()
            if task_data:
                try:
                    # 调用API创建新任务
                    response = api_client.create_processing_task(task_data)
                    if response:
                        InfoBar.success("成功", "任务创建成功", duration=3000, parent=self)
                        self.populate_table(preserve_old_data=False)
                    else:
                        InfoBar.error("失败", "创建任务失败", duration=3000, parent=self)
                except Exception as e:
                    logger.error(f"创建任务时出错: {e}")
                    InfoBar.error("错误", f"创建任务失败: {str(e)}", duration=3000, parent=self)

    def edit_task(self, task):
        """编辑现有任务"""
        dialog = ProcessingTaskEditDialog(parent=self, task_data=task)
        if dialog.exec_():
            task_data, error = dialog.get_data()
            if task_data:
                try:
                    # 调用API更新任务
                    response = api_client.update_processing_task(task['id'], task_data)
                    if response:
                        InfoBar.success("成功", "任务更新成功", duration=3000, parent=self)
                        self.populate_table(preserve_old_data=False)
                    else:
                        InfoBar.error("失败", "更新任务失败", duration=3000, parent=self)
                except Exception as e:
                    logger.error(f"更新任务时出错: {e}")
                    InfoBar.error("错误", f"更新任务失败: {str(e)}", duration=3000, parent=self)

    def clone_task(self, task_id):
        """复制任务"""
        try:
            # 获取原始任务数据
            task = api_client.get_processing_task(task_id)
            if task:
                # 创建新任务对话框，预填充原始任务数据
                # 清除任务ID和编码，确保是新任务
                cloned_task = task.copy()
                cloned_task.pop('id', None)
                cloned_task['task_code'] = f"{cloned_task.get('task_code', 'TASK')}_COPY"

                dialog = ProcessingTaskEditDialog(parent=self, task_data=cloned_task)
                if dialog.exec_():
                    task_data, error = dialog.get_data()
                    if task_data:
                        # 调用API创建复制的任务
                        response = api_client.create_processing_task(task_data)
                        if response:
                            InfoBar.success("成功", "任务复制成功", duration=3000, parent=self)
                            self.populate_table(preserve_old_data=False)
        except Exception as e:
            logger.error(f"复制任务时出错: {e}")
            InfoBar.error("错误", f"复制任务失败: {str(e)}", duration=3000, parent=self)

    def delete_task(self, task_id):
        """删除任务"""
        # 显示确认对话框
        msg_box = MessageBox("确认删除", f"确定要删除ID为 {task_id} 的任务吗？", self)
        msg_box.yesButton.setText("删除")
        msg_box.cancelButton.setText("取消")

        if msg_box.exec_():
            try:
                # 调用API删除任务
                success = api_client.delete_processing_task(task_id)
                if success:
                    InfoBar.success("成功", "任务已删除", duration=3000, parent=self)
                    self.populate_table(preserve_old_data=False)
                else:
                    InfoBar.error("失败", "删除任务失败", duration=3000, parent=self)
            except Exception as e:
                logger.error(f"删除任务时出错: {e}")
                InfoBar.error("错误", f"删除任务失败: {str(e)}", duration=3000, parent=self)
