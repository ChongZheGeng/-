# coding:utf-8
import sys

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QByteArray
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
                             QDesktopWidget, QGraphicsDropShadowEffect)
from qfluentwidgets import (setTheme, Theme, SplitTitleBar, isDarkTheme, SubtitleLabel, BodyLabel, LineEdit,
                            PasswordLineEdit, StrongBodyLabel, CheckBox, PrimaryPushButton, ProgressRing, InfoBar,
                            InfoBarPosition, setThemeColor)

# 使用相对路径导入上级包的模块
from ..api.api_client import api_client
from ..common.config import cfg
from .. import resource_rc  # 导入编译后的资源文件

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

    def login(self):
        """登录处理"""
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()

        if not username or not password:
            InfoBar.error("错误", "请输入用户名和密码", orient=Qt.Horizontal, isClosable=True,
                          position=InfoBarPosition.TOP, duration=3000, parent=self)
            return

        # 切换到加载状态
        self.username_edit.setEnabled(False)
        self.password_edit.setEnabled(False)
        self.loginButton.hide()
        self.progressRing.show()
        QApplication.processEvents()

        success, message = api_client.login(username, password)

        # 恢复正常状态
        self.username_edit.setEnabled(True)
        self.password_edit.setEnabled(True)
        self.loginButton.show()
        self.progressRing.hide()

        if success:
            # 保存或清除凭据
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