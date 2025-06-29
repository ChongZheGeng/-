# coding:utf-8

import logging

from qfluentwidgets import (LineEdit, MessageBoxBase, SubtitleLabel)

# 设置logger
logger = logging.getLogger(__name__)


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
