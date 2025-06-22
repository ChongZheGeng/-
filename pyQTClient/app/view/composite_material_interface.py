# coding:utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QAbstractItemView

from qfluentwidgets import (TableWidget, PushButton, StrongBodyLabel, LineEdit, ComboBox,
                            TextEdit, PrimaryPushButton, MessageBox, InfoBar, MessageBoxBase, SubtitleLabel)

from ..api.api_client import api_client


class CompositeMaterialEditDialog(MessageBoxBase):
    """ 用于编辑或添加复合材料的自定义对话框 """
    MATERIAL_TYPE_CHOICES = [
        ('carbon_fiber', '碳纤维'),
        ('glass_fiber', '玻璃纤维'),
        ('aramid', '芳纶'),
        ('hybrid', '混合材料'),
        ('other', '其他'),
    ]

    def __init__(self, parent=None, material_data=None):
        super().__init__(parent)
        self.material_data = material_data
        is_edit_mode = material_data is not None

        # 设置标题
        self.titleLabel = SubtitleLabel("编辑构件" if is_edit_mode else "新增构件", self)
        self.viewLayout.addWidget(self.titleLabel)

        # 创建输入字段
        self.part_number_label = StrongBodyLabel("构件编号:", self)
        self.part_number_edit = LineEdit(self)

        self.material_type_label = StrongBodyLabel("材料类型:", self)
        self.material_type_combo = ComboBox(self)

        self.thickness_label = StrongBodyLabel("厚度(mm):", self)
        self.thickness_edit = LineEdit(self)

        self.processing_reqs_label = StrongBodyLabel("加工要求:", self)
        self.processing_reqs_edit = TextEdit(self)
        self.processing_reqs_edit.setMinimumHeight(60)

        self.description_label = StrongBodyLabel("描述:", self)
        self.description_edit = TextEdit(self)
        self.description_edit.setMinimumHeight(80)

        # 填充材料类型下拉框
        for _, display_name in self.MATERIAL_TYPE_CHOICES:
            self.material_type_combo.addItem(display_name)

        # 如果是编辑模式，则填充现有数据
        if is_edit_mode:
            self.part_number_edit.setText(material_data.get('part_number', ''))
            self.thickness_edit.setText(str(material_data.get('thickness', '')))
            self.processing_reqs_edit.setText(material_data.get('processing_requirements', ''))
            self.description_edit.setText(material_data.get('description', ''))
            material_type_value = material_data.get('material_type', 'other')
            for index, (value, _) in enumerate(self.MATERIAL_TYPE_CHOICES):
                if value == material_type_value:
                    self.material_type_combo.setCurrentIndex(index)
                    break

        # 将控件添加到布局中
        self.viewLayout.addWidget(self.part_number_label)
        self.viewLayout.addWidget(self.part_number_edit)
        self.viewLayout.addWidget(self.material_type_label)
        self.viewLayout.addWidget(self.material_type_combo)
        self.viewLayout.addWidget(self.thickness_label)
        self.viewLayout.addWidget(self.thickness_edit)
        self.viewLayout.addWidget(self.processing_reqs_label)
        self.viewLayout.addWidget(self.processing_reqs_edit)
        self.viewLayout.addWidget(self.description_label)
        self.viewLayout.addWidget(self.description_edit)

        # 修改按钮文本
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        
        # 设置对话框大小
        self.widget.setMinimumWidth(450)

    def get_data(self):
        """ 获取表单中的数据 """
        try:
            # 检查必填字段
            if not self.part_number_edit.text().strip():
                return None, "构件编号不能为空"
            
            thickness_text = self.thickness_edit.text().strip()
            if not thickness_text:
                return None, "厚度不能为空"
            
            try:
                thickness_value = float(thickness_text)
                if thickness_value <= 0:
                    return None, "厚度必须是正数"
            except ValueError:
                return None, "厚度必须是有效的数字"

            if self.material_type_combo.currentIndex() < 0:
                return None, "请选择材料类型"

            material_type_value = self.MATERIAL_TYPE_CHOICES[self.material_type_combo.currentIndex()][0]

            return {
                "part_number": self.part_number_edit.text().strip(),
                "material_type": material_type_value,
                "thickness": float(thickness_text),
                "processing_requirements": self.processing_reqs_edit.toPlainText().strip(),
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


class CompositeMaterialInterface(QWidget):
    """ 复合材料构件管理主界面 """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("CompositeMaterialInterface")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        self.main_layout.addWidget(SubtitleLabel("复合材料构件管理"))

        # --- 工具栏 ---
        toolbar_layout = QHBoxLayout()
        self.add_button = PrimaryPushButton("新增构件")
        self.refresh_button = PushButton("刷新数据")
        toolbar_layout.addWidget(self.add_button)
        toolbar_layout.addWidget(self.refresh_button)
        toolbar_layout.addStretch(1)
        self.main_layout.addLayout(toolbar_layout)

        # --- 数据表格 ---
        self.table = TableWidget(self)
        self.main_layout.addWidget(self.table)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "构件编号", "材料类型", "厚度(mm)", "创建时间", "更新时间", "操作"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)

        # --- 信号与槽连接 ---
        self.refresh_button.clicked.connect(self.populate_table)
        self.add_button.clicked.connect(self.add_material)

        # --- 初始加载数据 ---
        self.populate_table()

    def populate_table(self):
        """ 从API获取数据并填充表格 """
        response_data = api_client.get_composite_materials()
        if response_data is None:
            InfoBar.error("错误", "无法从服务器获取数据，请确保后端服务已运行。", duration=3000, parent=self)
            return

        materials_data = response_data.get('results', [])
        
        self.table.setRowCount(0)
        for material in materials_data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(material['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(material['part_number']))
            self.table.setItem(row, 2, QTableWidgetItem(material.get('material_type_display', material['material_type'])))
            self.table.setItem(row, 3, QTableWidgetItem(str(material['thickness'])))
            self.table.setItem(row, 4, QTableWidgetItem(material.get('created_at', 'N/A').split('T')[0]))
            self.table.setItem(row, 5, QTableWidgetItem(material.get('updated_at', 'N/A').split('T')[0]))

            # 操作按钮
            edit_button = PushButton("编辑")
            delete_button = PushButton("删除")
            edit_button.clicked.connect(lambda _, m=material: self.edit_material(m))
            delete_button.clicked.connect(lambda _, m_id=material['id']: self.delete_material(m_id))
            
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.addWidget(edit_button)
            action_layout.addWidget(delete_button)
            action_layout.setContentsMargins(5, 2, 5, 2)
            self.table.setCellWidget(row, 6, action_widget)
            
        InfoBar.success("成功", "数据已刷新", duration=1500, parent=self)

    def add_material(self):
        """ 弹出新增对话框 """
        dialog = CompositeMaterialEditDialog(self)
        if dialog.exec():
            data, _ = dialog.get_data()
            if data and api_client.add_composite_material(data):
                InfoBar.success("成功", "新增构件成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "新增构件失败，请查看控制台输出。", duration=3000, parent=self)

    def edit_material(self, material_data):
        """ 弹出编辑对话框 """
        dialog = CompositeMaterialEditDialog(self, material_data)
        if dialog.exec():
            data, _ = dialog.get_data()
            if data and api_client.update_composite_material(material_data['id'], data):
                InfoBar.success("成功", "更新构件成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "更新构件失败，请查看控制台输出。", duration=3000, parent=self)

    def delete_material(self, material_id):
        """ 删除构件 """
        msg_box = MessageBox("确认删除", f"您确定要删除 ID 为 {material_id} 的构件吗？", self.window())
        if msg_box.exec():
            if api_client.delete_composite_material(material_id):
                InfoBar.success("成功", "删除成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "删除失败", duration=3000, parent=self) 