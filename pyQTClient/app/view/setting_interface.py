# coding:utf-8
from PyQt5.QtCore import pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, Qt
from PyQt5.QtWidgets import QVBoxLayout, QScrollArea, QWidget, QLabel
from qfluentwidgets import (FluentIcon as FIF, SubtitleLabel,
                            OptionsSettingCard, SettingCardGroup, setTheme)

from .components.setting_component import UserInfoCard, LogoutCard, WebDAVCard
from .nav_interface import NavInterface  # 继承保持与代码2一致
from ..api.api_client import api_client
from ..common.config import cfg


class SettingInterface(NavInterface):  # 继承NavInterface，与代码2一致
    """设置界面（保留滚动布局，功能与代码2完全一致）"""

    logoutSignal = pyqtSignal()  # 保留退出信号

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingInterface")

        # === 保留代码1的滚动布局框架 ===
        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建滚动区域
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_layout.addWidget(self.scrollArea)

        # 滚动区域内容容器
        self.contentWidget = QWidget()
        self.contentLayout = QVBoxLayout(self.contentWidget)
        # 复用代码2的边距设置
        self.contentLayout.setContentsMargins(40, 30, 40, 30)
        self.contentLayout.setSpacing(30)
        self.scrollArea.setWidget(self.contentWidget)

        # === 以下内容完全复用代码2的功能组件 ===
        # 标题
        self.contentLayout.addWidget(SubtitleLabel("设置"))

        # 个性化设置组
        self.personalGroup = SettingCardGroup("个性化", self.contentWidget)
        self.themeCard = OptionsSettingCard(
            cfg.themeMode,
            FIF.BRUSH,
            '应用主题',
            "改变应用的外观",
            texts=['亮色', '暗色', '跟随系统'],
            parent=self.personalGroup
        )
        self.personalGroup.addSettingCard(self.themeCard)
        self.contentLayout.addWidget(self.personalGroup)

        # WebDAV 设置卡片
        self.webdavCard = WebDAVCard(self.contentWidget)
        self.contentLayout.addWidget(self.webdavCard)

        # 用户信息卡片
        self.userInfoCard = UserInfoCard(self.contentWidget)
        self.contentLayout.addWidget(self.userInfoCard)

        # 退出登录卡片
        self.logoutCard = LogoutCard(self.contentWidget)
        self.contentLayout.addWidget(self.logoutCard)

        # 弹性空间
        self.contentLayout.addStretch(1)

        # 信号连接（与代码2完全一致）
        self.logoutCard.logoutButton.clicked.connect(self.logoutSignal.emit)
        cfg.themeChanged.connect(setTheme)

        # 测试滚动（可选，实际使用时可删除）
        # self.scrollToWidget(self.userInfoCard)

    # === 完全保留代码2的功能方法 ===
    def scrollToWidget(self, widget):
        """平滑滚动到指定控件（代码1的特色功能保留）"""
        def _scroll():
            bar = self.scrollArea.verticalScrollBar()
            top = widget.pos().y()
            current_value = bar.value()
            target_value = top - 30  # 顶部留白

            animation = QPropertyAnimation(bar, b"value", self)
            animation.setDuration(400)
            animation.setStartValue(current_value)
            animation.setEndValue(target_value)
            animation.setEasingCurve(QEasingCurve.InOutCubic)
            animation.start()
            self._scrollAnimation = animation  # 防止被垃圾回收

        QTimer.singleShot(100, _scroll)

    def on_activated(self):
        """界面激活时加载用户信息（与代码2一致）"""
        self.load_user_info()

    def on_deactivated(self):
        """界面停用处理（与代码2一致）"""
        pass

    def load_user_info(self):
        """加载用户信息（与代码2一致）"""
        user_info = api_client.get_current_user_info()
        if user_info:
            self.userInfoCard.update_info(user_info)

    def on_personnel_changed(self, personnel_id):
        """人员切换时更新信息（与代码2一致）"""
        self.load_user_info()