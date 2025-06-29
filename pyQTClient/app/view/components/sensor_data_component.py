# coding:utf-8
import logging

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QFileDialog
from qfluentwidgets import (StrongBodyLabel, LineEdit, ComboBox,
                            PrimaryPushButton, MessageBoxBase, SubtitleLabel,
                            CaptionLabel, TextEdit)

from ...api.api_client import api_client

# 设置logger
logger = logging.getLogger(__name__)

import os


# 移除重复的上传进度对话框类，使用统一的文件传输管理器


class SensorDataUploadDialog(MessageBoxBase):
    """ 用于上传传感器数据文件的对话框 """
    SENSOR_TYPE_CHOICES = [
        ('temperature', '温度'), ('vibration', '振动'), ('force', '力'),
        ('acoustic', '声学'), ('current', '电流'), ('other', '其他'),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_file_path = None

        self.titleLabel = SubtitleLabel("上传传感器数据文件", self)

        # --- 输入字段 ---
        self.sensor_type_combo = ComboBox(self)
        self.sensor_id_edit = LineEdit(self)
        self.task_combo = ComboBox(self)
        self.description_edit = TextEdit(self)
        self.description_edit.setMaximumHeight(80)

        # 文件选择
        self.file_path_edit = LineEdit(self)
        self.file_path_edit.setReadOnly(True)
        self.file_select_button = PrimaryPushButton("选择文件", self)
        self.file_select_button.clicked.connect(self.select_file)

        self.warningLabel = CaptionLabel("")
        self.warningLabel.setHidden(True)

        # --- 填充下拉框 ---
        for _, display in self.SENSOR_TYPE_CHOICES:
            self.sensor_type_combo.addItem(display)
        self.load_tasks()

        # --- 布局 ---
        self.viewLayout.addWidget(self.titleLabel)

        self.viewLayout.addWidget(StrongBodyLabel("传感器类型:"))
        self.viewLayout.addWidget(self.sensor_type_combo)

        self.viewLayout.addWidget(StrongBodyLabel("传感器ID:"))
        self.viewLayout.addWidget(self.sensor_id_edit)

        self.viewLayout.addWidget(StrongBodyLabel("关联任务:"))
        self.viewLayout.addWidget(self.task_combo)

        self.viewLayout.addWidget(StrongBodyLabel("选择文件:"))
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(self.file_select_button)
        file_widget = QWidget()
        file_widget.setLayout(file_layout)
        self.viewLayout.addWidget(file_widget)

        self.viewLayout.addWidget(StrongBodyLabel("描述:"))
        self.viewLayout.addWidget(self.description_edit)

        self.viewLayout.addWidget(self.warningLabel)

        self.yesButton.setText("上传")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(450)

    def select_file(self):
        """选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择传感器数据文件",
            "",
            "所有文件 (*);;CSV文件 (*.csv);;Excel文件 (*.xlsx);;文本文件 (*.txt)"
        )
        if file_path:
            self.selected_file_path = file_path
            self.file_path_edit.setText(file_path)

    def load_tasks(self):
        """ 加载加工任务列表 """
        tasks = api_client.get_processing_tasks()
        if tasks and 'results' in tasks:
            for task in tasks['results']:
                self.task_combo.addItem(f"{task['task_code']}", userData=task['id'])

    def validate(self):
        """ 重写验证方法 """
        self.warningLabel.hide()

        if self.task_combo.currentIndex() < 0:
            self.warningLabel.setText("必须选择一个关联任务")
            self.warningLabel.show()
            return False

        if not self.selected_file_path:
            self.warningLabel.setText("必须选择一个文件")
            self.warningLabel.show()
            return False

        if not os.path.exists(self.selected_file_path):
            self.warningLabel.setText("选择的文件不存在")
            self.warningLabel.show()
            return False

        return True

    def get_data(self):
        """ 获取表单数据 """
        return {
            "file_path": self.selected_file_path,
            "sensor_type": self.SENSOR_TYPE_CHOICES[self.sensor_type_combo.currentIndex()][0],
            "sensor_id": self.sensor_id_edit.text().strip(),
            "task_id": self.task_combo.currentData(),
            "description": self.description_edit.toPlainText().strip()
        }
