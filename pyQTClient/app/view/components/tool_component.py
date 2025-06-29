# coding:utf-8

import logging

from qfluentwidgets import (StrongBodyLabel, LineEdit, ComboBox,
                            TextEdit, InfoBar, MessageBoxBase, SubtitleLabel)

# 设置logger
logger = logging.getLogger(__name__)


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
