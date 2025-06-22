# coding:utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QAbstractItemView

from qfluentwidgets import (TableWidget, PushButton, StrongBodyLabel, LineEdit, ComboBox,
                            TextEdit, PrimaryPushButton, MessageBox, InfoBar, MessageBoxBase, SubtitleLabel)

from ..api.api_client import api_client


class ToolEditDialog(MessageBoxBase):
    """ 用于编辑或添加刀具的自定义对话框 """
    TOOL_STATUS_CHOICES = [
        ('normal', '正常'),
        ('warning', '警告'),
        ('worn', '已磨损'),
        ('broken', '损坏'),
        ('maintenance', '维护中'),
    ]

    def __init__(self, parent=None, tool_data=None):
        super().__init__(parent)
        self.tool_data = tool_data
        is_edit_mode = tool_data is not None

        # 设置标题
        self.titleLabel = SubtitleLabel("编辑刀具" if is_edit_mode else "新增刀具", self)
        self.viewLayout.addWidget(self.titleLabel)
        
        # 创建输入字段
        self.tool_type_label = StrongBodyLabel("刀具类型:", self)
        self.tool_type_edit = LineEdit(self)
        
        self.tool_spec_label = StrongBodyLabel("刀具规格:", self)
        self.tool_spec_edit = LineEdit(self)
        
        self.code_label = StrongBodyLabel("刀具编码:", self)
        self.code_edit = LineEdit(self)
        
        self.threshold_label = StrongBodyLabel("初始磨损阈值:", self)
        self.threshold_edit = LineEdit(self)
        
        self.status_label = StrongBodyLabel("当前状态:", self)
        self.status_combo = ComboBox(self)
        
        self.description_label = StrongBodyLabel("描述:", self)
        self.description_edit = TextEdit(self)
        self.description_edit.setMinimumHeight(80)

        # 填充状态下拉框
        for _, display_name in self.TOOL_STATUS_CHOICES:
            self.status_combo.addItem(display_name)

        # 如果是编辑模式，则填充现有数据
        if is_edit_mode:
            self.tool_type_edit.setText(tool_data.get('tool_type', ''))
            self.tool_spec_edit.setText(tool_data.get('tool_spec', ''))
            self.code_edit.setText(tool_data.get('code', ''))
            self.threshold_edit.setText(str(tool_data.get('initial_wear_threshold', '')))
            self.description_edit.setText(tool_data.get('description', ''))
            status_value = tool_data.get('current_status', 'normal')
            for index, (value, _) in enumerate(self.TOOL_STATUS_CHOICES):
                if value == status_value:
                    self.status_combo.setCurrentIndex(index)
                    break

        # 将控件添加到布局中
        self.viewLayout.addWidget(self.tool_type_label)
        self.viewLayout.addWidget(self.tool_type_edit)
        self.viewLayout.addWidget(self.tool_spec_label)
        self.viewLayout.addWidget(self.tool_spec_edit)
        self.viewLayout.addWidget(self.code_label)
        self.viewLayout.addWidget(self.code_edit)
        self.viewLayout.addWidget(self.threshold_label)
        self.viewLayout.addWidget(self.threshold_edit)
        self.viewLayout.addWidget(self.status_label)
        self.viewLayout.addWidget(self.status_combo)
        self.viewLayout.addWidget(self.description_label)
        self.viewLayout.addWidget(self.description_edit)

        # 修改按钮文本
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        
        # 设置对话框大小
        self.widget.setMinimumWidth(400)

    def get_data(self):
        """ 获取表单中的数据 """
        try:
            # 检查必填字段
            if not self.tool_type_edit.text().strip():
                return None, "刀具类型不能为空"
            
            if not self.tool_spec_edit.text().strip():
                return None, "刀具规格不能为空"
            
            if not self.code_edit.text().strip():
                return None, "刀具编码不能为空"
            
            # 检查阈值是否为有效的浮点数
            threshold_text = self.threshold_edit.text().strip()
            if not threshold_text:
                return None, "初始磨损阈值不能为空"
            
            try:
                threshold_value = float(threshold_text)
                if threshold_value < 0:
                    return None, "初始磨损阈值必须是正数"
            except ValueError:
                return None, "初始磨损阈值必须是有效的数字"
            
            # 获取状态值
            if self.status_combo.currentIndex() < 0:
                return None, "请选择刀具状态"
                
            status_value = self.TOOL_STATUS_CHOICES[self.status_combo.currentIndex()][0]
            
            return {
                "tool_type": self.tool_type_edit.text().strip(),
                "tool_spec": self.tool_spec_edit.text().strip(),
                "code": self.code_edit.text().strip(),
                "initial_wear_threshold": float(threshold_text),
                "current_status": status_value,
                "description": self.description_edit.toPlainText().strip(),
            }, None
            
        except (ValueError, IndexError) as e:
            return None, f"数据格式错误: {str(e)}"

    def validate(self):
        """ 重写验证方法 """
        data, error_msg = self.get_data()
        if data is None:
            InfoBar.warning("提示", error_msg, duration=3000, parent=self)
            return False
        return True


class ToolInterface(QWidget):
    """ 刀具管理主界面 """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("ToolInterface")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        self.main_layout.addWidget(SubtitleLabel("刀具信息管理"))

        # --- 工具栏 ---
        toolbar_layout = QHBoxLayout()
        self.add_button = PrimaryPushButton("新增刀具")
        self.refresh_button = PushButton("刷新数据")
        toolbar_layout.addWidget(self.add_button)
        toolbar_layout.addWidget(self.refresh_button)
        toolbar_layout.addStretch(1)
        self.main_layout.addLayout(toolbar_layout)

        # --- 数据表格 ---
        self.table = TableWidget(self)
        self.main_layout.addWidget(self.table)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "类型", "规格", "编码", "状态", "创建时间", "更新时间", "操作"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)

        # --- 信号与槽连接 ---
        self.refresh_button.clicked.connect(self.populate_table)
        self.add_button.clicked.connect(self.add_tool)

        # --- 初始加载数据 ---
        self.populate_table()

    def populate_table(self):
        """ 从API获取数据并填充表格 """
        response_data = api_client.get_tools()
        if response_data is None:
            InfoBar.error("错误", "无法从服务器获取数据，请确保后端服务已运行。", duration=3000, parent=self)
            return

        tools_data = response_data.get('results', [])
        
        self.table.setRowCount(0)
        for tool in tools_data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(tool['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(tool['tool_type']))
            self.table.setItem(row, 2, QTableWidgetItem(tool['tool_spec']))
            self.table.setItem(row, 3, QTableWidgetItem(tool['code']))
            self.table.setItem(row, 4, QTableWidgetItem(tool.get('get_current_status_display', tool['current_status'])))
            self.table.setItem(row, 5, QTableWidgetItem(tool.get('created_at', 'N/A').split('T')[0]))
            self.table.setItem(row, 6, QTableWidgetItem(tool.get('updated_at', 'N/A').split('T')[0]))

            # 操作按钮
            edit_button = PushButton("编辑")
            delete_button = PushButton("删除")
            edit_button.clicked.connect(lambda _, t=tool: self.edit_tool(t))
            delete_button.clicked.connect(lambda _, t_id=tool['id']: self.delete_tool(t_id))
            
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.addWidget(edit_button)
            action_layout.addWidget(delete_button)
            action_layout.setContentsMargins(5, 2, 5, 2)
            self.table.setCellWidget(row, 7, action_widget)
            
        InfoBar.success("成功", "数据已刷新", duration=1500, parent=self)

    def add_tool(self):
        """ 弹出新增对话框 """
        dialog = ToolEditDialog(self)
        if dialog.exec():
            data, _ = dialog.get_data()
            result = api_client.add_tool(data)
            if result:
                InfoBar.success("成功", "新增成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "新增失败，请查看控制台输出。", duration=3000, parent=self)

    def edit_tool(self, tool_data):
        """ 弹出编辑对话框 """
        dialog = ToolEditDialog(self, tool_data)
        if dialog.exec():
            data, _ = dialog.get_data()
            result = api_client.update_tool(tool_data['id'], data)
            if result:
                InfoBar.success("成功", "更新成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "更新失败，请查看控制台输出。", duration=3000, parent=self)

    def delete_tool(self, tool_id):
        """ 删除刀具 """
        msg_box = MessageBox("确认删除", f"您确定要删除 ID 为 {tool_id} 的刀具吗？", self.window())
        if msg_box.exec():
            if api_client.delete_tool(tool_id):
                InfoBar.success("成功", "删除成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "删除失败", duration=3000, parent=self) 