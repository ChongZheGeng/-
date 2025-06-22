# coding:utf-8
import os
import sys

from PyQt5.QtCore import Qt, QTimer, QUrl, QRect, QSize
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
                            QDesktopWidget, QGraphicsDropShadowEffect)
from qfluentwidgets import (FluentTranslator, FluentWindow, NavigationItemPosition,
                            FluentIcon as FIF, LineEdit, PasswordLineEdit,
                            PrimaryPushButton, SubtitleLabel, Dialog, qconfig, Theme,
                            SystemThemeListener, isDarkTheme, MessageBoxBase, InfoBar,
                            InfoBarPosition, TitleLabel, BodyLabel, TransparentPushButton,
                            CardWidget, FluentStyleSheet, setTheme, Theme, SmoothScrollArea,
                            StrongBodyLabel, ProgressRing, InfoBadge, InfoBadgePosition)

from app.api.api_client import api_client
from app.common.config import cfg
# from app.view.main_window import MainWindow
from app.view.tool_interface import ToolInterface
from app.view.composite_material_interface import CompositeMaterialInterface
from app.view.processing_task_interface import ProcessingTaskInterface
from app.view.setting_interface import SettingInterface
from app.view.user_interface import UserInterface
from app.common.signal_bus import signalBus


class LoginWindow(QWidget):
    """美观的登录窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.login_successful = False
        
        self.initUI()
        self.initLayout()
        self.initSignals()
        
        # 设置窗口居中
        self.centerOnScreen()
        
        # 应用样式
        setTheme(Theme.AUTO)
        
        # 添加窗口阴影效果
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        """绘制圆角背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        
        # 根据主题设置背景色
        if isDarkTheme():
            brush_color = QColor(39, 39, 39)
        else:
            brush_color = QColor(249, 249, 249)
            
        painter.setBrush(QBrush(brush_color))
        painter.drawRoundedRect(self.rect(), 10, 10)

    def initUI(self):
        """初始化UI组件"""
        self.setObjectName("loginWindow")
        self.setFixedSize(400, 500)
        self.setWindowTitle("登录")
        
        # 关闭按钮
        self.closeButton = TransparentPushButton(self)
        self.closeButton.setIcon(FIF.CLOSE)
        self.closeButton.setFixedSize(34, 34)
        self.closeButton.setIconSize(QSize(12, 12))
        self.closeButton.setToolTip("关闭")
        self.closeButton.move(self.width() - self.closeButton.width() - 5, 5)
        
        # 标题和图标
        self.titleLabel = TitleLabel("复合材料加工数据管理系统", self)
        self.titleLabel.setAlignment(Qt.AlignCenter)
        
        # 创建一个卡片作为登录表单的容器
        self.loginCard = CardWidget(self)
        self.loginCard.setObjectName("loginCard")
        
        # 登录表单标题
        self.loginTitle = SubtitleLabel("用户登录", self.loginCard)
        self.loginTitle.setAlignment(Qt.AlignCenter)
        
        # 用户名输入框
        self.usernameLabel = StrongBodyLabel("用户名", self.loginCard)
        self.username_edit = LineEdit(self.loginCard)
        self.username_edit.setPlaceholderText("请输入用户名")
        self.username_edit.setClearButtonEnabled(True)
        
        # 密码输入框
        self.passwordLabel = StrongBodyLabel("密码", self.loginCard)
        self.password_edit = PasswordLineEdit(self.loginCard)
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.setClearButtonEnabled(True)
        
        # 登录按钮
        self.loginButton = PrimaryPushButton("登录", self.loginCard)
        self.loginButton.setFixedHeight(40)
        
        # 取消按钮
        self.cancelButton = TransparentPushButton("取消", self.loginCard)
        
        # 进度指示器
        self.progressRing = ProgressRing(self.loginCard)
        self.progressRing.setFixedSize(30, 30)
        self.progressRing.hide()
        
        # 底部版权信息
        self.copyrightLabel = BodyLabel("© 2025 复合材料加工数据管理系统", self)
        self.copyrightLabel.setAlignment(Qt.AlignCenter)

    def initLayout(self):
        """初始化布局"""
        # 主布局
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(20, 20, 20, 20)
        mainLayout.setSpacing(15)
        
        # 添加标题
        mainLayout.addWidget(self.titleLabel)
        mainLayout.addSpacing(20)
        
        # 登录卡片布局
        cardLayout = QVBoxLayout(self.loginCard)
        cardLayout.setContentsMargins(20, 20, 20, 20)
        cardLayout.setSpacing(10)
        
        cardLayout.addWidget(self.loginTitle)
        cardLayout.addSpacing(20)
        
        cardLayout.addWidget(self.usernameLabel)
        cardLayout.addWidget(self.username_edit)
        cardLayout.addSpacing(10)
        
        cardLayout.addWidget(self.passwordLabel)
        cardLayout.addWidget(self.password_edit)
        cardLayout.addSpacing(20)
        
        # 按钮和进度条布局
        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.progressRing)
        buttonLayout.addWidget(self.loginButton)
        buttonLayout.addWidget(self.cancelButton)
        cardLayout.addLayout(buttonLayout)
        
        # 添加登录卡片到主布局
        mainLayout.addWidget(self.loginCard)
        mainLayout.addStretch(1)
        mainLayout.addWidget(self.copyrightLabel)

    def initSignals(self):
        """初始化信号连接"""
        self.closeButton.clicked.connect(self.close)
        self.loginButton.clicked.connect(self.login)
        self.cancelButton.clicked.connect(self.close)
        self.password_edit.returnPressed.connect(self.login)
        self.username_edit.returnPressed.connect(lambda: self.password_edit.setFocus())

    def login(self):
        """登录处理"""
        username = self.username_edit.text()
        password = self.password_edit.text()
        
        if not username or not password:
            InfoBar.error(
                title="错误",
                content="请输入用户名和密码",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        # 显示加载状态
        self.progressRing.show()
        self.loginButton.setEnabled(False)
        self.cancelButton.setEnabled(False)
        QApplication.processEvents()
        
        # 调用登录API
        success, message = api_client.login(username, password)
        
        # 恢复按钮状态
        self.progressRing.hide()
        self.loginButton.setEnabled(True)
        self.cancelButton.setEnabled(True)
        
        if success:
            self.login_successful = True
            self.accept()
        else:
            InfoBar.error(
                title="登录失败",
                content=message,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def accept(self):
        """模拟Dialog的accept方法"""
        self.login_successful = True
        self.close()

    def centerOnScreen(self):
        """将窗口居中显示在屏幕上"""
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2,
                 (screen.height() - size.height()) // 2)

    def mousePressEvent(self, event):
        """实现窗口拖动"""
        if event.button() == Qt.LeftButton:
            self._isTracking = True
            self._startPos = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        """实现窗口拖动"""
        if self._isTracking and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._startPos)
            event.accept()

    def mouseReleaseEvent(self, event):
        """实现窗口拖动"""
        self._isTracking = False


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
        self.initWindow()

    def initNavigation(self):
        self.stackedWidget.addWidget(self.task_interface)
        self.stackedWidget.addWidget(self.tool_interface)
        self.stackedWidget.addWidget(self.material_interface)

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
            self.stackedWidget.addWidget(self.user_interface)
            self.addSubInterface(
                interface=self.user_interface,
                icon=FIF.PEOPLE,
                text='用户管理',
                position=NavigationItemPosition.TOP
            )

        # add setting interface
        self.stackedWidget.addWidget(self.setting_interface)
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


# --- 主程序入口 ---
if __name__ == '__main__':
    # enable dpi scale
    if cfg.get(cfg.dpiScale) == "Auto":
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    else:
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))

    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # create application
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

    # internationalization
    locale = cfg.get(cfg.language).value
    translator = FluentTranslator(locale)
    app.installTranslator(translator)
    
    while True:
        # login logic
        login_window = LoginWindow()
        login_window.show()
        app.exec_()
        
        if login_window.login_successful:
            main_window = MainWindow()
            main_window.show()
            app.exec_()
            
            # 如果是退出登录，则循环继续，否则退出
            if main_window.is_logout:
                continue
            else:
                break
        else:
            # 用户取消登录或登录失败
            break