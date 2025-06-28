# coding:utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QAbstractItemView, QCheckBox

from qfluentwidgets import (TableWidget, PushButton, StrongBodyLabel, LineEdit, ComboBox,
                            TextEdit, PrimaryPushButton, MessageBox, InfoBar, MessageBoxBase, 
                            SubtitleLabel, PasswordLineEdit)

from pyQTClient.app.view.nav_interface import NavInterface

from ..api.api_client import api_client
from ..api.data_manager import interface_loader
import logging

# 设置logger
logger = logging.getLogger(__name__)


class UserEditDialog(MessageBoxBase):
    """ 用于编辑或添加用户的自定义对话框 """

    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.user_data = user_data
        self.is_edit_mode = user_data is not None

        self.titleLabel = SubtitleLabel("编辑用户" if self.is_edit_mode else "新增用户", self)
        self.viewLayout.addWidget(self.titleLabel)
        
        # --- 创建表单控件 ---
        self.username_label = StrongBodyLabel("用户名:", self)
        self.username_edit = LineEdit(self)
        
        self.password_label = StrongBodyLabel("密码:", self)
        self.password_edit = PasswordLineEdit(self)
        
        self.first_name_label = StrongBodyLabel("名字:", self)
        self.first_name_edit = LineEdit(self)
        
        self.last_name_label = StrongBodyLabel("姓氏:", self)
        self.last_name_edit = LineEdit(self)
        
        self.email_label = StrongBodyLabel("邮箱:", self)
        self.email_edit = LineEdit(self)

        self.is_active_checkbox = QCheckBox("是否激活", self)
        self.is_staff_checkbox = QCheckBox("是否职员", self)

        # --- 布局 ---
        self.viewLayout.addWidget(self.username_label)
        self.viewLayout.addWidget(self.username_edit)
        self.viewLayout.addWidget(self.password_label)
        self.viewLayout.addWidget(self.password_edit)
        self.viewLayout.addWidget(self.first_name_label)
        self.viewLayout.addWidget(self.first_name_edit)
        self.viewLayout.addWidget(self.last_name_label)
        self.viewLayout.addWidget(self.last_name_edit)
        self.viewLayout.addWidget(self.email_label)
        self.viewLayout.addWidget(self.email_edit)
        self.viewLayout.addWidget(self.is_active_checkbox)
        self.viewLayout.addWidget(self.is_staff_checkbox)
        
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(400)

        # --- 根据模式设置初始值和控件状态 ---
        self.setup_mode()

    def setup_mode(self):
        """ 根据是编辑模式还是新增模式来设置控件 """
        if self.is_edit_mode:
            self.username_edit.setText(self.user_data.get('username', ''))
            self.username_edit.setReadOnly(True) # 用户名通常不允许修改
            self.password_edit.setPlaceholderText("留空表示不修改密码")
            
            self.first_name_edit.setText(self.user_data.get('first_name', ''))
            self.last_name_edit.setText(self.user_data.get('last_name', ''))
            self.email_edit.setText(self.user_data.get('email', ''))
            self.is_active_checkbox.setChecked(self.user_data.get('is_active', True))
            self.is_staff_checkbox.setChecked(self.user_data.get('is_staff', False))
        else:
            # 新增模式
            self.username_edit.setPlaceholderText("必填")
            self.password_edit.setPlaceholderText("必填")
            self.is_active_checkbox.setChecked(True)

    def get_data(self):
        """ 获取表单中的数据 """
        username = self.username_edit.text().strip()
        if not username:
            return None, "用户名不能为空"

        data = {
            "username": username,
            "first_name": self.first_name_edit.text().strip(),
            "last_name": self.last_name_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "is_active": self.is_active_checkbox.isChecked(),
            "is_staff": self.is_staff_checkbox.isChecked(),
        }

        # 处理密码
        password = self.password_edit.text()
        if not self.is_edit_mode and not password:
            return None, "新增用户时密码不能为空"
        if password:
            data['password'] = password
            
        return data, None

    def validate(self):
        data, error_msg = self.get_data()
        if data is None:
            InfoBar.warning("提示", error_msg, duration=3000, parent=self)
            return False
        return True


class UserInterface(NavInterface):
    """ 用户管理主界面 """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("UserInterface")
        self.worker = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        self.main_layout.addWidget(SubtitleLabel("用户信息管理"))

        toolbar_layout = QHBoxLayout()
        self.add_button = PrimaryPushButton("新增用户")
        self.refresh_button = PushButton("刷新数据")
        toolbar_layout.addWidget(self.add_button)
        toolbar_layout.addWidget(self.refresh_button)
        toolbar_layout.addStretch(1)
        self.main_layout.addLayout(toolbar_layout)

        self.table = TableWidget(self)
        self.main_layout.addWidget(self.table)
        
        # --- 应用官方示例样式 ---
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)
        # --- 样式应用结束 ---
        
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        self._define_column_mapping()

        self.refresh_button.clicked.connect(self.populate_table)
        self.add_button.clicked.connect(self.add_user)

    def _define_column_mapping(self):
        """定义表格的列映射关系"""
        self.column_mapping = [
            {'key': 'id', 'header': 'ID', 'width': 60},
            {'key': 'username', 'header': '用户名'},
            {
                'key': 'full_name', 
                'header': '姓名',
                'formatter': lambda full_name: full_name or "N/A"
            },
            {'key': 'email', 'header': '邮箱'},
            {
                'key': 'is_staff', 
                'header': '是否职员',
                'formatter': lambda is_staff: "是" if is_staff else "否"
            },
            {
                'key': 'is_active', 
                'header': '是否激活',
                'formatter': lambda is_active: "是" if is_active else "否"
            },
            {
                'type': 'buttons',
                'header': '操作',
                'width': 170,
                'buttons': [
                    {'text': '编辑', 'style': 'primary', 'callback': self.edit_user},
                    {'text': '删除', 'style': 'default', 'callback': lambda user: self.delete_user(user['id'], user['username'])}
                ]
            }
        ]

    def on_activated(self):
        """
        当界面被激活时调用（例如，通过导航切换到此界面）。
        主要负责自动加载数据，为了UI流畅性会保留旧数据。
        """
        logger.debug("UserInterface 被激活，开始加载数据")
        self._load_data(preserve_old_data=True)

    def on_deactivated(self):
        """
        当界面被切换离开时调用。
        可以在此处进行一些清理工作，如取消正在进行的请求。
        """
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel()
            logger.debug("UserInterface 被切换离开，已取消数据加载请求")

    def _load_data(self, preserve_old_data: bool):
        """
        内部数据加载方法。
        
        Args:
            preserve_old_data (bool): 是否保留旧数据直到新数据加载完成
        """
        try:
            logger.debug("使用数据管理器加载用户数据")
            self.worker = interface_loader.load_for_interface(
                interface=self,
                data_type='users',
                table_widget=self.table,
                force_refresh=not preserve_old_data,
                preserve_old_data=preserve_old_data,
                column_mapping=self.column_mapping
            )
        except Exception as e:
            logger.error(f"加载用户数据时出错: {e}")
            self.on_users_data_error(str(e))

    def populate_table(self):
        """ 手动刷新数据（不保留旧数据） """
        logger.debug("手动刷新用户数据")
        self._load_data(preserve_old_data=False)

    def on_users_data_received(self, response_data):
        """处理接收到的用户数据（现在主要用于日志记录或额外操作）"""
        # 当使用了 column_mapping 自动填充时，表格填充已由 InterfaceDataLoader 自动处理
        # 这里只进行日志记录和任何需要的额外操作
        if hasattr(self, 'column_mapping') and self.column_mapping:
            total = response_data.get('count', 0)
            logger.info(f"UserInterface 成功接收并处理了 {total} 条用户数据。")
            return
        
        # 如果没有使用自动填充，则保留原有的手动处理逻辑
        # （这部分代码在当前实现中已经被移除，因为我们已经完全转向自动填充）
        logger.warning("UserInterface 未使用自动填充配置，但手动填充逻辑已被移除")
    
    def on_users_data_error(self, error_message):
        """处理用户数据加载错误"""
        # InfoBar 错误提示已由 InterfaceDataLoader 自动处理
        logger.error(f"用户数据加载失败: {error_message}")

    def add_user(self):
        dialog = UserEditDialog(self)
        if dialog.exec():
            data, _ = dialog.get_data()
            result = api_client.add_user(data)
            if result:
                InfoBar.success("成功", "新增用户成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "新增用户失败，请检查控制台输出。", duration=3000, parent=self)

    def edit_user(self, user_data):
        dialog = UserEditDialog(self, user_data)
        if dialog.exec():
            data, _ = dialog.get_data()
            result = api_client.update_user(user_data['id'], data)
            if result:
                InfoBar.success("成功", "更新用户成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "更新用户失败，请查看控制台输出。", duration=3000, parent=self)

    def delete_user(self, user_id, username):
        if username == api_client.current_user.get('username'):
            MessageBox("操作无效", "不能删除当前登录的用户。", self.window())
            return
            
        msg_box = MessageBox("确认删除", f"您确定要删除用户 {username} (ID: {user_id}) 吗？", self.window())
        if msg_box.exec():
            if api_client.delete_user(user_id):
                InfoBar.success("成功", "删除用户成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "删除用户失败", duration=3000, parent=self) 