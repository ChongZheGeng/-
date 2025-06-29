# coding:utf-8

import logging

from qfluentwidgets import (StrongBodyLabel, LineEdit, ComboBox,
                            TextEdit, InfoBar, MessageBoxBase, SubtitleLabel)

# 设置logger
logger = logging.getLogger(__name__)


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
