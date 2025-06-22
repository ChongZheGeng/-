# coding:utf-8
from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QAbstractItemView

from qfluentwidgets import (TableWidget, PushButton, StrongBodyLabel, LineEdit, ComboBox,
                            TextEdit, PrimaryPushButton, MessageBox, InfoBar, MessageBoxBase, SubtitleLabel,
                            DateTimeEdit)

from ..api.api_client import api_client


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

    def __init__(self, parent=None, task_data=None):
        super().__init__(parent)
        self.task_data = task_data
        is_edit_mode = task_data is not None

        # 设置标题
        self.titleLabel = SubtitleLabel("编辑任务" if is_edit_mode else "新增任务", self)
        self.viewLayout.addWidget(self.titleLabel)

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

        # --- 填充下拉框 ---
        for _, display in self.TASK_TYPE_CHOICES: self.processing_type_combo.addItem(display)
        for _, display in self.TASK_STATUS_CHOICES: self.status_combo.addItem(display)
        
        # 动态加载刀具、材料和人员
        self.load_tools()
        self.load_materials()
        self.load_operators()

        # --- 如果是编辑模式，则填充现有数据 ---
        if is_edit_mode:
            self.task_code_edit.setText(task_data.get('task_code', ''))
            proc_time = QDateTime.fromString(task_data.get('processing_time', ''), Qt.ISODate)
            self.processing_time_edit.setDateTime(proc_time)
            
            # 设置下拉框的选中项
            self.set_combo_by_value(self.processing_type_combo, self.TASK_TYPE_CHOICES, task_data.get('processing_type'))
            self.set_combo_by_data(self.tool_combo, task_data.get('tool'))
            self.set_combo_by_data(self.material_combo, task_data.get('composite_material'))
            self.set_combo_by_value(self.status_combo, self.TASK_STATUS_CHOICES, task_data.get('status'))
            self.set_combo_by_data(self.operator_combo, task_data.get('operator'))
            
            self.duration_edit.setText(str(task_data.get('duration', '')))
            self.notes_edit.setText(task_data.get('notes', ''))

        # --- 将控件添加到布局中 (新布局) ---
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)

        def create_field_row(label1_text, widget1, label2_text, widget2):
            row_layout = QHBoxLayout()
            row_layout.addWidget(StrongBodyLabel(label1_text))
            row_layout.addWidget(widget1)
            row_layout.addSpacing(20)
            row_layout.addWidget(StrongBodyLabel(label2_text))
            row_layout.addWidget(widget2)
            return row_layout

        # 第1行：任务编码 和 操作员
        form_layout.addLayout(create_field_row("任务编码:", self.task_code_edit, "操作员:", self.operator_combo))
        
        # 第2行：加工时间 和 预计耗时
        form_layout.addLayout(create_field_row("加工时间:", self.processing_time_edit, "预计耗时(分钟):", self.duration_edit))

        # 第3行：加工类型 和 任务状态
        form_layout.addLayout(create_field_row("加工类型:", self.processing_type_combo, "任务状态:", self.status_combo))
        
        # 第4行：选用刀具
        self.tool_combo.setMinimumWidth(300)
        form_layout.addWidget(StrongBodyLabel("选用刀具:", self))
        form_layout.addWidget(self.tool_combo)
        
        # 第5行：加工构件
        self.material_combo.setMinimumWidth(300)
        form_layout.addWidget(StrongBodyLabel("加工构件:", self))
        form_layout.addWidget(self.material_combo)
        
        # 第6行：备注
        form_layout.addWidget(StrongBodyLabel("备注:", self))
        form_layout.addWidget(self.notes_edit)

        self.viewLayout.addLayout(form_layout)

        # --- 按钮和尺寸 ---
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(600)

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

    def set_combo_by_value(self, combo, choices, value_to_find):
        for index, (val, _) in enumerate(choices):
            if val == value_to_find:
                combo.setCurrentIndex(index)
                return
    
    def set_combo_by_data(self, combo, data_to_find):
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
            
            duration = self.duration_edit.text().strip()
            if duration and not duration.isdigit():
                return None, "预计耗时必须是整数"

            return {
                "task_code": self.task_code_edit.text().strip(),
                "processing_time": self.processing_time_edit.dateTime().toString(Qt.ISODate),
                "processing_type": proc_type,
                "tool": tool_id,
                "composite_material": material_id,
                "status": status,
                "duration": int(duration) if duration else None,
                "operator": operator_id,
                "notes": self.notes_edit.toPlainText().strip(),
            }, None

        except (ValueError, IndexError) as e:
            return None, f"数据格式错误: {str(e)}"

    def validate(self):
        data, error_msg = self.get_data()
        if data is None:
            InfoBar.warning("提示", error_msg, duration=3000, parent=self)
            return False
        return True


class ProcessingTaskInterface(QWidget):
    """ 加工任务管理主界面 """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("ProcessingTaskInterface")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        self.main_layout.addWidget(SubtitleLabel("加工任务管理"))

        # --- 工具栏 ---
        toolbar_layout = QHBoxLayout()
        self.add_button = PrimaryPushButton("新增任务")
        self.refresh_button = PushButton("刷新数据")
        toolbar_layout.addWidget(self.add_button)
        toolbar_layout.addWidget(self.refresh_button)
        toolbar_layout.addStretch(1)
        self.main_layout.addLayout(toolbar_layout)

        # --- 数据表格 ---
        self.table = TableWidget(self)
        self.main_layout.addWidget(self.table)
        self.table.setColumnCount(9)
        headers = ["ID", "任务编码", "加工类型", "状态", "刀具", "构件", "操作员", "加工时间", "操作"]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)

        # --- 信号与槽连接 ---
        self.refresh_button.clicked.connect(self.populate_table)
        self.add_button.clicked.connect(self.add_task)

        # --- 初始加载数据 ---
        self.populate_table()

    def populate_table(self):
        """ 从API获取数据并填充表格 """
        response_data = api_client.get_processing_tasks()
        if response_data is None:
            InfoBar.error("错误", "无法从服务器获取数据。", duration=3000, parent=self)
            return

        tasks_data = response_data.get('results', [])
        
        self.table.setRowCount(0)
        for task in tasks_data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(task['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(task['task_code']))
            self.table.setItem(row, 2, QTableWidgetItem(task.get('processing_type_display', '')))
            self.table.setItem(row, 3, QTableWidgetItem(task.get('status_display', '')))
            self.table.setItem(row, 4, QTableWidgetItem(task.get('tool_code', '')))
            self.table.setItem(row, 5, QTableWidgetItem(task.get('material_part_number', '')))
            self.table.setItem(row, 6, QTableWidgetItem(task.get('operator_name', '')))
            time_str = task.get('processing_time', 'N/A').replace('T', ' ').split('.')[0]
            self.table.setItem(row, 7, QTableWidgetItem(time_str))

            # 操作按钮
            edit_button = PushButton("编辑")
            delete_button = PushButton("删除")
            edit_button.clicked.connect(lambda _, t=task: self.edit_task(t))
            delete_button.clicked.connect(lambda _, t_id=task['id']: self.delete_task(t_id))
            
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.addWidget(edit_button)
            action_layout.addWidget(delete_button)
            action_layout.setContentsMargins(5, 2, 5, 2)
            self.table.setCellWidget(row, 8, action_widget)
            
        InfoBar.success("成功", "数据已刷新", duration=1500, parent=self)

    def add_task(self):
        """ 弹出新增对话框 """
        dialog = ProcessingTaskEditDialog(self)
        if dialog.exec():
            data, _ = dialog.get_data()
            if data and api_client.add_processing_task(data):
                InfoBar.success("成功", "新增任务成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "新增任务失败。", duration=3000, parent=self)

    def edit_task(self, task_data):
        """ 弹出编辑对话框 """
        dialog = ProcessingTaskEditDialog(self, task_data)
        if dialog.exec():
            data, _ = dialog.get_data()
            if data and api_client.update_processing_task(task_data['id'], data):
                InfoBar.success("成功", "更新任务成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "更新任务失败。", duration=3000, parent=self)

    def delete_task(self, task_id):
        """ 删除任务 """
        msg_box = MessageBox("确认删除", f"您确定要删除 ID 为 {task_id} 的任务吗？", self.window())
        if msg_box.exec():
            if api_client.delete_processing_task(task_id):
                InfoBar.success("成功", "删除成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "删除失败", duration=3000, parent=self) 