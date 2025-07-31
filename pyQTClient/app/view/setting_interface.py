# coding:utf-8
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout
from qfluentwidgets import (FluentIcon as FIF, SubtitleLabel,
                            OptionsSettingCard, SettingCardGroup, setTheme)

from .components.setting_component import UserInfoCard, LogoutCard, WebDAVCard
from .nav_interface import NavInterface
from ..api.api_client import api_client
from ..common.config import cfg


class SettingInterface(NavInterface):
    """设置界面"""

    logoutSignal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingInterface")

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(40, 30, 40, 30)
        self.main_layout.setSpacing(30)

        # 标题
        self.main_layout.addWidget(SubtitleLabel("设置"))

        # --- 个性化设置 ---
        self.personalGroup = SettingCardGroup("个性化", self)

        # 主题设置
        self.themeCard = OptionsSettingCard(
            cfg.themeMode,
            FIF.BRUSH,
            '应用主题',
            "改变应用的外观",
            texts=['亮色', '暗色', '跟随系统'],
            parent=self.personalGroup
        )
        self.personalGroup.addSettingCard(self.themeCard)
        self.main_layout.addWidget(self.personalGroup)

        # WebDAV 设置卡片
        self.webdavCard = WebDAVCard(self)
        self.main_layout.addWidget(self.webdavCard)

        # 用户信息卡片
        self.userInfoCard = UserInfoCard(self)
        self.main_layout.addWidget(self.userInfoCard)

        # 退出登录卡片
        self.logoutCard = LogoutCard(self)
        self.main_layout.addWidget(self.logoutCard)

        # 添加一个弹性空间
        self.main_layout.addStretch(1)

        # 连接信号
        self.logoutCard.logoutButton.clicked.connect(self.logoutSignal.emit)
        cfg.themeChanged.connect(setTheme)

    def on_activated(self):
        """
        当界面被激活时调用（例如，通过导航切换到此界面）。
        设置界面主要处理本地配置，但需要加载当前用户信息。
        """
        # 加载当前用户信息
        self.load_user_info()

    def on_deactivated(self):
        """
        当界面被切换离开时调用。
        设置界面通常不需要特殊的清理工作。
        """
        pass

    def load_user_info(self):
        """加载当前用户信息"""
        user_info = api_client.get_current_user_info()
        if user_info:
            self.userInfoCard.update_info(user_info)

    def on_personnel_changed(self, personnel_id):
        """当选择的人员改变时更新用户信息"""
        self.load_user_info()
