# coding:utf-8
import logging

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QAbstractItemView
from qfluentwidgets import (TableWidget, PushButton, PrimaryPushButton, MessageBox, InfoBar, SubtitleLabel)

from pyQTClient.app.view.nav_interface import NavInterface
from .components.user_component import UserEditDialog
from ..api.api_client import api_client
from ..api.data_manager import interface_loader

# 设置logger
logger = logging.getLogger(__name__)


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
                    {'text': '删除', 'style': 'default',
                     'callback': lambda user: self.delete_user(user['id'], user['username'])}
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
