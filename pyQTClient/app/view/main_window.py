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
        # self.download_button.bor
        
        # 设置按钮大小与标题栏系统按钮一致
        # self.download_button.setFixedSize(16, 16)

        
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
        """界面切换时的处理，每次切换都自动刷新数据"""
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

        # 每次切换都自动刷新数据（移除了只加载一次的限制）
        # 根据界面类型加载对应数据，使用preserve_old_data=True避免用户看到空白界面
        try:
            if interface_name == "DashboardInterface":
                # 看板界面 - 定时器会自动刷新数据，这里不需要额外操作
                pass

            elif interface_name == "ProcessingTaskInterface":
                # 加工任务界面 - 使用数据管理器自动刷新数据
                try:
                    from ..api.data_manager import interface_loader
                    interface_loader.load_for_interface(
                        interface=current_widget.task_list_widget,
                        data_type='processing_tasks',
                        table_widget=current_widget.task_list_widget.table,
                        force_refresh=True,
                        preserve_old_data=True  # 保留旧数据直到新数据加载完成
                    )
                except ImportError:
                    # 回退到原始方法
                    current_widget.task_list_widget.populate_table()

            elif interface_name == "TaskGroupInterface":
                # 任务分组界面 - 自动刷新数据，使用preserve_old_data避免空白
                if hasattr(current_widget, 'populate_group_tree'):
                    current_widget.populate_group_tree(preserve_old_data=True)

            elif interface_name == "ToolInterface":
                # 刀具管理界面 - 使用数据管理器自动刷新数据
                try:
                    from ..api.data_manager import interface_loader
                    interface_loader.load_for_interface(
                        interface=current_widget,
                        data_type='tools',
                        table_widget=current_widget.table,
                        force_refresh=True,
                        preserve_old_data=True  # 保留旧数据直到新数据加载完成
                    )
                except ImportError:
                    # 回退到原始方法
                    if hasattr(current_widget, 'populate_table'):
                        current_widget.populate_table()

            elif interface_name == "CompositeMaterialInterface":
                # 构件管理界面 - 使用数据管理器自动刷新数据
                try:
                    from ..api.data_manager import interface_loader
                    interface_loader.load_for_interface(
                        interface=current_widget,
                        data_type='composite_materials',
                        table_widget=current_widget.table,
                        force_refresh=True,
                        preserve_old_data=True  # 保留旧数据直到新数据加载完成
                    )
                except ImportError:
                    # 回退到原始方法
                    if hasattr(current_widget, 'populate_table'):
                        current_widget.populate_table()

            elif interface_name == "SensorDataInterface":
                # 传感器数据界面 - 使用数据管理器自动刷新数据
                try:
                    from ..api.data_manager import interface_loader
                    interface_loader.load_for_interface(
                        interface=current_widget,
                        data_type='sensor_data',
                        table_widget=current_widget.table,
                        force_refresh=True,
                        preserve_old_data=True  # 保留旧数据直到新数据加载完成
                    )
                except ImportError:
                    # 回退到原始方法
                    if hasattr(current_widget, 'populate_table'):
                        current_widget.populate_table()

            elif interface_name == "UserInterface":
                # 用户管理界面 - 使用数据管理器自动刷新数据
                try:
                    from ..api.data_manager import interface_loader
                    interface_loader.load_for_interface(
                        interface=current_widget,
                        data_type='users',
                        table_widget=current_widget.table,
                        force_refresh=True,
                        preserve_old_data=True  # 保留旧数据直到新数据加载完成
                    )
                except ImportError:
                    # 回退到原始方法
                    if hasattr(current_widget, 'populate_table'):
                        current_widget.populate_table()

            elif interface_name == "SettingInterface":
                # 设置界面 - 不需要刷新数据
                pass

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"自动刷新界面数据时出错 ({interface_name}): {e}") 