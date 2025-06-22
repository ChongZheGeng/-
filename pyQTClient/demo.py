# coding:utf-8
import os
import sys

from PyQt5.QtCore import Qt, QTimer, QUrl, QRect, QSize, pyqtSignal, QByteArray
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
                            QDesktopWidget, QGraphicsDropShadowEffect)
from qfluentwidgets import (FluentTranslator, FluentWindow, NavigationItemPosition,
                            FluentIcon as FIF, LineEdit, PasswordLineEdit,
                            PrimaryPushButton, SubtitleLabel, Dialog, qconfig, Theme,
                            SystemThemeListener, isDarkTheme, MessageBoxBase, InfoBar,
                            InfoBarPosition, TitleLabel, BodyLabel, TransparentPushButton,
                            CardWidget, FluentStyleSheet, setTheme, Theme, SmoothScrollArea,
                            StrongBodyLabel, ProgressRing, InfoBadge, InfoBadgePosition,
                            setThemeColor, SplitTitleBar, CheckBox)

from app.common.config import cfg

# 动态导入无边框窗口库
def isWin11():
    return sys.platform == 'win32' and sys.getwindowsversion().build >= 22000

if isWin11():
    from qframelesswindow import AcrylicWindow as Window
else:
    from qframelesswindow import FramelessWindow as Window

from app.api.api_client import api_client
from app.common import resource # 导入资源文件
from app.view.tool_interface import ToolInterface
from app.view.composite_material_interface import CompositeMaterialInterface
from app.view.processing_task_interface import ProcessingTaskInterface
from app.view.setting_interface import SettingInterface
from app.view.user_interface import UserInterface
from app.common.signal_bus import signalBus
from app import resource_rc # 导入编译后的资源文件


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


class MainWindow(FluentWindow):

    def __init__(self):
        super().__init__()
        self.is_logout = False
        self.initWindow()

        # create sub interface
        self.tool_interface = ToolInterface(self)
        self.material_interface = CompositeMaterialInterface(self)
        self.task_interface = ProcessingTaskInterface(self)
        self.setting_interface = SettingInterface(self)

        # 根据用户权限决定是否添加用户管理界面
        if api_client.current_user and api_client.current_user.get('is_staff'):
            self.user_interface = UserInterface(self)
        else:
            self.user_interface = None

        # connect signal to slot
        signalBus.micaEnableChanged.connect(self.setMicaEffectEnabled)
        self.setting_interface.logoutSignal.connect(self.logout)

        # add items to navigation interface
        self.initNavigation()

    def initNavigation(self):
        self.addSubInterface(
            interface=self.task_interface,
            icon=FIF.ROBOT,
            text='加工任务管理',
            position=NavigationItemPosition.TOP
        )
 
        self.addSubInterface(
            interface=self.tool_interface,
            icon=FIF.CODE,
            text='刀具管理',
            position=NavigationItemPosition.TOP
        )

        self.addSubInterface(
            interface=self.material_interface,
            icon=FIF.CONSTRACT,
            text='复合材料管理',
            position=NavigationItemPosition.TOP
        )

        # 如果用户管理界面存在，则添加到导航
        if self.user_interface:
            self.addSubInterface(
                interface=self.user_interface,
                icon=FIF.PEOPLE,
                text='用户管理',
                position=NavigationItemPosition.TOP
            )

        # add setting interface
        self.addSubInterface(
            interface=self.setting_interface,
            icon=FIF.SETTING,
            text='设置',
            position=NavigationItemPosition.BOTTOM
        )

        self.navigationInterface.setCurrentItem(self.task_interface.objectName())

    def initWindow(self):
        self.resize(1200, 800)
        self.setMinimumWidth(760)
        self.setWindowTitle("复合材料加工数据管理")
        self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        # 隐藏回退按钮
        # self.titleBar.hide()

        # create system theme listener
        self.themeListener = SystemThemeListener(self)
        # self.themeListener.themeChanged.connect(self.setMicaEffectEnabled)
        self.themeListener.start()

    def _onThemeChangedFinished(self):
        super()._onThemeChangedFinished()
        # retry to enable mica effect
        if self.isMicaEffectEnabled():
            QTimer.singleShot(100, lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()))

    def logout(self):
        """ 触发退出登录 """
        self.is_logout = True
        self.close()


class ApplicationManager:
    """应用管理器，用于控制窗口流程"""
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.setup_app_style()

        self.login_window = LoginWindow()
        self.login_window.loginSuccess.connect(self.show_main_window)
        
        self.main_window = None

    def setup_app_style(self):
        """设置应用的基础样式和国际化"""
        # enable dpi scale
        if cfg.get(cfg.dpiScale) == "Auto":
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        else:
            os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
            os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))

        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        self.app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

        # internationalization
        locale = cfg.get(cfg.language).value
        translator = FluentTranslator(locale)
        self.app.installTranslator(translator)

    def run(self):
        """启动应用"""
        self.login_window.show()
        sys.exit(self.app.exec_())

    def show_main_window(self):
        """显示主窗口"""
        self.main_window = MainWindow()
        # Connect the logout signal after showing the main window
        self.main_window.setting_interface.logoutSignal.connect(self.show_login_window)
        self.main_window.show()

        if self.login_window:
            self.login_window.close()

    def show_login_window(self):
        """显示登录窗口"""
        # 在显示新窗口前先关闭旧的，避免闪烁
        if self.main_window:
            self.main_window.is_logout = True # 标记为登出
            self.main_window.close()

        self.login_window = LoginWindow()
        self.login_window.loginSuccess.connect(self.show_main_window)
        self.login_window.show()


# --- 主程序入口 ---
if __name__ == '__main__':
    # --- 应用初始化 ---
    # 启用高分屏缩放
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

    # --- 国际化 ---
    # translator = FluentTranslator(locals())
    # app.installTranslator(translator)

    # --- 应用管理器 ---
    manager = ApplicationManager()
    manager.run()

    sys.exit(app.exec_())