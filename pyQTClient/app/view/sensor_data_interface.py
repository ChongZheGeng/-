# coding:utf-8
from PyQt5.QtCore import Qt, QDateTime, QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QAbstractItemView, QFileDialog

from qfluentwidgets import (TableWidget, StrongBodyLabel, LineEdit, ComboBox,
                            PrimaryPushButton, PushButton, MessageBox, InfoBar, MessageBoxBase, SubtitleLabel,
                            DateTimeEdit, FluentIcon as FIF, CaptionLabel, TextEdit, ProgressBar)

from ..api.api_client import api_client
import logging

# 设置logger
logger = logging.getLogger(__name__)

# 导入数据管理器
try:
    from ..api.data_manager import interface_loader
    DATA_MANAGER_AVAILABLE = True
    logger.debug("数据管理器导入成功")
except ImportError as e:
    logger.warning(f"数据管理器导入失败，回退到原始异步API: {e}")
    # 安全导入异步API作为回退
    try:
        from ..api.async_api import async_api
        ASYNC_API_AVAILABLE = True
        logger.debug("异步API模块导入成功")
    except ImportError as e2:
        logger.warning(f"异步API模块导入失败: {e2}")
        async_api = None
        ASYNC_API_AVAILABLE = False
    DATA_MANAGER_AVAILABLE = False

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


class SensorDataInterface(QWidget):
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
        
        self.table.setColumnCount(7)
        headers = ["传感器类型", "文件名", "文件大小", "关联任务", "上传时间", "传感器ID", "操作"]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # 列宽设置：数据列可调整，操作列固定宽度，倒数第二列拉伸
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)  # 数据列可调整
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)  # 传感器ID列拉伸以铺满
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)  # 操作列固定宽度
        # 初始设置操作列宽度（数据加载后会重新计算）
        self.table.horizontalHeader().resizeSection(6, 160)
        self.main_layout.addWidget(self.table)
        
        # --- 信号连接 ---
        self.add_button.clicked.connect(self.upload_data_file)
        
        # --- 初始化时不自动加载数据，改为按需加载 ---
        # self.populate_table()  # 注释掉自动加载

    def populate_table(self, preserve_old_data=True):
        """ 异步从API获取数据并填充表格 """
        try:
            if DATA_MANAGER_AVAILABLE:
                logger.debug("使用数据管理器加载传感器数据")
                # 使用新的数据管理器
                interface_loader.load_for_interface(
                    interface=self,
                    data_type='sensor_data',
                    table_widget=self.table,
                    force_refresh=True,
                    preserve_old_data=preserve_old_data
                )
            elif ASYNC_API_AVAILABLE and async_api:
                # 回退到原始异步API
                logger.debug("回退到原始异步API加载传感器数据")
                if self.worker and self.worker.isRunning():
                    self.worker.cancel()
                
                if not preserve_old_data:
                    self.table.setRowCount(0)
                self.worker = async_api.get_sensor_data_async(
                    success_callback=self.on_data_received,
                    error_callback=self.on_data_error
                )
            else:
                # 最终回退到同步加载
                logger.warning("异步API不可用，回退到同步加载")
                if not preserve_old_data:
                    self.table.setRowCount(0)
                try:
                    response_data = api_client.get_sensor_data()
                    self.on_data_received(response_data)
                except Exception as e:
                    self.on_data_error(str(e))
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
        """处理接收到的数据"""
        try:
            if not self or not hasattr(self, 'table') or not self.table:
                logger.warning("传感器数据回调时界面已销毁")
                return
                
            if not response or 'results' not in response:
                logger.debug("传感器数据为空")
                return

            data_list = response['results']
            logger.debug(f"接收到 {len(data_list)} 个传感器数据")
            
            self.table.setRowCount(0)
            for data in data_list:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # 设置表格项
                self.table.setItem(row, 0, QTableWidgetItem(data.get('sensor_type_display', 'N/A')))
                
                file_name = os.path.basename(data.get('file_url', ''))
                self.table.setItem(row, 1, QTableWidgetItem(file_name))
                
                file_size = data.get('file_size', 0)
                if file_size:
                    size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB"
                else:
                    size_str = "未知"
                self.table.setItem(row, 2, QTableWidgetItem(size_str))
                
                task_info = data.get('task_info', {})
                task_code = task_info.get('task_code', 'N/A') if task_info else 'N/A'
                self.table.setItem(row, 3, QTableWidgetItem(task_code))
                
                upload_time = data.get('upload_time', '')
                if upload_time:
                    try:
                        dt = datetime.fromisoformat(upload_time.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        formatted_time = upload_time
                else:
                    formatted_time = 'N/A'
                self.table.setItem(row, 4, QTableWidgetItem(formatted_time))
                
                self.table.setItem(row, 5, QTableWidgetItem(data.get('sensor_id', 'N/A')))
                
                # 操作按钮
                download_button = PrimaryPushButton("下载")
                delete_button = PushButton("删除")
                
                file_url = data.get('file_url', '')
                download_button.clicked.connect(partial(self.download_file, file_url, file_name))
                delete_button.clicked.connect(partial(self.delete_data, data['id']))
                
                button_widget = QWidget()
                button_layout = QHBoxLayout(button_widget)
                button_layout.setContentsMargins(2, 2, 2, 2)
                button_layout.setSpacing(8)
                button_layout.addWidget(download_button)
                button_layout.addWidget(delete_button)
                self.table.setCellWidget(row, 6, button_widget)
            
            # 根据按钮数量动态调整操作列宽度 (2个按钮)
            button_width = 75
            spacing = 8
            margin = 6
            total_width = 2 * button_width + spacing + 2 * margin
            self.table.horizontalHeader().resizeSection(6, total_width)
            
        except Exception as e:
            logger.error(f"处理传感器数据时出错: {e}")
    
    def on_data_error(self, error_message):
        """处理数据加载错误"""
        try:
            logger.error(f"传感器数据加载失败: {error_message}")
            if self and hasattr(self, 'parent') and self.parent():
                InfoBar.error("加载失败", f"传感器数据加载失败: {error_message}", parent=self)
        except Exception as e:
            logger.error(f"处理传感器数据错误时出错: {e}")


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