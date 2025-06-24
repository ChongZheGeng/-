# coding:utf-8
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QDateTime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, 
                            QHeaderView, QAbstractItemView, QFileDialog, QProgressBar,
                            QLabel, QFrame, QPushButton, QMessageBox)

from qfluentwidgets import (TableWidget, StrongBodyLabel, LineEdit, ComboBox,
                            PrimaryPushButton, MessageBox, InfoBar, MessageBoxBase, SubtitleLabel,
                            DateTimeEdit, FluentIcon as FIF, CaptionLabel, TextEdit, CardWidget,
                            ProgressBar, IconWidget, BodyLabel, TransparentPushButton, TitleLabel)

from ..common.config import get_webdav_credentials, cfg
import json
import os
from datetime import datetime
import threading


class DownloadTask(QThread):
    """下载任务线程"""
    progress_updated = pyqtSignal(int)  # 进度更新信号
    download_finished = pyqtSignal(bool, str)  # 下载完成信号 (成功, 消息)
    
    def __init__(self, file_url, save_path, file_name, parent=None):
        super().__init__(parent)
        self.file_url = file_url
        self.save_path = save_path
        self.file_name = file_name
        self.is_cancelled = False
        
    def run(self):
        """执行下载任务"""
        try:
            credentials = get_webdav_credentials()
            if not credentials or not credentials['enabled']:
                self.download_finished.emit(False, "WebDAV未配置")
                return
            
            from webdav4.client import Client
            
            client = Client(
                base_url=credentials['url'],
                auth=(credentials['username'], credentials['password'])
            )
            
            # 从URL中提取远程文件路径
            remote_path = self.file_url.replace(credentials['url'].rstrip('/') + '/', '')
            
            # 模拟下载进度（实际情况下可以通过文件大小计算真实进度）
            for i in range(101):
                if self.is_cancelled:
                    return
                self.progress_updated.emit(i)
                self.msleep(50)  # 模拟下载时间
                
                # 在50%时执行真实下载
                if i == 50:
                    client.download_file(from_path=remote_path, to_path=self.save_path)
            
            self.download_finished.emit(True, f"文件已保存到: {self.save_path}")
            
        except Exception as e:
            self.download_finished.emit(False, f"下载失败: {str(e)}")
    
    def cancel_download(self):
        """取消下载"""
        self.is_cancelled = True


class DownloadItemWidget(CardWidget):
    """单个下载项目的卡片组件"""
    
    def __init__(self, file_name, file_url, save_path, parent=None):
        super().__init__(parent)
        self.file_name = file_name
        self.file_url = file_url
        self.save_path = save_path
        self.download_task = None
        
        self.setFixedHeight(130)
        self.setup_ui()
        self.setup_style()
        
    def setup_style(self):
        """设置卡片样式"""
        self.setStyleSheet("""
            DownloadItemWidget {
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                margin: 2px;
            }
            DownloadItemWidget:hover {
                background-color: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(0, 0, 0, 0.15);
            }
        """)
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        # 第一行：文件信息
        info_layout = QHBoxLayout()
        
        # 文件图标
        self.file_icon = IconWidget(FIF.DOCUMENT, self)
        self.file_icon.setFixedSize(40, 40)
        info_layout.addWidget(self.file_icon)
        
        # 文件信息
        file_info_layout = QVBoxLayout()
        file_info_layout.setSpacing(3)
        
        self.file_name_label = StrongBodyLabel(self.file_name)
        self.file_name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        self.file_path_label = CaptionLabel(self.save_path)
        self.file_path_label.setTextColor("#666666")
        self.file_path_label.setStyleSheet("font-size: 12px;")
        
        file_info_layout.addWidget(self.file_name_label)
        file_info_layout.addWidget(self.file_path_label)
        
        info_layout.addLayout(file_info_layout)
        info_layout.addStretch(1)
        
        # 操作按钮
        self.action_button = PrimaryPushButton("开始下载")
        self.action_button.setFixedSize(100, 35)
        self.action_button.clicked.connect(self.start_download)
        info_layout.addWidget(self.action_button)
        
        layout.addLayout(info_layout)
        
        # 第二行：进度条和状态
        progress_layout = QHBoxLayout()
        
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        
        self.status_label = CaptionLabel("等待下载")
        self.status_label.setFixedWidth(120)
        self.status_label.setStyleSheet("font-size: 12px; color: #666666;")
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        
        layout.addLayout(progress_layout)
        
        # 第三行：时间和操作
        bottom_layout = QHBoxLayout()
        
        self.time_label = CaptionLabel(f"添加时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.time_label.setTextColor("#999999")
        self.time_label.setStyleSheet("font-size: 11px;")
        
        self.open_folder_button = TransparentPushButton("打开文件夹")
        self.open_folder_button.setFixedHeight(28)
        self.open_folder_button.clicked.connect(self.open_folder)
        self.open_folder_button.hide()  # 下载完成后显示
        
        self.remove_button = TransparentPushButton("移除")
        self.remove_button.setFixedHeight(28)
        self.remove_button.clicked.connect(self.remove_item)
        
        bottom_layout.addWidget(self.time_label)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.open_folder_button)
        bottom_layout.addWidget(self.remove_button)
        
        layout.addLayout(bottom_layout)
    
    def start_download(self):
        """开始下载"""
        if self.download_task and self.download_task.isRunning():
            return
            
        self.download_task = DownloadTask(self.file_url, self.save_path, self.file_name)
        self.download_task.progress_updated.connect(self.update_progress)
        self.download_task.download_finished.connect(self.download_completed)
        
        self.action_button.setText("取消")
        self.action_button.clicked.disconnect()
        self.action_button.clicked.connect(self.cancel_download)
        
        self.status_label.setText("下载中...")
        self.download_task.start()
    
    def cancel_download(self):
        """取消下载"""
        if self.download_task:
            self.download_task.cancel_download()
            self.download_task.quit()
            self.download_task.wait()
        
        self.action_button.setText("重新下载")
        self.action_button.clicked.disconnect()
        self.action_button.clicked.connect(self.start_download)
        
        self.status_label.setText("已取消")
        self.progress_bar.setValue(0)
    
    def update_progress(self, value):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.status_label.setText(f"下载中... {value}%")
    
    def download_completed(self, success, message):
        """下载完成"""
        if success:
            self.action_button.setText("已完成")
            self.action_button.setEnabled(False)
            self.status_label.setText("下载完成")
            self.progress_bar.setValue(100)
            self.open_folder_button.show()
            
            # 更新文件图标为成功状态
            self.file_icon.setIcon(FIF.ACCEPT)
        else:
            self.action_button.setText("重新下载")
            self.action_button.clicked.disconnect()
            self.action_button.clicked.connect(self.start_download)
            self.status_label.setText("下载失败")
            
            # 更新文件图标为错误状态
            self.file_icon.setIcon(FIF.CLOSE)
    
    def open_folder(self):
        """打开文件夹"""
        import subprocess
        import platform
        
        folder_path = os.path.dirname(self.save_path)
        
        if platform.system() == "Windows":
            subprocess.Popen(f'explorer /select,"{self.save_path}"')
        elif platform.system() == "Darwin":  # macOS
            subprocess.Popen(["open", "-R", self.save_path])
        else:  # Linux
            subprocess.Popen(["xdg-open", folder_path])
    
    def remove_item(self):
        """移除下载项"""
        reply = QMessageBox.question(
            self, 
            "确认移除", 
            "确定要从下载列表中移除此项吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.download_task and self.download_task.isRunning():
                self.download_task.cancel_download()
                self.download_task.quit()
                self.download_task.wait()
            
            self.parent().remove_download_item(self)


class DownloadInterface(QWidget):
    """下载管理界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("DownloadInterface")
        self.download_items = []
        
        self.setup_ui()
        self.setup_style()
    
    def setup_style(self):
        """设置界面样式"""
        self.setStyleSheet("""
            DownloadInterface {
                background-color: #f5f5f5;
            }
            QLabel#emptyLabel {
                color: #999999;
                font-size: 18px;
                font-weight: 300;
                padding: 60px;
                background-color: transparent;
            }
        """)
    
    def setup_ui(self):
        """设置UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 20, 30, 20)
        self.main_layout.setSpacing(20)
        
        # 标题栏
        title_layout = QHBoxLayout()
        
        title_icon = IconWidget(FIF.DOWNLOAD, self)
        title_icon.setFixedSize(36, 36)
        title_label = TitleLabel("下载管理")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333333;")
        
        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_label)
        title_layout.addStretch(1)
        
        # 统计信息
        self.stats_label = BodyLabel("共 0 个下载任务")
        self.stats_label.setStyleSheet("color: #666666; font-size: 14px;")
        title_layout.addWidget(self.stats_label)
        
        # 操作按钮
        self.clear_completed_button = PrimaryPushButton("清除已完成")
        self.clear_completed_button.setIcon(FIF.DELETE)
        self.clear_completed_button.setFixedHeight(35)
        self.clear_completed_button.clicked.connect(self.clear_completed_downloads)
        
        self.clear_all_button = PrimaryPushButton("清除全部")
        self.clear_all_button.setIcon(FIF.CLEAR_SELECTION)
        self.clear_all_button.setFixedHeight(35)
        self.clear_all_button.clicked.connect(self.clear_all_downloads)
        
        title_layout.addWidget(self.clear_completed_button)
        title_layout.addWidget(self.clear_all_button)
        
        self.main_layout.addLayout(title_layout)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #e0e0e0;")
        self.main_layout.addWidget(separator)
        
        # 下载列表容器
        self.downloads_layout = QVBoxLayout()
        self.downloads_layout.setSpacing(12)
        self.main_layout.addLayout(self.downloads_layout)
        
        # 空状态提示
        self.empty_label = QLabel("暂无下载任务\n点击文件的下载按钮即可开始下载")
        self.empty_label.setObjectName("emptyLabel")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.empty_label)
        
        # 弹性空间
        self.main_layout.addStretch(1)
        
        self.update_empty_state()
    
    def add_download(self, file_name, file_url, save_path=None):
        """添加下载任务"""
        # 如果没有指定保存路径，使用默认下载文件夹
        if not save_path:
            download_folder = cfg.downloadFolder.value
            if not os.path.exists(download_folder):
                os.makedirs(download_folder)
            save_path = os.path.join(download_folder, file_name)
        
        # 创建下载项
        download_item = DownloadItemWidget(file_name, file_url, save_path, self)
        self.download_items.append(download_item)
        self.downloads_layout.addWidget(download_item)
        
        self.update_empty_state()
        self.update_stats()
        
        # 自动开始下载
        QTimer.singleShot(100, download_item.start_download)
        
        return download_item
    
    def remove_download_item(self, item):
        """移除下载项"""
        if item in self.download_items:
            self.download_items.remove(item)
            self.downloads_layout.removeWidget(item)
            item.deleteLater()
            self.update_empty_state()
            self.update_stats()
    
    def clear_completed_downloads(self):
        """清除已完成的下载"""
        items_to_remove = []
        for item in self.download_items:
            if (item.download_task and not item.download_task.isRunning() and 
                item.progress_bar.value() == 100):
                items_to_remove.append(item)
        
        for item in items_to_remove:
            self.remove_download_item(item)
    
    def clear_all_downloads(self):
        """清除所有下载"""
        reply = QMessageBox.question(
            self,
            "确认清除",
            "确定要清除所有下载记录吗？正在进行的下载将被取消。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            items_to_remove = self.download_items.copy()
            for item in items_to_remove:
                self.remove_download_item(item)
    
    def update_empty_state(self):
        """更新空状态显示"""
        if self.download_items:
            self.empty_label.hide()
        else:
            self.empty_label.show()
    
    def update_stats(self):
        """更新统计信息"""
        total = len(self.download_items)
        completed = sum(1 for item in self.download_items 
                       if item.progress_bar.value() == 100)
        downloading = sum(1 for item in self.download_items 
                         if item.download_task and item.download_task.isRunning())
        
        if total == 0:
            self.stats_label.setText("共 0 个下载任务")
        else:
            self.stats_label.setText(f"共 {total} 个任务 | {completed} 已完成 | {downloading} 下载中") 