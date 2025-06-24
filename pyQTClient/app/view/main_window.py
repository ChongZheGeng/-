# coding:utf-8
from PyQt5.QtCore import QTimer
from qfluentwidgets import (FluentWindow, NavigationItemPosition,
                            FluentIcon as FIF, isDarkTheme, SystemThemeListener)

# 使用相对路径导入上级包的模块
from ..api.api_client import api_client
from ..common.config import cfg
from ..common.signal_bus import signalBus

# 使用相对路径导入同级包的模块
from .dashboard_interface import DashboardInterface
from .file_transfer_manager import FileTransferButton
from .sensor_data_interface import SensorDataInterface
from .setting_interface import SettingInterface
from .task_group_interface import TaskGroupInterface
from .processing_task_interface import ProcessingTaskInterface
from .composite_material_interface import CompositeMaterialInterface
from .tool_interface import ToolInterface
from .user_interface import UserInterface


class MainWindow(FluentWindow):

    def __init__(self):
        super().__init__()
        self.is_logout = False
        self.loaded_interfaces = set()  # 记录已加载数据的界面
        self.initWindow()

        # create sub interface
        self.dashboard_interface = DashboardInterface(self)
        self.tool_interface = ToolInterface(self)
        self.user_interface = UserInterface(self)
        self.composite_material_interface = CompositeMaterialInterface(self)
        self.processing_task_interface = ProcessingTaskInterface(self)
        self.task_group_interface = TaskGroupInterface(self)
        self.sensor_data_interface = SensorDataInterface(self)
        self.setting_interface = SettingInterface(self)

        # 根据用户权限决定是否添加用户管理界面
        if api_client.current_user and api_client.current_user.get('is_staff'):
            self.user_interface = UserInterface(self)
        else:
            self.user_interface = None

        # 添加文件传输按钮到标题栏
        self.download_button = FileTransferButton(self)
        
        # 设置按钮大小与标题栏系统按钮一致
        self.download_button.setFixedSize(46, 32)

        
        # 插入到标题栏右侧，在系统按钮之前
        self.titleBar.hBoxLayout.insertWidget(
            self.titleBar.hBoxLayout.count() - 1,
            self.download_button
        )

        # connect signal to slot
        signalBus.micaEnableChanged.connect(self.setMicaEffectEnabled)
        self.setting_interface.logoutSignal.connect(self.logout)

        # add items to navigation interface
        self.initNavigation()

        # 连接导航切换信号，实现按需加载
        self.stackedWidget.currentChanged.connect(self.on_interface_changed)

    def initNavigation(self):
        # --- 首页看板 ---
        self.addSubInterface(self.dashboard_interface, FIF.HOME, "系统概览",position=NavigationItemPosition.SCROLL)
        self.navigationInterface.addSeparator(35)

        # --- 主导航 ---
        self.addSubInterface(self.processing_task_interface, FIF.EDIT, "加工任务",position=NavigationItemPosition.SCROLL)
        self.addSubInterface(self.task_group_interface, FIF.TAG, "任务分组",position=NavigationItemPosition.SCROLL)
        self.navigationInterface.addSeparator(35)

        # --- 二级导航 ---
        self.addSubInterface(
            interface=self.tool_interface,
            icon=FIF.DEVELOPER_TOOLS,
            text='刀具管理',
            position=NavigationItemPosition.SCROLL
        )
        self.addSubInterface(
            interface=self.composite_material_interface,
            icon=FIF.CONSTRACT,
            text='构件管理',
            position=NavigationItemPosition.SCROLL
        )

        # add sensor data interface
        self.addSubInterface(self.sensor_data_interface, FIF.SPEED_HIGH, "传感器数据管理")

        if self.user_interface:
            self.addSubInterface(
                interface=self.user_interface,
                icon=FIF.PEOPLE,
                text='用户管理',
                position=NavigationItemPosition.BOTTOM
            )

        # --- 设置页面 ---
        self.addSubInterface(
            interface=self.setting_interface,
            icon=FIF.SETTING,
            text='设置',
            position=NavigationItemPosition.BOTTOM
        )

        # 设置首页为默认页面
        self.navigationInterface.setCurrentItem(self.dashboard_interface.objectName())

        self.navigationInterface.addSeparator()

        # add setting interface
        self.stackedWidget.addWidget(self.dashboard_interface)
        if self.user_interface:
            self.stackedWidget.addWidget(self.user_interface)
        self.stackedWidget.addWidget(self.composite_material_interface)
        self.stackedWidget.addWidget(self.processing_task_interface)
        self.stackedWidget.addWidget(self.task_group_interface)
        self.stackedWidget.addWidget(self.sensor_data_interface)
        self.stackedWidget.addWidget(self.setting_interface)
        self.stackedWidget.addWidget(self.tool_interface)

        # 确保看板界面显示在最前面
        self.stackedWidget.setCurrentWidget(self.dashboard_interface)

        # 启动看板界面的定时器（因为默认显示看板）
        if hasattr(self.dashboard_interface, 'start_refresh_timer'):
            self.dashboard_interface.start_refresh_timer()

    def initWindow(self):
        self.resize(1200, 600)
        self.setMinimumWidth(760)
        self.setWindowTitle("复合材料加工数据管理")
        self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        # create system theme listener
        self.themeListener = SystemThemeListener(self)
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

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止看板界面的定时器
        if hasattr(self.dashboard_interface, 'stop_refresh_timer'):
            self.dashboard_interface.stop_refresh_timer()

        super().closeEvent(event)

    def on_interface_changed(self, index):
        """界面切换时的处理，实现按需加载"""
        current_widget = self.stackedWidget.widget(index)
        if current_widget is None:
            return

        # 获取界面的对象名称
        interface_name = current_widget.objectName()

        # 控制看板界面的定时器
        if interface_name == "DashboardInterface":
            # 切换到看板界面时启动定时器
            if hasattr(current_widget, 'start_refresh_timer'):
                current_widget.start_refresh_timer()
        else:
            # 切换到其他界面时停止看板的定时器
            if hasattr(self.dashboard_interface, 'stop_refresh_timer'):
                self.dashboard_interface.stop_refresh_timer()

        # 如果该界面已经加载过数据，则不重复加载
        if interface_name in self.loaded_interfaces:
            return

        # 根据界面类型加载对应数据
        try:
            if interface_name == "DashboardInterface":
                # 看板界面 - 已在初始化时自动加载数据
                self.loaded_interfaces.add(interface_name)

            elif interface_name == "ProcessingTaskInterface":
                # 加工任务界面
                current_widget.task_list_widget.populate_table()
                self.loaded_interfaces.add(interface_name)

            elif interface_name == "TaskGroupInterface":
                # 任务分组界面
                if hasattr(current_widget, 'populate_group_tree'):
                    current_widget.populate_group_tree()
                self.loaded_interfaces.add(interface_name)

            elif interface_name == "ToolInterface":
                # 刀具管理界面
                if hasattr(current_widget, 'populate_table'):
                    current_widget.populate_table()
                self.loaded_interfaces.add(interface_name)

            elif interface_name == "CompositeMaterialInterface":
                # 构件管理界面
                if hasattr(current_widget, 'populate_table'):
                    current_widget.populate_table()
                self.loaded_interfaces.add(interface_name)

            elif interface_name == "SensorDataInterface":
                # 传感器数据界面
                if hasattr(current_widget, 'populate_table'):
                    current_widget.populate_table()
                self.loaded_interfaces.add(interface_name)

            elif interface_name == "UserInterface":
                # 用户管理界面
                if hasattr(current_widget, 'populate_table'):
                    current_widget.populate_table()
                self.loaded_interfaces.add(interface_name)

            elif interface_name == "SettingInterface":
                # 设置界面 - 已在初始化时加载用户信息
                self.loaded_interfaces.add(interface_name)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"加载界面数据时出错 ({interface_name}): {e}") 