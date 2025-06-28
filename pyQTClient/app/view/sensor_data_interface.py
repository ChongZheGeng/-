# coding:utf-8
from PyQt5.QtCore import Qt, QDateTime, QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QAbstractItemView, QFileDialog

from qfluentwidgets import (TableWidget, StrongBodyLabel, LineEdit, ComboBox,
                            PrimaryPushButton, PushButton, MessageBox, InfoBar, MessageBoxBase, SubtitleLabel,
                            DateTimeEdit, FluentIcon as FIF, CaptionLabel, TextEdit, ProgressBar)

from ..api.api_client import api_client
from ..api.data_manager import interface_loader
from .nav_interface import NavInterface
import logging

# 设置logger
logger = logging.getLogger(__name__)

from ..common.config import get_webdav_credentials, cfg

import json
import os
from datetime import datetime
from urllib.parse import urlparse
from functools import partial


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


class SensorDataInterface(NavInterface):
    """ 传感器数据管理界面 """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SensorDataInterface")
        self.worker = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 20, 30, 20)
        self.main_layout.setSpacing(20)

        # --- 标题和工具栏 ---
        title_layout = QHBoxLayout()
        title_label = SubtitleLabel("传感器数据管理")
        title_layout.addWidget(title_label)
        title_layout.addStretch(1)
        self.add_button = PrimaryPushButton("上传数据文件")
        self.add_button.setIcon(FIF.ADD)
        title_layout.addWidget(self.add_button)
        
        self.main_layout.addLayout(title_layout)
        
        # --- 数据表格 ---
        self.table = TableWidget(self)
        
        # --- 应用官方示例样式 ---
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)
        # --- 样式应用结束 ---
        
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        self._define_column_mapping()
        
        self.main_layout.addWidget(self.table)
        
        # --- 信号连接 ---
        self.add_button.clicked.connect(self.upload_data_file)
        
        # --- 移除初始化时的数据加载调用，改为在on_activated中加载 ---

    def _define_column_mapping(self):
        """定义表格的列映射关系"""
        self.column_mapping = [
            {
                'key': 'sensor_type', 
                'header': '传感器类型',
                'formatter': lambda sensor_type: dict(SensorDataUploadDialog.SENSOR_TYPE_CHOICES).get(sensor_type, sensor_type)
            },
            {
                'key': 'file_url', 
                'header': '文件名',
                'formatter': lambda file_url: os.path.basename(file_url) if file_url else 'N/A'
            },
            {
                'key': 'file_size', 
                'header': '文件大小',
                'formatter': lambda file_size: f"{file_size / 1024:.1f} KB" if file_size and file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB" if file_size else "未知"
            },
            {
                'key': 'task_info', 
                'header': '关联任务',
                'formatter': lambda task_info: task_info.get('task_code', 'N/A') if task_info else 'N/A'
            },
            {
                'key': 'upload_time', 
                'header': '上传时间',
                'formatter': lambda upload_time: datetime.fromisoformat(upload_time.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M') if upload_time else 'N/A'
            },
            {'key': 'sensor_id', 'header': '传感器ID'},
            {
                'type': 'buttons',
                'header': '操作',
                'width': 170,
                'buttons': [
                    {'text': '下载', 'style': 'primary', 'callback': lambda data: self.download_file(data.get('file_url', ''), os.path.basename(data.get('file_url', '')) if data.get('file_url') else 'unknown')},
                    {'text': '删除', 'style': 'default', 'callback': lambda data: self.delete_data(data['id'])}
                ]
            }
        ]

    def on_activated(self):
        """界面激活时的回调方法 - 按需加载数据"""
        try:
            interface_loader.load_for_interface(
                interface=self,
                data_type='sensor_data',
                table_widget=self.table,
                force_refresh=True,
                preserve_old_data=True,
                column_mapping=self.column_mapping
            )
        except Exception as e:
            logger.error(f"激活传感器数据界面时加载数据出错: {e}")
            self.on_data_error(str(e))

    def on_deactivated(self):
        """
        当界面被切换离开时调用。
        可以在此处进行一些清理工作，如取消正在进行的请求。
        """
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel()
            logger.debug("SensorDataInterface 被切换离开，已取消数据加载请求")

    def populate_table(self, preserve_old_data=True):
        """ 异步从API获取数据并填充表格 """
        try:
            logger.debug("使用数据管理器加载传感器数据")
            # 使用新的数据管理器
            self.worker = interface_loader.load_for_interface(
                interface=self,
                data_type='sensor_data',
                table_widget=self.table,
                force_refresh=not preserve_old_data,
                preserve_old_data=preserve_old_data,
                column_mapping=self.column_mapping
            )
        except Exception as e:
            logger.error(f"加载传感器数据时出错: {e}")
            self.on_data_error(str(e))
    
    def on_sensor_data_data_received(self, response):
        """数据管理器使用的标准回调方法"""
        self.on_data_received(response)
    
    def on_sensor_data_data_error(self, error):
        """数据管理器使用的标准错误回调方法"""
        self.on_data_error(error)
    
    def on_data_received(self, response):
        """处理接收到的传感器数据（现在主要用于日志记录或额外操作）"""
        # 当使用了 column_mapping 自动填充时，表格填充已由 InterfaceDataLoader 自动处理
        # 这里只进行日志记录和任何需要的额外操作
        if hasattr(self, 'column_mapping') and self.column_mapping:
            total = response.get('count', 0) if response else 0
            logger.info(f"SensorDataInterface 成功接收并处理了 {total} 条传感器数据。")
            return
        
        # 如果没有使用自动填充，则保留原有的手动处理逻辑
        # （这部分代码在当前实现中已经被移除，因为我们已经完全转向自动填充）
        logger.warning("SensorDataInterface 未使用自动填充配置，但手动填充逻辑已被移除")
    
    def on_data_error(self, error_message):
        """处理传感器数据加载错误"""
        # InfoBar 错误提示已由 InterfaceDataLoader 自动处理
        logger.error(f"传感器数据加载失败: {error_message}")

    def upload_data_file(self):
        """ 上传数据文件 """
        # 首先检查WebDAV是否已配置
        credentials = get_webdav_credentials()
        if not credentials or not credentials['enabled']:
            InfoBar.warning(
                "WebDAV未配置", 
                "请先在设置页面中配置并启用WebDAV连接。", 
                duration=5000,
                parent=self
            )
            return
            
        # 显示文件选择对话框
        dialog = SensorDataUploadDialog(self.window())
        if dialog.exec():
            data = dialog.get_data()
            if data:
                # 获取主窗口的文件传输按钮
                main_window = self.window()
                if hasattr(main_window, 'download_button'):
                    # 使用统一的文件传输管理器
                    upload_task = main_window.download_button.start_upload(data, self.parent())
                    if upload_task:
                        # 连接上传完成信号到刷新表格
                        upload_task.transfer_finished.connect(
                            lambda success, message: self.populate_table(preserve_old_data=False) if success else None
                        )
                else:
                    InfoBar.error("错误", "文件传输功能不可用", parent=self)

    def download_file(self, file_url, file_name):
        """下载文件"""
        # 获取主窗口的下载按钮
        main_window = self.window()
        if hasattr(main_window, 'download_button'):
            main_window.download_button.start_download(file_name, file_url,self.parent())
        else:
            InfoBar.error("错误", "下载功能不可用", parent=self)

    def delete_data(self, data_id):
        """ 删除数据 """
        w = MessageBox("确认删除", "您确定要删除这条数据吗？此操作不可撤销。", self.window())
        if w.exec():
            success = api_client.delete_sensor_data(data_id)
            if success:
                InfoBar.success("成功", "数据已删除。", parent=self)
                self.populate_table(preserve_old_data=False)
            else:
                InfoBar.error("失败", "删除失败。", parent=self)

    def __del__(self):
        """ 确保在销毁时取消工作线程 """
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel() 