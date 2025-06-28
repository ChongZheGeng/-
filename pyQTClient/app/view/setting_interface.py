# coding:utf-8
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtGui import QColor

from qfluentwidgets import (StrongBodyLabel, BodyLabel, ComboBox, PrimaryPushButton, 
                           InfoBar, CardWidget, FluentIcon as FIF, IconWidget, SubtitleLabel,
                           qconfig, Theme, OptionsSettingCard, SettingCardGroup, setTheme,
                           LineEdit, PasswordLineEdit, SwitchButton, CaptionLabel)

from ..api.api_client import api_client
from ..common.config import cfg, save_webdav_credentials, get_webdav_credentials, test_webdav_connection
from .nav_interface import NavInterface


class WebDAVCard(CardWidget):
    """WebDAV设置卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.setSpacing(15)

        # 标题
        title_layout = QHBoxLayout()
        self.iconWidget = IconWidget(FIF.SYNC, self)
        self.titleLabel = SubtitleLabel("WebDAV 连接", self)
        title_layout.addWidget(self.iconWidget)
        title_layout.addWidget(self.titleLabel)
        title_layout.addStretch(1)
        
        # 启用/禁用 WebDAV 开关
        self.enableSwitch = SwitchButton(self)
        title_layout.addWidget(self.enableSwitch)
        
        self.vBoxLayout.addLayout(title_layout)

        # 分隔线
        self.separator = QFrame(self)
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        self.vBoxLayout.addWidget(self.separator)

        # 描述
        self.descriptionLabel = BodyLabel("配置 WebDAV 连接，以便上传传感器数据到云存储。", self)
        self.vBoxLayout.addWidget(self.descriptionLabel)

        # 服务器地址
        self.vBoxLayout.addWidget(StrongBodyLabel("服务器地址:"))
        self.urlEdit = LineEdit(self)
        self.urlEdit.setPlaceholderText("例如：https://dav.example.com")
        self.vBoxLayout.addWidget(self.urlEdit)

        # 用户名
        self.vBoxLayout.addWidget(StrongBodyLabel("用户名:"))
        self.usernameEdit = LineEdit(self)
        self.vBoxLayout.addWidget(self.usernameEdit)

        # 密码
        self.vBoxLayout.addWidget(StrongBodyLabel("密码:"))
        self.passwordEdit = PasswordLineEdit(self)
        self.vBoxLayout.addWidget(self.passwordEdit)

        # 状态提示
        self.statusLabel = CaptionLabel("", self)
        self.statusLabel.setHidden(True)
        self.vBoxLayout.addWidget(self.statusLabel)

        # 测试连接按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)
        self.testButton = PrimaryPushButton("测试连接", self)
        self.saveButton = PrimaryPushButton("保存凭据", self)
        buttons_layout.addWidget(self.testButton)
        buttons_layout.addWidget(self.saveButton)
        self.vBoxLayout.addLayout(buttons_layout)

        # 连接信号
        self.testButton.clicked.connect(self.test_connection)
        self.saveButton.clicked.connect(self.save_credentials)
        self.enableSwitch.checkedChanged.connect(self.on_enable_switch)

        # 加载保存的凭据
        self.load_saved_credentials()

    def load_saved_credentials(self):
        """加载保存的WebDAV凭据"""
        credentials = get_webdav_credentials()
        if credentials:
            self.enableSwitch.setChecked(credentials['enabled'])
            self.urlEdit.setText(credentials['url'])
            self.usernameEdit.setText(credentials['username'])
            self.passwordEdit.setText(credentials['password'])
            
            # 启用或禁用输入字段
            self.set_fields_enabled(credentials['enabled'])
        else:
            self.enableSwitch.setChecked(False)
            self.set_fields_enabled(False)

    def save_credentials(self):
        """保存WebDAV凭据"""
        url = self.urlEdit.text().strip()
        username = self.usernameEdit.text().strip()
        password = self.passwordEdit.text()
        
        if not url:
            self.show_status(False, "服务器地址不能为空")
            return
            
        if not username:
            self.show_status(False, "用户名不能为空")
            return
            
        if not password:
            self.show_status(False, "密码不能为空")
            return
        
        # 保存凭据
        save_webdav_credentials(url, username, password, self.enableSwitch.isChecked())
        self.show_status(True, "凭据已保存")
        
    def test_connection(self):
        """测试WebDAV连接"""
        url = self.urlEdit.text().strip()
        username = self.usernameEdit.text().strip()
        password = self.passwordEdit.text()
        
        if not url:
            self.show_status(False, "服务器地址不能为空")
            return
            
        if not username:
            self.show_status(False, "用户名不能为空")
            return
            
        if not password:
            self.show_status(False, "密码不能为空")
            return
        
        # 显示测试中状态
        self.statusLabel.setText("正在测试连接...")
        self.statusLabel.setHidden(False)
        self.statusLabel.setTextColor("#808080")
        
        # 测试连接
        success, message = test_webdav_connection(url, username, password)
        self.show_status(success, message)
        
    def show_status(self, success, message):
        """显示状态信息"""
        self.statusLabel.setText(message)
        self.statusLabel.setHidden(False)
        
        if success:
            self.statusLabel.setTextColor("#0a805e")  # 绿色
        else:
            self.statusLabel.setTextColor("#cf1010")  # 红色
    
    def on_enable_switch(self, enabled):
        """启用/禁用 WebDAV 时的回调"""
        self.set_fields_enabled(enabled)
        if enabled:
            self.statusLabel.setHidden(True)
        else:
            self.show_status(False, "WebDAV 已禁用")
    
    def set_fields_enabled(self, enabled):
        """设置所有输入字段的启用状态"""
        self.urlEdit.setEnabled(enabled)
        self.usernameEdit.setEnabled(enabled)
        self.passwordEdit.setEnabled(enabled)
        self.testButton.setEnabled(enabled)
        self.saveButton.setEnabled(enabled)


class LogoutCard(CardWidget):
    """退出登录卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.setSpacing(10)

        # 标题
        title_layout = QHBoxLayout()
        self.iconWidget = IconWidget(FIF.CLOSE, self)
        self.titleLabel = SubtitleLabel("安全退出", self)
        title_layout.addWidget(self.iconWidget)
        title_layout.addWidget(self.titleLabel)
        title_layout.addStretch(1)
        self.vBoxLayout.addLayout(title_layout)

        # 描述
        self.descriptionLabel = BodyLabel("您将退出当前账户并返回到登录页面。", self)
        self.vBoxLayout.addWidget(self.descriptionLabel)

        # 按钮
        self.logoutButton = PrimaryPushButton("退出登录", self)
        self.logoutButton.setFixedWidth(120)
        self.vBoxLayout.addWidget(self.logoutButton, 0, Qt.AlignRight)


class UserInfoCard(CardWidget):
    """用户信息卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(200)
        
        # 创建布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.setSpacing(10)
        
        # 标题
        title_layout = QHBoxLayout()
        self.iconWidget = IconWidget(FIF.PEOPLE, self)
        self.titleLabel = SubtitleLabel("用户信息", self)
        title_layout.addWidget(self.iconWidget)
        title_layout.addWidget(self.titleLabel)
        title_layout.addStretch(1)
        self.vBoxLayout.addLayout(title_layout)
        
        # 分隔线
        self.separator = QFrame(self)
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        self.vBoxLayout.addWidget(self.separator)
        
        # 用户信息
        self.usernameLabel = StrongBodyLabel("用户名：", self)
        self.emailLabel = StrongBodyLabel("邮箱：", self)
        self.nameLabel = StrongBodyLabel("姓名：", self)
        
        self.vBoxLayout.addWidget(self.usernameLabel)
        self.vBoxLayout.addWidget(self.emailLabel)
        self.vBoxLayout.addWidget(self.nameLabel)
        
        self.vBoxLayout.addStretch(1)

    def update_info(self, user_info):
        """更新用户信息"""
        if not user_info:
            return
            
        self.usernameLabel.setText(f"用户名：{user_info.get('username', 'N/A')}")
        self.emailLabel.setText(f"邮箱：{user_info.get('email', 'N/A')}")
        
        name = user_info.get('first_name', '')
        if user_info.get('last_name'):
            name += f" {user_info.get('last_name')}"
        self.nameLabel.setText(f"姓名：{name or 'N/A'}")


class PersonnelSelectionCard(CardWidget):
    """人员选择卡片"""
    
    personnelChanged = pyqtSignal(int)  # 当选择的人员改变时发出信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(200)
        
        # 创建布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.setSpacing(10)
        
        # 标题
        title_layout = QHBoxLayout()
        self.iconWidget = IconWidget(FIF.PEOPLE, self)
        self.titleLabel = SubtitleLabel("关联人员", self)
        title_layout.addWidget(self.iconWidget)
        title_layout.addWidget(self.titleLabel)
        title_layout.addStretch(1)
        self.vBoxLayout.addLayout(title_layout)
        
        # 分隔线
        self.separator = QFrame(self)
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        self.vBoxLayout.addWidget(self.separator)
        
        # 人员选择
        self.descriptionLabel = BodyLabel("请选择您的关联人员：", self)
        self.vBoxLayout.addWidget(self.descriptionLabel)
        
        self.personnelCombo = ComboBox(self)
        self.vBoxLayout.addWidget(self.personnelCombo)
        
        self.applyButton = PrimaryPushButton("应用", self)
        self.vBoxLayout.addWidget(self.applyButton, 0, Qt.AlignRight)
        
        self.vBoxLayout.addStretch(1)
        
        # 连接信号
        self.applyButton.clicked.connect(self._on_apply_clicked)
        
        # 加载人员列表
        self.load_personnel()
        
    def load_personnel(self):
        """加载人员列表"""
        self.personnelCombo.clear()
        personnel_list = api_client.get_personnel()
        
        if personnel_list and 'results' in personnel_list:
            for person in personnel_list['results']:
                display_text = f"{person['name']}"
                if person.get('employee_id'):
                    display_text += f" ({person['employee_id']})"
                self.personnelCombo.addItem(display_text, userData=person['id'])
                
            # 如果当前用户已关联人员，则选中对应项
            if api_client.current_user and api_client.current_user.get('personnel'):
                personnel_id = api_client.current_user['personnel']['id']
                for i in range(self.personnelCombo.count()):
                    if self.personnelCombo.itemData(i) == personnel_id:
                        self.personnelCombo.setCurrentIndex(i)
                        break
    
    def _on_apply_clicked(self):
        """应用按钮点击事件"""
        if self.personnelCombo.currentIndex() < 0:
            InfoBar.warning("提示", "请选择一个人员", parent=self.window())
            return
            
        personnel_id = self.personnelCombo.currentData()
        result = api_client.set_current_user_personnel(personnel_id)
        
        if result:
            InfoBar.success("成功", "人员关联已更新", parent=self.window())
            self.personnelChanged.emit(personnel_id)
        else:
            InfoBar.error("错误", "更新人员关联失败", parent=self.window())


class SettingInterface(NavInterface):
    """设置界面"""
    
    logoutSignal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingInterface")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)
        
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