# coding:utf-8
import os
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PyQt5.QtGui import QColor

from qfluentwidgets import (BodyLabel, TransparentToolButton, TransparentPushButton,
                            FluentIcon as FIF, IconWidget, SubtitleLabel,
                            PrimaryPushButton, PushButton, InfoBar, ProgressBar, CaptionLabel,
                            Flyout, FlyoutAnimationType, MessageBoxBase, FlyoutViewBase)

from webdav4.client import Client
from ..common.config import cfg, get_webdav_credentials
from ..api.api_client import api_client


def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


class FileTransferTask(QThread):
    """文件传输任务基类"""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    transfer_finished = pyqtSignal(bool, str)
    
    def __init__(self, task_type, file_name):
        super().__init__()
        self.task_type = task_type  # 'upload' 或 'download'
        self.file_name = file_name
        self.is_cancelled = False
        self.progress = 0
        self.status = "准备中"
    
    def cancel(self):
        """取消传输"""
        self.is_cancelled = True


class UploadTask(FileTransferTask):
    """上传任务"""
    
    def __init__(self, upload_data):
        super().__init__('upload', os.path.basename(upload_data['file_path']))
        self.upload_data = upload_data
        self.uploaded_size = 0
        self.total_size = 0
        
        # 获取文件大小
        try:
            if os.path.exists(upload_data['file_path']):
                self.total_size = os.path.getsize(upload_data['file_path'])
                print(f"[DEBUG] 上传文件大小: {format_file_size(self.total_size)}")
        except Exception as e:
            print(f"[DEBUG] 获取文件大小失败: {e}")
            self.total_size = 0
    
    def run(self):
        """执行上传"""
        try:
            # 模拟上传进度
            for i in range(0, 101, 5):
                if self.is_cancelled:
                    return
                
                self.progress = i
                self.progress_updated.emit(i)
                
                # 计算已上传大小
                if self.total_size > 0:
                    self.uploaded_size = int((i / 100.0) * self.total_size)
                    # 显示详细的上传信息
                    status_text = f"上传中: {format_file_size(self.uploaded_size)} / {format_file_size(self.total_size)} ({i}%)"
                else:
                    # 如果无法获取文件大小，显示简化信息
                    status_text = f"上传中: {i}%"
                
                if i == 0:
                    status_text = "正在连接服务器..."
                elif i < 20:
                    status_text = "正在验证文件..."
                elif i < 50:
                    if self.total_size > 0:
                        status_text = f"上传中: {format_file_size(self.uploaded_size)} / {format_file_size(self.total_size)} ({i}%)"
                    else:
                        status_text = f"上传中: {i}%"
                elif i < 80:
                    status_text = "正在处理文件..."
                elif i < 100:
                    status_text = "正在保存数据..."
                elif i == 100:
                    if self.total_size > 0:
                        self.uploaded_size = self.total_size
                        status_text = f"上传完成: {format_file_size(self.total_size)}"
                    else:
                        status_text = "上传完成"
                
                self.status = status_text
                self.status_updated.emit(status_text)
                
                # 模拟上传延迟
                self.msleep(100)
                
                # 在50%时执行实际上传
                if i == 50 and not self.is_cancelled:
                    success, message = api_client.upload_sensor_file_to_webdav(
                        self.upload_data['file_path'],
                        self.upload_data['task_id'],
                        self.upload_data['sensor_type'],
                        self.upload_data['sensor_id'],
                        self.upload_data['description']
                    )
                    
                    if not success:
                        self.transfer_finished.emit(False, message)
                        return
            
            if not self.is_cancelled:
                self.transfer_finished.emit(True, "文件上传成功")
                
        except Exception as e:
            if not self.is_cancelled:
                self.transfer_finished.emit(False, f"上传过程中发生错误: {str(e)}")


class DownloadTask(FileTransferTask):
    """下载任务"""
    
    def __init__(self, file_url, save_path, file_name):
        super().__init__('download', file_name)
        self.file_url = file_url
        self.save_path = save_path
        self.downloaded_size = 0
        self.total_size = 0
    
    def run(self):
        """执行下载"""
        try:
            # 获取WebDAV配置
            credentials = get_webdav_credentials()
            if not credentials or not credentials['enabled']:
                self.transfer_finished.emit(False, "WebDAV未配置或未启用")
                return

            # 创建WebDAV客户端
            client = Client(
                base_url=credentials['url'],
                auth=(credentials['username'], credentials['password'])
            )
            
            # 从完整URL中提取相对路径
            base_url = credentials['url'].rstrip('/')
            if self.file_url.startswith(base_url):
                remote_path = self.file_url[len(base_url):].lstrip('/')
            else:
                remote_path = self.file_url.lstrip('/')
            
            # 检查远程文件是否存在
            if not client.exists(remote_path):
                self.transfer_finished.emit(False, f"远程文件不存在: {remote_path}")
                return
            
            # 获取文件信息
            try:
                info = client.info(remote_path)
                file_size = info.get('size', 0)
                self.total_size = file_size
                print(f"[DEBUG] 文件大小: {format_file_size(file_size)}")
            except Exception:
                file_size = 0
                self.total_size = 0
            
            self.status = "正在下载..."
            self.status_updated.emit(self.status)
            
            # 下载文件
            with open(self.save_path, 'wb') as f:
                with client.open(remote_path, 'rb') as remote_file:
                    downloaded = 0
                    chunk_size = 8192
                    
                    while True:
                        if self.is_cancelled:
                            self.transfer_finished.emit(False, "下载已取消")
                            return
                        
                        chunk = remote_file.read(chunk_size)
                        if not chunk:
                            break
                        
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.downloaded_size = downloaded
                        
                        # 更新进度
                        if file_size > 0:
                            progress = int((downloaded / file_size) * 100)
                            # 显示详细的下载信息
                            status_text = f"下载中: {format_file_size(downloaded)} / {format_file_size(file_size)} ({progress}%)"
                        else:
                            progress = min(90, downloaded // 1024)
                            status_text = f"下载中: {format_file_size(downloaded)} ({progress}%)"
                        
                        self.progress = progress
                        self.progress_updated.emit(progress)
                        self.status_updated.emit(status_text)
            
            # 检查文件是否下载完成
            if os.path.exists(self.save_path):
                self.transfer_finished.emit(True, f"文件已保存到: {self.save_path}")
            else:
                self.transfer_finished.emit(False, "文件下载失败")
                
        except Exception as e:
            self.transfer_finished.emit(False, f"下载出错: {str(e)}")


class FileTransferProgressDialog(MessageBoxBase):
    """文件传输进度弹窗 - 使用MessageBoxBase"""
    
    def __init__(self, transfer_task, parent=None):
        super().__init__(parent)
        self.transfer_task = transfer_task
        self.is_background = False
        
        self.setup_ui()
        self.start_transfer()
    
    def setup_ui(self):
        """设置UI"""
        # 标题
        task_type_text = "上传" if self.transfer_task.task_type == 'upload' else "下载"
        self.titleLabel = SubtitleLabel(f"{task_type_text}文件", self)
        
        # 文件名标签
        self.file_label = BodyLabel(f"文件: {self.transfer_task.file_name}", self)
        
        # 进度条
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        
        # 状态标签
        self.status_label = CaptionLabel("准备中...", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # 添加到视图布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.file_label)
        self.viewLayout.addWidget(self.progress_bar)
        self.viewLayout.addWidget(self.status_label)
        
        # 修改按钮文本
        self.yesButton.setText("后台传输")
        self.cancelButton.setText("取消")
        
        # 连接按钮事件
        self.yesButton.clicked.connect(self.background_transfer)
        self.cancelButton.clicked.connect(self.cancel_transfer)
        
        # 设置最小宽度
        self.widget.setMinimumWidth(400)
    
    def start_transfer(self):
        """开始传输"""
        self.transfer_task.progress_updated.connect(self.update_progress)
        self.transfer_task.status_updated.connect(self.update_status)
        self.transfer_task.transfer_finished.connect(self.transfer_completed)
        self.transfer_task.start()
    
    def update_progress(self, progress):
        """更新进度"""
        self.progress_bar.setValue(progress)
    
    def update_status(self, status):
        """更新状态"""
        self.status_label.setText(status)
    
    def transfer_completed(self, success, message):
        """传输完成"""
        if success:
            self.status_label.setText("✅ 传输完成!")
            self.progress_bar.setValue(100)
            
            task_type_text = "上传" if self.transfer_task.task_type == 'upload' else "下载"
            InfoBar.success(f"{task_type_text}完成", message, parent=self.parent())
            
            # 如果不是后台传输，自动关闭弹窗
            if not self.is_background:
                QTimer.singleShot(1500, self.accept)
        else:
            self.status_label.setText("❌ 传输失败")
            task_type_text = "上传" if self.transfer_task.task_type == 'upload' else "下载"
            InfoBar.error(f"{task_type_text}失败", message, parent=self.parent())
            
            # 失败时也自动关闭
            if not self.is_background:
                QTimer.singleShot(2500, self.reject)
    
    def background_transfer(self):
        """后台传输"""
        self.is_background = True
        task_type_text = "上传" if self.transfer_task.task_type == 'upload' else "下载"
        InfoBar.info("后台传输", f"文件将在后台继续{task_type_text}", parent=self.parent())
        self.accept()  # 关闭对话框
    
    def cancel_transfer(self):
        """取消传输"""
        if self.transfer_task.isRunning():
            self.transfer_task.cancel()
            task_type_text = "上传" if self.transfer_task.task_type == 'upload' else "下载"
            InfoBar.warning("取消", f"文件{task_type_text}已取消", parent=self.parent())
        
        self.reject()  # 关闭对话框


class BackgroundTransferFlyoutView(FlyoutViewBase):
    """后台传输管理Flyout视图 - 参照官方示例"""
    
    # 添加关闭信号
    closed = pyqtSignal()
    
    def __init__(self, background_transfers, parent=None):
        super().__init__(parent)
        self.background_transfers = background_transfers  # 保存引用，不是复制
        self.flyout_widget = None  # 保存flyout引用
        self.setup_ui()
        
        # 定时器更新进度
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_progress)
        self.update_timer.start(1000)
        
        print(f"[DEBUG] BackgroundTransferFlyoutView 创建，任务数: {len(self.background_transfers)}")
    
    def setup_ui(self):
        """设置UI - 参照官方CustomFlyoutView"""
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setSpacing(12)
        self.vBoxLayout.setContentsMargins(20, 16, 20, 16)
        
        if not self.background_transfers:
            # 无传输任务
            self.label = BodyLabel('暂无进行中的传输任务')
            self.vBoxLayout.addWidget(self.label)
        else:
            # 有传输任务
            # self.label = BodyLabel('暂无进行中的传输任务')
            # self.vBoxLayout.addWidget(self.label)
            for transfer_task in self.background_transfers:
                item_widget = self.create_transfer_item(transfer_task)
                self.vBoxLayout.addWidget(item_widget)

    
    def create_transfer_item(self, transfer_task):
        """创建传输项"""
        item_widget = QWidget()
        item_widget.transfer_task = transfer_task  # 保存任务引用
        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 图标
        icon = FIF.UP if transfer_task.task_type == 'upload' else FIF.CLOUD_DOWNLOAD
        icon_widget = IconWidget(icon, item_widget)
        icon_widget.setFixedSize(24, 24)
        
        # 信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        name_label = BodyLabel(transfer_task.file_name, item_widget)
        name_label.setStyleSheet("font-weight: 500;")
        
        # 添加文件大小信息
        size_label = CaptionLabel("", item_widget)
        size_label.setStyleSheet("color: #666666; font-size: 11px;")
        
        progress_bar = ProgressBar(item_widget)
        progress_bar.setValue(transfer_task.progress)
        progress_bar.setFixedWidth(200)
        progress_bar.setFixedHeight(6)
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(size_label)
        info_layout.addWidget(progress_bar)
        
        # 取消按钮
        cancel_button = PushButton('取消', item_widget)
        cancel_button.setFixedWidth(60)
        cancel_button.clicked.connect(lambda: self.cancel_transfer(transfer_task))
        
        if not transfer_task.isRunning():
            cancel_button.setEnabled(False)
        
        layout.addWidget(icon_widget)
        layout.addLayout(info_layout)
        layout.addWidget(cancel_button)
        
        # 保存控件引用以便更新
        item_widget.progress_bar = progress_bar
        item_widget.cancel_button = cancel_button
        item_widget.size_label = size_label
        
        return item_widget
    
    def cancel_transfer(self, transfer_task):
        """取消传输"""
        transfer_task.cancel()
        task_type_text = "上传" if transfer_task.task_type == 'upload' else "下载"
        InfoBar.warning("取消", f"{transfer_task.file_name} {task_type_text}已取消", parent=self.parent())
    
    def update_progress(self):
        """更新进度"""
        # 检查是否还有活跃的任务
        active_tasks = [t for t in self.background_transfers if t.isRunning()]
        
        if not active_tasks and len(self.background_transfers) == 0:
            # 如果没有任务了，关闭Flyout
            print("[DEBUG] 所有任务已完成，关闭Flyout")
            self.closed.emit()
            if self.flyout_widget:
                self.flyout_widget.close()
            return
        
        # 更新所有传输项的进度
        for i in range(self.vBoxLayout.count()):
            widget = self.vBoxLayout.itemAt(i).widget()
            if widget and hasattr(widget, 'transfer_task'):
                transfer_task = widget.transfer_task
                
                # 更新进度条
                if hasattr(widget, 'progress_bar'):
                    widget.progress_bar.setValue(transfer_task.progress)
                
                # 更新文件大小信息
                if hasattr(widget, 'size_label'):
                    if transfer_task.task_type == 'download':
                        if hasattr(transfer_task, 'downloaded_size') and hasattr(transfer_task, 'total_size'):
                            if transfer_task.total_size > 0:
                                size_text = f"{format_file_size(transfer_task.downloaded_size)} / {format_file_size(transfer_task.total_size)}"
                            else:
                                size_text = f"{format_file_size(transfer_task.downloaded_size)}"
                            widget.size_label.setText(size_text)
                    elif transfer_task.task_type == 'upload':
                        if hasattr(transfer_task, 'uploaded_size') and hasattr(transfer_task, 'total_size'):
                            if transfer_task.total_size > 0:
                                size_text = f"{format_file_size(transfer_task.uploaded_size)} / {format_file_size(transfer_task.total_size)}"
                            else:
                                size_text = f"{format_file_size(transfer_task.uploaded_size)}"
                            widget.size_label.setText(size_text)
                
                # 更新取消按钮状态
                if hasattr(widget, 'cancel_button'):
                    widget.cancel_button.setEnabled(transfer_task.isRunning())
                    
                print(f"[DEBUG] 更新进度: {transfer_task.file_name} - {transfer_task.progress}%")


class FileTransferButton(TransparentToolButton):
    """文件传输管理按钮"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(FIF.CLOUD)
        self.setFixedSize(40, 40)
        self.setToolTip("文件传输管理")
        self.background_transfers = []  # 后台传输任务列表
        self.clicked.connect(self.show_background_transfers)
        
        # 创建徽章
        self.badge_widget = QWidget(self)
        self.badge_widget.setFixedSize(16, 16)
        self.badge_widget.setStyleSheet("""
            QWidget {
                background-color: #FF4444;
                border-radius: 8px;
                color: white;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        self.badge_widget.hide()
        
        # 定时器更新徽章
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_badge)
        self.update_timer.start(1000)  # 每秒更新一次
    
    def show_background_transfers(self):
        """显示后台传输管理 - 参照官方示例"""
        print(f"[DEBUG] 显示后台传输列表，当前任务数: {len(self.background_transfers)}")
        for i, task in enumerate(self.background_transfers):
            print(f"[DEBUG] 任务 {i}: {task.file_name} - 进度: {task.progress}% - 运行中: {task.isRunning()}")
        
        # 创建自定义Flyout视图
        flyout_view = BackgroundTransferFlyoutView(self.background_transfers, self.parent())
        
        # 使用Flyout.make显示，参照官方showFlyout3
        flyout_widget = Flyout.make(flyout_view, self, self.parent(), aniType=FlyoutAnimationType.DROP_DOWN)
        
        # 保存flyout引用并连接关闭信号
        flyout_view.flyout_widget = flyout_widget
        flyout_view.closed.connect(flyout_widget.close)
    
    def start_upload(self, upload_data, parent=None):
        """开始上传"""
        upload_task = UploadTask(upload_data)
        
        # 先连接完成信号
        upload_task.transfer_finished.connect(
            lambda success, message: self.transfer_completed(upload_task, success, message)
        )
        
        # 显示进度对话框
        if parent:
            progress_dialog = FileTransferProgressDialog(upload_task,parent)
        else:
            progress_dialog = FileTransferProgressDialog(upload_task, self.parent())
        result = progress_dialog.exec()
        
        # 如果选择后台传输，添加到后台列表
        if progress_dialog.is_background:
            self.background_transfers.append(upload_task)
            print(f"[DEBUG] 添加上传任务到后台列表: {upload_task.file_name}")
        
        return upload_task
    
    def start_download(self, file_name, file_url, parent=None):
        """开始下载"""
        # 弹出文件保存对话框
        save_path, _ = QFileDialog.getSaveFileName(
            self.parent(),
            "保存文件",
            file_name,
            "所有文件 (*.*)"
        )
        
        if not save_path:
            return None
        
        download_task = DownloadTask(file_url, save_path, file_name)
        
        # 先连接完成信号
        download_task.transfer_finished.connect(
            lambda success, message: self.transfer_completed(download_task, success, message)
        )
        
        # 显示进度对话框
        if parent:
            progress_dialog = FileTransferProgressDialog(download_task, parent)
        else:
            progress_dialog = FileTransferProgressDialog(download_task, self.parent())
        result = progress_dialog.exec()
        
        # 如果选择后台传输，添加到后台列表
        if progress_dialog.is_background:
            self.background_transfers.append(download_task)
            print(f"[DEBUG] 添加下载任务到后台列表: {download_task.file_name}")
        
        return download_task
    
    def transfer_completed(self, task, success, message):
        """传输完成回调"""
        # 从后台列表中移除完成的任务
        if task in self.background_transfers:
            self.background_transfers.remove(task)
        
        # 显示完成通知
        task_type_text = "上传" if task.task_type == 'upload' else "下载"
        if success:
            InfoBar.success(f"{task_type_text}完成", f"{task.file_name} {task_type_text}成功", parent=self.parent())
        else:
            InfoBar.error(f"{task_type_text}失败", f"{task.file_name} {task_type_text}失败: {message}", parent=self.parent())
        
        # 如果是上传任务完成，刷新传感器数据表格
        if task.task_type == 'upload' and success:
            # 尝试找到传感器数据界面并刷新
            main_window = self.parent()
            if hasattr(main_window, 'sensor_data_interface'):
                main_window.sensor_data_interface.populate_table()
    
    def update_badge(self):
        """更新徽章显示"""
        active_count = len([t for t in self.background_transfers if t.isRunning()])
        
        if active_count > 0:
            self.badge_widget.show()
            self.badge_widget.move(26, 4)  # 右上角位置
        else:
            self.badge_widget.hide()

 