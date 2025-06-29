# coding:utf-8
import logging

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QAbstractItemView
from qfluentwidgets import (TableWidget, PrimaryPushButton, MessageBox, InfoBar, SubtitleLabel,
                            FluentIcon as FIF, PushButton, MessageBoxBase, CheckBox, BodyLabel)

from .nav_interface import NavInterface
from ..api.api_client import api_client
from ..api.data_manager import interface_loader

# 设置logger
logger = logging.getLogger(__name__)

from ..common.config import get_webdav_credentials

import os
from datetime import datetime
from .components.sensor_data_component import SensorDataUploadDialog, SensorDataEditDialog


class SensorDataInterface(NavInterface):
    """ 传感器数据管理界面 """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SensorDataInterface")
        self.worker = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(40, 30, 40, 30)
        self.main_layout.setSpacing(30)

        # --- 标题和工具栏 ---
        title_layout = QHBoxLayout()
        title_label = SubtitleLabel("传感器数据管理")
        title_layout.addWidget(title_label)
        title_layout.addStretch(1)
        
        # 添加文件同步按钮
        self.sync_button = PushButton("同步文件")
        self.sync_button.setIcon(FIF.SYNC)
        title_layout.addWidget(self.sync_button)
        
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
        self.sync_button.clicked.connect(self.sync_files_with_database)

        # --- 移除初始化时的数据加载调用，改为在on_activated中加载 ---

    def _define_column_mapping(self):
        """定义表格的列映射关系"""
        self.column_mapping = [
            {
                'key': 'sensor_type',
                'header': '传感器类型',
                'width': 100,
                'formatter': lambda sensor_type: dict(SensorDataUploadDialog.SENSOR_TYPE_CHOICES).get(sensor_type,
                                                                                                      sensor_type)
            },
            {'key': 'sensor_id', 'header': '传感器ID', 'width': 100},
            {
                'key': 'file_url',
                'header': '文件名',
                'stretch': True,  # 这个列会占满剩余空间
                'formatter': lambda file_url: os.path.basename(file_url) if file_url else 'N/A'
            },
            {
                'key': 'file_size',
                'header': '文件大小',
                'width': 90,
                'formatter': lambda
                    file_size: f"{file_size / 1024:.1f} KB" if file_size and file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.1f} MB" if file_size else "未知"
            },
            {
                'key': 'task_info',
                'header': '关联任务',
                'width': 120,
                'formatter': lambda task_info: task_info.get('task_code', 'N/A') if task_info else 'N/A'
            },
            {
                'key': 'upload_time',
                'header': '上传时间',
                'width': 130,
                'formatter': lambda upload_time: datetime.fromisoformat(upload_time.replace('Z', '+00:00')).strftime(
                    '%Y-%m-%d %H:%M') if upload_time else 'N/A'
            },
            {
                'type': 'buttons',
                'header': '操作',
                'width': 210,
                'buttons': [
                    {'text': '编辑', 'style': 'primary', 'callback': self.edit_sensor_data},
                    {'text': '下载', 'style': 'default',
                     'callback': lambda data: self.download_file(data.get('file_url', ''),
                                                                 os.path.basename(data.get('file_url', '')) if data.get(
                                                                     'file_url') else 'unknown')},
                    {'text': '删除', 'style': 'default', 'callback': self.delete_data}
                ]
            }
        ]

    def on_activated(self):
        """界面激活时的回调方法 - 按需加载数据并自动同步文件"""
        try:
            # 首先进行文件同步（静默执行）
            credentials = get_webdav_credentials()
            if credentials and credentials['enabled']:
                try:
                    success, message, unmanaged_files = api_client.sync_sensor_files_with_database()
                    if success and unmanaged_files:
                        InfoBar.info(
                            "文件同步", 
                            f"发现 {len(unmanaged_files)} 个未管理的文件已移动到 unmanaged 目录",
                            duration=3000, 
                            parent=self
                        )
                except Exception as e:
                    logger.warning(f"自动文件同步失败: {e}")
            
            # 然后加载数据
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
            main_window.download_button.start_download(file_name, file_url, self.parent())
        else:
            InfoBar.error("错误", "下载功能不可用", parent=self)

    def edit_sensor_data(self, sensor_data):
        """ 编辑传感器数据 """
        dialog = SensorDataEditDialog(self.window(), sensor_data)
        if dialog.exec():
            data = dialog.get_data()
            result = api_client.update_sensor_data(sensor_data['id'], data)
            if result:
                InfoBar.success("成功", "传感器数据更新成功", duration=2000, parent=self)
                self.populate_table(preserve_old_data=False)
            else:
                InfoBar.error("失败", "传感器数据更新失败，请查看控制台输出。", duration=3000, parent=self)

    def delete_data(self, sensor_data):
        """ 删除传感器数据（带文件删除选项） """
        dialog = MessageBoxBase(self.window())
        
        title_label = SubtitleLabel("确认删除", dialog)
        dialog.viewLayout.addWidget(title_label)

        confirm_label = BodyLabel("您确定要删除这条传感器数据记录吗？此操作不可撤销。")
        dialog.viewLayout.addWidget(confirm_label)
        
        file_checkbox = CheckBox("同时删除文件服务器上的对应文件", dialog)
        file_checkbox.setChecked(False)
        dialog.viewLayout.addWidget(file_checkbox)

        dialog.yesButton.setText("删除")
        dialog.cancelButton.setText("取消")
        
        if dialog.exec():
            data_id = sensor_data.get('id')
            file_url = sensor_data.get('file_url', '')
            
            success = api_client.delete_sensor_data(data_id)
            if success:
                InfoBar.success("成功", "数据记录已删除。", parent=self)
                
                if file_checkbox.isChecked() and file_url:
                    file_success, file_message = api_client.delete_sensor_file_from_webdav(file_url)
                    if file_success:
                        InfoBar.success("成功", f"文件也已删除：{file_message}", parent=self)
                    else:
                        InfoBar.warning("警告", f"数据记录已删除，但文件删除失败：{file_message}", parent=self)
                
                self.populate_table(preserve_old_data=False)
            else:
                InfoBar.error("失败", "删除数据记录失败。", parent=self)

    def sync_files_with_database(self):
        """ 同步文件服务器与数据库记录 """
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
        
        # 显示同步进度
        InfoBar.info("同步中", "正在同步文件服务器与数据库记录...", duration=3000, parent=self)
        
        try:
            success, message, unmanaged_files = api_client.sync_sensor_files_with_database()
            
            if success:
                if unmanaged_files:
                    InfoBar.success(
                        "同步完成", 
                        f"{message}。移动的文件：{', '.join(unmanaged_files[:5])}{'等' if len(unmanaged_files) > 5 else ''}",
                        duration=5000, 
                        parent=self
                    )
                else:
                    InfoBar.success("同步完成", message, duration=3000, parent=self)
            else:
                InfoBar.error("同步失败", message, duration=5000, parent=self)
                
        except Exception as e:
            logger.error(f"文件同步出错: {e}")
            InfoBar.error("同步失败", f"文件同步过程中出现错误: {str(e)}", duration=5000, parent=self)

    def __del__(self):
        """ 确保在销毁时取消工作线程 """
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel()
