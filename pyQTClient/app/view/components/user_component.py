# coding:utf-8
import logging

from PyQt5.QtWidgets import QCheckBox
from qfluentwidgets import (StrongBodyLabel, LineEdit, InfoBar, MessageBoxBase,
                            SubtitleLabel, PasswordLineEdit)

# 设置logger
logger = logging.getLogger(__name__)


class UserEditDialog(MessageBoxBase):
    """ 用于编辑或添加用户的自定义对话框 """

    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.user_data = user_data
        self.is_edit_mode = user_data is not None

        self.titleLabel = SubtitleLabel("编辑用户" if self.is_edit_mode else "新增用户", self)
        self.viewLayout.addWidget(self.titleLabel)

        # --- 创建表单控件 ---
        self.username_label = StrongBodyLabel("用户名:", self)
        self.username_edit = LineEdit(self)

        self.password_label = StrongBodyLabel("密码:", self)
        self.password_edit = PasswordLineEdit(self)

        self.first_name_label = StrongBodyLabel("名字:", self)
        self.first_name_edit = LineEdit(self)

        self.last_name_label = StrongBodyLabel("姓氏:", self)
        self.last_name_edit = LineEdit(self)

        self.email_label = StrongBodyLabel("邮箱:", self)
        self.email_edit = LineEdit(self)

        self.is_active_checkbox = QCheckBox("是否激活", self)
        self.is_staff_checkbox = QCheckBox("是否职员", self)

        # --- 布局 ---
        self.viewLayout.addWidget(self.username_label)
        self.viewLayout.addWidget(self.username_edit)
        self.viewLayout.addWidget(self.password_label)
        self.viewLayout.addWidget(self.password_edit)
        self.viewLayout.addWidget(self.first_name_label)
        self.viewLayout.addWidget(self.first_name_edit)
        self.viewLayout.addWidget(self.last_name_label)
        self.viewLayout.addWidget(self.last_name_edit)
        self.viewLayout.addWidget(self.email_label)
        self.viewLayout.addWidget(self.email_edit)
        self.viewLayout.addWidget(self.is_active_checkbox)
        self.viewLayout.addWidget(self.is_staff_checkbox)

        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(400)

        # --- 根据模式设置初始值和控件状态 ---
        self.setup_mode()

    def setup_mode(self):
        """ 根据是编辑模式还是新增模式来设置控件 """
        if self.is_edit_mode:
            self.username_edit.setText(self.user_data.get('username', ''))
            self.username_edit.setReadOnly(True)  # 用户名通常不允许修改
            self.password_edit.setPlaceholderText("留空表示不修改密码")

            self.first_name_edit.setText(self.user_data.get('first_name', ''))
            self.last_name_edit.setText(self.user_data.get('last_name', ''))
            self.email_edit.setText(self.user_data.get('email', ''))
            self.is_active_checkbox.setChecked(self.user_data.get('is_active', True))
            self.is_staff_checkbox.setChecked(self.user_data.get('is_staff', False))
        else:
            # 新增模式
            self.username_edit.setPlaceholderText("必填")
            self.password_edit.setPlaceholderText("必填")
            self.is_active_checkbox.setChecked(True)

    def get_data(self):
        """ 获取表单中的数据 """
        username = self.username_edit.text().strip()
        if not username:
            return None, "用户名不能为空"

        data = {
            "username": username,
            "first_name": self.first_name_edit.text().strip(),
            "last_name": self.last_name_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "is_active": self.is_active_checkbox.isChecked(),
            "is_staff": self.is_staff_checkbox.isChecked(),
        }

        # 处理密码
        password = self.password_edit.text()
        if not self.is_edit_mode and not password:
            return None, "新增用户时密码不能为空"
        if password:
            data['password'] = password

        return data, None

    def validate(self):
        data, error_msg = self.get_data()
        if data is None:
            InfoBar.warning("提示", error_msg, duration=3000, parent=self)
            return False
        return True
