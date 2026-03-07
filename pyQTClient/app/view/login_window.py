# coding:utf-8
import sys
import logging

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QByteArray
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
                             QDesktopWidget, QGraphicsDropShadowEffect, QMessageBox)
from qfluentwidgets import (setTheme, Theme, SplitTitleBar, isDarkTheme, SubtitleLabel, BodyLabel, LineEdit,
                            PasswordLineEdit, StrongBodyLabel, CheckBox, PrimaryPushButton, ProgressRing, InfoBar,
                            InfoBarPosition, setThemeColor)

# 使用相对路径导入上级包的模块
from ..api.api_client import api_client
from ..api.async_api import async_api
from ..common.config import cfg, is_auto_start_backend_enabled
from ..common import backend_launcher
from .. import resource_rc  # 导入编译后的资源文件


logger = logging.getLogger(__name__)

# 动态导入无边框窗口库
def isWin11():
    return sys.platform == 'win32' and sys.getwindowsversion().build >= 22000

if isWin11():
    from qframelesswindow import AcrylicWindow as Window
else:
    from qframelesswindow import FramelessWindow as Window


class LoginWindow(Window):
    """一个美观的分栏式登录窗口"""
    loginSuccess = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.login_successful = False
        self.health_worker = None
        self.login_worker = None
        self.pending_credentials = None
        self.backend_starting = False
        self.health_dialog_visible = False
        self.auto_start_worker = None

        # --- 主布局 (分栏) ---
        mainLayout = QHBoxLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)

        # --- 左侧 (背景图) ---
        self.backgroundLabel = QLabel(self)
        self.backgroundLabel.setScaledContents(False)
        mainLayout.addWidget(self.backgroundLabel, 1)

        # --- 右侧 (表单) ---
        self.formWidget = QWidget(self)
        self.formWidget.setObjectName("formWidget")
        self.formWidget.setMinimumSize(360, 0)
        self.formWidget.setMaximumSize(360, 16777215)
        mainLayout.addWidget(self.formWidget, 0)

        self.setLayout(mainLayout)

        # --- 初始化表单内容和信号 ---
        self.initForm()
        self.initSignals()
        self.loadSavedCredentials()

        # --- 基础设置 ---
        setTheme(Theme.AUTO)
        setThemeColor('#28afe9')
        self.setTitleBar(SplitTitleBar(self))
        self.titleBar.raise_()

        self.setWindowTitle("登录 - 复合材料加工数据管理系统")
        self.resize(1000, 650)

        # --- 窗口特效 ---
        self.windowEffect.setMicaEffect(self.winId(), isDarkMode=isDarkTheme())
        if not isWin11():
            color = QColor(39, 39, 39) if isDarkTheme() else QColor(249, 249, 249)
            self.setStyleSheet(f"background-color: {color.name()}")

        self.centerOnScreen()

    def initForm(self):
        """初始化右侧的登录表单"""
        formLayout = QVBoxLayout(self.formWidget)
        formLayout.setContentsMargins(30, 35, 30, 30)
        formLayout.setSpacing(15)

        formLayout.addStretch(1)

        title = SubtitleLabel("欢迎回来！", self.formWidget)
        title.setAlignment(Qt.AlignCenter)
        formLayout.addWidget(title)

        body = BodyLabel("请登录以继续", self.formWidget)
        body.setAlignment(Qt.AlignCenter)
        formLayout.addWidget(body)

        formLayout.addSpacing(30)

        self.username_edit = LineEdit(self.formWidget)
        self.username_edit.setPlaceholderText("用户名")
        self.username_edit.setClearButtonEnabled(True)

        self.password_edit = PasswordLineEdit(self.formWidget)
        self.password_edit.setPlaceholderText("密码")
        self.password_edit.setClearButtonEnabled(True)

        formLayout.addWidget(StrongBodyLabel("用户名", self.formWidget))
        formLayout.addWidget(self.username_edit)
        formLayout.addSpacing(10)
        formLayout.addWidget(StrongBodyLabel("密码", self.formWidget))
        formLayout.addWidget(self.password_edit)

        self.remember_checkbox = CheckBox("记住密码", self.formWidget)
        formLayout.addWidget(self.remember_checkbox)

        formLayout.addSpacing(20)

        self.loginButton = PrimaryPushButton("登录", self.formWidget)
        self.loginButton.setFixedHeight(40)
        formLayout.addWidget(self.loginButton)

        self.progressRing = ProgressRing(self.formWidget)
        self.progressRing.setFixedSize(30, 30)
        formLayout.addWidget(self.progressRing, 0, Qt.AlignCenter)
        self.progressRing.hide()

        formLayout.addStretch(2)

        copyrightLabel = BodyLabel("© 2025 复合材料加工数据管理系统", self.formWidget)
        copyrightLabel.setAlignment(Qt.AlignCenter)
        formLayout.addWidget(copyrightLabel)

    def initSignals(self):
        """初始化信号连接"""
        self.loginButton.clicked.connect(self.login)
        self.password_edit.returnPressed.connect(self.login)
        self.username_edit.returnPressed.connect(self.password_edit.setFocus)

    def loadSavedCredentials(self):
        """ 加载保存的凭据并尝试自动登录 """
        remember_me = cfg.get(cfg.rememberMe)
        self.remember_checkbox.setChecked(remember_me)

        if remember_me:
            username = cfg.get(cfg.username)
            encrypted_password = cfg.get(cfg.password)

            if username and encrypted_password:
                self.username_edit.setText(username)
                password_bytes = QByteArray.fromBase64(encrypted_password.encode('utf-8'))
                self.password_edit.setText(password_bytes.data().decode('utf-8'))

                # 让UI有时间渲染，然后再自动登录
                QTimer.singleShot(100, self.login)

    def set_loading_state(self, loading, button_text="登录"):
        """设置加载状态，避免阻塞 UI。"""
        self.username_edit.setEnabled(not loading)
        self.password_edit.setEnabled(not loading)
        self.remember_checkbox.setEnabled(not loading)
        self.loginButton.setEnabled(not loading)
        self.loginButton.setText(button_text)

        if loading:
            self.progressRing.show()
        else:
            self.progressRing.hide()
            self.loginButton.setText("登录")

    def login(self):
        """登录处理：先健康检查，再异步登录"""
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()

        if not username or not password:
            InfoBar.error("错误", "请输入用户名和密码", orient=Qt.Horizontal, isClosable=True,
                          position=InfoBarPosition.TOP, duration=3000, parent=self)
            return

        self.pending_credentials = (username, password)
        self.set_loading_state(True, "检测后端中...")

        self.health_worker = async_api.ping_health_async(
            success_callback=self.on_health_check_finished,
            error_callback=self.on_health_check_error
        )

    def on_health_check_finished(self, result):
        """健康检查成功后再发起登录请求"""
        is_ok, payload = result
        if not is_ok:
            self.on_health_check_error(payload)
            return

        self.set_loading_state(True, "登录中...")
        username, password = self.pending_credentials
        self.login_worker = async_api.login_async(
            username,
            password,
            success_callback=self.on_login_finished,
            error_callback=self.on_login_error
        )

    def on_health_check_error(self, error_message):
        self.set_loading_state(False)
        if self.health_dialog_visible:
            return

        self.health_dialog_visible = True
        should_retry = self.show_backend_error_dialog(
            title="连接失败",
            message=f"后端未启动/连接失败。\n\n{error_message}\n\n请先启动 Django 服务后重试。",
            manual_command=backend_launcher.build_manual_command(),
            allow_retry=True
        )
        self.health_dialog_visible = False
        if should_retry:
            self.retry_health_check()

    def retry_health_check(self):
        """点击 Retry 后的流程：先快速探活，再视配置自动拉起后端。"""
        if self.backend_starting:
            return

        self.set_loading_state(True, "重试检测后端中...")
        self.health_worker = async_api.ping_health_async(
            success_callback=self.on_retry_health_finished,
            error_callback=self.on_retry_health_error
        )

    def on_retry_health_error(self, error_message):
        self.on_retry_health_finished((False, str(error_message)))

    def on_retry_health_finished(self, result):
        is_ok, payload = result
        if is_ok:
            logger.info("Retry 阶段健康检查成功，继续登录")
            self.on_health_check_finished(result)
            return

        if not is_auto_start_backend_enabled():
            self.set_loading_state(False)
            logger.info("自动拉起后端未启用，保持原有重试提示")
            self.on_health_check_error(payload)
            return

        self.start_backend_auto_flow(payload)

    def start_backend_auto_flow(self, last_error):
        if self.backend_starting:
            logger.info("后端已在启动中，忽略重复启动请求")
            return

        self.backend_starting = True
        self.set_loading_state(True, "正在自动启动后端...")
        logger.info("开始执行后端自动拉起流程，最后一次健康检查错误: %s", last_error)
        self.auto_start_worker = async_api.call_async(
            self._start_backend_and_wait,
            self.on_backend_auto_flow_finished,
            self.on_backend_auto_flow_error,
            str(last_error)
        )

    def _start_backend_and_wait(self, last_error):
        repo_root = backend_launcher.find_repo_root()
        if not repo_root:
            manual_cmd = backend_launcher.build_manual_command()
            logger.warning("自动拉起失败：未找到 manage.py")
            return {
                "ok": False,
                "message": f"未找到 DjangoService/manage.py。最后错误: {last_error}",
                "manual_command": manual_cmd
            }

        manual_cmd = backend_launcher.build_manual_command(repo_root)
        try:
            process = backend_launcher.start_django_server(repo_root)
            ok, elapsed, wait_message = backend_launcher.wait_for_health(timeout_seconds=25, interval_seconds=0.5)
            logger.info("后端自动拉起等待结果: ok=%s elapsed=%.2fs detail=%s", ok, elapsed, wait_message)
            if ok:
                return {
                    "ok": True,
                    "message": f"后端已就绪，耗时 {elapsed:.1f}s",
                    "manual_command": manual_cmd,
                    "pid": process.pid,
                }

            return {
                "ok": False,
                "message": f"自动启动后端后等待超时（{elapsed:.1f}s）：{wait_message}",
                "manual_command": manual_cmd,
                "pid": process.pid,
            }
        except Exception as e:
            logger.exception("自动启动后端异常")
            return {
                "ok": False,
                "message": f"自动启动后端异常: {e}",
                "manual_command": manual_cmd,
            }

    def on_backend_auto_flow_error(self, error_message):
        self.backend_starting = False
        self.set_loading_state(False)
        logger.error("后端自动拉起流程线程异常: %s", error_message)
        self.show_backend_error_dialog(
            title="自动启动失败",
            message=f"自动启动后端失败：{error_message}",
            manual_command=backend_launcher.build_manual_command(),
            allow_retry=False
        )

    def on_backend_auto_flow_finished(self, result):
        self.backend_starting = False
        if result.get("ok"):
            logger.info("自动启动成功: pid=%s %s", result.get("pid"), result.get("message"))
            self.set_loading_state(True, "后端已就绪，登录中...")
            username, password = self.pending_credentials
            self.login_worker = async_api.login_async(
                username,
                password,
                success_callback=self.on_login_finished,
                error_callback=self.on_login_error
            )
            return

        self.set_loading_state(False)
        logger.warning("自动启动失败: %s", result.get("message"))
        self.show_backend_error_dialog(
            title="自动启动失败",
            message=result.get("message", "未知错误"),
            manual_command=result.get("manual_command"),
            allow_retry=True
        )

    def show_backend_error_dialog(self, title, message, manual_command=None, allow_retry=True):
        """统一显示后端失败提示，并支持复制手动启动命令。"""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(title)
        box.setText(message)

        if manual_command:
            box.setInformativeText(f"可手动执行：\n{manual_command}")

        if allow_retry:
            box.setStandardButtons(QMessageBox.Retry | QMessageBox.Cancel)
            box.setDefaultButton(QMessageBox.Retry)
        else:
            box.setStandardButtons(QMessageBox.Ok)

        copy_button = None
        if manual_command:
            copy_button = box.addButton("复制启动命令", QMessageBox.ActionRole)

        box.exec_()
        clicked = box.clickedButton()
        if copy_button and clicked == copy_button:
            QApplication.clipboard().setText(manual_command)
            InfoBar.success(
                "已复制",
                "启动命令已复制到剪贴板",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2500,
                parent=self
            )

        return allow_retry and box.standardButton(clicked) == QMessageBox.Retry

    def on_login_finished(self, result):
        success, message = result
        self.set_loading_state(False)

        if success:
            username, password = self.pending_credentials
            if self.remember_checkbox.isChecked():
                password_bytes = QByteArray(password.encode('utf-8'))
                encrypted_password = password_bytes.toBase64().data().decode('utf-8')
                cfg.set(cfg.username, username)
                cfg.set(cfg.password, encrypted_password)
                cfg.set(cfg.rememberMe, True)
            else:
                cfg.set(cfg.username, '')
                cfg.set(cfg.password, '')
                cfg.set(cfg.rememberMe, False)

            self.login_successful = True
            self.loginSuccess.emit()
        else:
            InfoBar.error("登录失败", message, orient=Qt.Horizontal, isClosable=True,
                          position=InfoBarPosition.TOP, duration=3000, parent=self)

    def on_login_error(self, error_message):
        self.set_loading_state(False)
        InfoBar.error("登录失败", str(error_message), orient=Qt.Horizontal, isClosable=True,
                      position=InfoBarPosition.TOP, duration=3000, parent=self)

    def accept(self):
        """模拟Dialog的accept方法"""
        self.login_successful = True
        self.close()

    def centerOnScreen(self):
        """将窗口居中显示在屏幕上"""
        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

    def resizeEvent(self, e):
        super().resizeEvent(e)

        # 加载原始图像
        original_pixmap = QPixmap(":/resource/background.png")
        if original_pixmap.isNull():
            return

        # 目标宽高比
        target_ar = 2240 / 2160

        # 原始尺寸和宽高比
        w = original_pixmap.width()
        h = original_pixmap.height()

        # 避免除以零
        if h == 0:
            return

        original_ar = w / h

        # 将图像裁剪为目标宽高比
        cropped_pixmap = original_pixmap
        if original_ar > target_ar:
            # 图像过宽，裁剪宽度
            new_w = int(h * target_ar)
            x_offset = (w - new_w) // 2
            cropped_pixmap = original_pixmap.copy(x_offset, 0, new_w, h)
        elif original_ar < target_ar:
            # 图像过高，裁剪高度
            new_h = int(w / target_ar)
            y_offset = (h - new_h) // 2
            cropped_pixmap = original_pixmap.copy(0, y_offset, w, new_h)

        # 缩放裁剪后的图像以填充标签
        scaled_pixmap = cropped_pixmap.scaled(
            self.backgroundLabel.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        self.backgroundLabel.setPixmap(scaled_pixmap) 
