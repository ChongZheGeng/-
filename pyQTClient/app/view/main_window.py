# coding:utf-8
import logging

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget
from qfluentwidgets import (FluentWindow, NavigationItemPosition,
                            FluentIcon as FIF, isDarkTheme, SystemThemeListener)

logger = logging.getLogger(__name__)

# 使用相对路径导入上级包的模块
from ..api.api_client import api_client
from ..common.config import cfg
from ..common.signal_bus import signalBus
from .nav_interface import NavInterface

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
        # 添加一个属性来跟踪前一个激活的界面
        self.previous_interface = None
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


    def initNavigation(self):
        # --- 首页看板 ---
        self.addSubInterface(self.dashboard_interface, FIF.HOME, "系统概览", position=NavigationItemPosition.TOP)
        # self.navigationInterface.addSeparator(35)

        # --- 主导航 ---
        self.addSubInterface(self.processing_task_interface, FIF.CALENDAR, "加工任务",
                             position=NavigationItemPosition.SCROLL)
        self.addSubInterface(self.task_group_interface, FIF.TAG, "任务分组", position=NavigationItemPosition.SCROLL)
        # self.navigationInterface.addSeparator(35)

        # --- 二级导航 ---
        self.addSubInterface(
            interface=self.tool_interface,
            icon=FIF.DEVELOPER_TOOLS,
            text='刀具管理',
            position=NavigationItemPosition.SCROLL
        )
        self.addSubInterface(
            interface=self.composite_material_interface,
            icon=FIF.TILES,
            text='构件管理',
            position=NavigationItemPosition.SCROLL
        )

        # add sensor data interface
        self.addSubInterface(self.sensor_data_interface, FIF.BOOK_SHELF, "传感器数据管理",
                             position=NavigationItemPosition.SCROLL)

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
        # self.navigationInterface.setCurrentItem(self.dashboard_interface.objectName())
        self.switchTo(self.dashboard_interface)

        # enable acrylic effect
        self.navigationInterface.setAcrylicEnabled(True)

        # 启动看板界面的定时器（因为默认显示看板）
        if hasattr(self.dashboard_interface, 'start_refresh_timer'):
            self.dashboard_interface.start_refresh_timer()

    def initWindow(self):
        self.resize(1400, 700)
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)
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

    def switchTo(self, interface: QWidget):
        super().switchTo(interface)
        current_widget = self.stackedWidget.currentWidget()

        if current_widget is None:
            logger.warning(f"on_interface_changed: current_widget is None, name={current_widget.objectName()}")
            return

        # 获取界面的对象名称
        interface_name = current_widget.objectName()
        logger.debug(f"界面切换到: {interface_name} (name={current_widget.objectName()})")

        # 控制看板界面的定时器
        if interface_name == "DashboardInterface":
            # 切换到看板界面时启动定时器
            if hasattr(current_widget, 'start_refresh_timer'):
                current_widget.start_refresh_timer()
        else:
            # 切换到其他界面时停止看板的定时器
            if hasattr(self.dashboard_interface, 'stop_refresh_timer'):
                self.dashboard_interface.stop_refresh_timer()

        # 处理前一个界面的清理工作
        if self.previous_interface and isinstance(self.previous_interface, NavInterface):
            logger.debug(f"调用前一个界面的 on_deactivated: {self.previous_interface.objectName()}")
            self.previous_interface.on_deactivated()

        # 处理当前界面的激活工作
        logger.debug(f"检查当前界面是否为 NavInterface: {isinstance(current_widget, NavInterface)}")
        if isinstance(current_widget, NavInterface):
            # 调用标准的激活方法
            logger.debug(f"准备调用 {interface_name} 的 on_activated 方法")
            try:
                logger.debug(f"正在调用 {interface_name}.on_activated()")
                current_widget.on_activated()
                logger.debug(f"成功调用 {interface_name}.on_activated()")
            except Exception as e:
                logger.error(f"调用 {current_widget.objectName()} 的 on_activated 时出错: {e}")

        else:
            logger.warning(f"{interface_name} 不是 NavInterface 的实例")

        # 更新前一个界面的引用
        self.previous_interface = current_widget
        logger.debug(f"已更新 previous_interface 为: {interface_name}")

