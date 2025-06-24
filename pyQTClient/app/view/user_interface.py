# coding:utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QAbstractItemView, QCheckBox

from qfluentwidgets import (TableWidget, PushButton, StrongBodyLabel, LineEdit, ComboBox,
                            TextEdit, PrimaryPushButton, MessageBox, InfoBar, MessageBoxBase, 
                            SubtitleLabel, PasswordLineEdit)

from ..api.api_client import api_client
import logging

# 设置logger
logger = logging.getLogger(__name__)

# 安全导入异步API
try:
    from ..api.async_api import async_api
    ASYNC_API_AVAILABLE = True
    logger.debug("异步API模块导入成功")
except ImportError as e:
    logger.warning(f"异步API模块导入失败: {e}")
    async_api = None
    ASYNC_API_AVAILABLE = False


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


class UserInterface(QWidget):
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
        
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "用户名", "姓名", "邮箱", "是否职员", "是否激活", "操作"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # 列宽设置：数据列可调整，操作列固定宽度，倒数第二列拉伸
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)  # 数据列可调整
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)  # 是否激活列拉伸以铺满
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)  # 操作列固定宽度
        # 初始设置操作列宽度（数据加载后会重新计算）
        self.table.horizontalHeader().resizeSection(6, 160)
        self.table.setAlternatingRowColors(True)

        self.refresh_button.clicked.connect(self.populate_table)
        self.add_button.clicked.connect(self.add_user)

        # --- 初始化时不自动加载数据，改为按需加载 ---
        # self.populate_table()  # 注释掉自动加载

    def populate_table(self):
        """ 异步从API获取数据并填充表格 """
        if self.worker and self.worker.isRunning():
            logger.debug("取消之前的用户数据加载")
            self.worker.cancel()

        try:
            if ASYNC_API_AVAILABLE and async_api:
                logger.debug("开始异步加载用户数据")
                self.table.setRowCount(0)
                
                # 异步获取用户数据
                self.worker = async_api.get_users_async(
                    success_callback=self.on_users_data_received,
                    error_callback=self.on_users_data_error
                )
            else:
                logger.warning("异步API不可用，回退到同步加载")
                self.table.setRowCount(0)
                try:
                    response_data = api_client.get_users()
                    self.on_users_data_received(response_data)
                except Exception as e:
                    self.on_users_data_error(str(e))
        except Exception as e:
            logger.error(f"加载用户数据时出错: {e}")
            self.on_users_data_error(str(e))
    
    def on_users_data_received(self, response_data):
        """处理接收到的用户数据"""
        try:
            if not self or not hasattr(self, 'table') or not self.table:
                logger.warning("用户数据回调时界面已销毁")
                return
                
            if response_data is None:
                InfoBar.error("错误", "无法从服务器获取用户数据。", duration=3000, parent=self)
                return

            user_list = response_data.get('results', [])
            logger.debug(f"接收到 {len(user_list)} 个用户数据")
            
            self.table.setRowCount(0)
            for user in user_list:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(user['id'])))
                self.table.setItem(row, 1, QTableWidgetItem(user['username']))
                full_name = user.get('full_name') or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                self.table.setItem(row, 2, QTableWidgetItem(full_name))
                self.table.setItem(row, 3, QTableWidgetItem(user.get('email', '')))

                is_staff_item = QTableWidgetItem("是" if user['is_staff'] else "否")
                is_staff_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 4, is_staff_item)
                
                is_active_item = QTableWidgetItem("是" if user['is_active'] else "否")
                is_active_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 5, is_active_item)
                
                edit_button = PrimaryPushButton("编辑")
                delete_button = PushButton("删除")
                edit_button.clicked.connect(lambda _, u=user: self.edit_user(u))
                delete_button.clicked.connect(lambda _, u_id=user['id'], u_name=user['username']: self.delete_user(u_id, u_name))
                
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(2, 2, 2, 2)
                action_layout.setSpacing(8)
                action_layout.addWidget(edit_button)
                action_layout.addWidget(delete_button)
                self.table.setCellWidget(row, 6, action_widget)
            
            # 根据按钮数量动态调整操作列宽度 (2个按钮)
            button_width = 75  # 每个按钮约75px
            spacing = 8  # 按钮间距
            margin = 6  # 边距
            total_width = 2 * button_width + spacing + 2 * margin
            self.table.horizontalHeader().resizeSection(6, total_width)
            
            InfoBar.success("成功", "数据已刷新", duration=1500, parent=self)
            
        except Exception as e:
            logger.error(f"处理用户数据时出错: {e}")
    
    def on_users_data_error(self, error_message):
        """处理用户数据加载错误"""
        try:
            logger.error(f"用户数据加载失败: {error_message}")
            if self and hasattr(self, 'parent') and self.parent():
                InfoBar.error("加载失败", f"用户数据加载失败: {error_message}", parent=self)
        except Exception as e:
            logger.error(f"处理用户数据错误时出错: {e}")

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

    def __del__(self):
        """ 确保在销毁时取消工作线程 """
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel() 