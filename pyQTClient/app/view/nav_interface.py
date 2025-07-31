from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget
from qfluentwidgets import ScrollArea, qconfig
from ..common.style_sheet import StyleSheet


class NavInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.view = QWidget(self)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        
        # 设置对象名称
        self.view.setObjectName('view')
        
        # 确保背景透明
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.view.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # 应用样式
        self._apply_style()
        
        # 监听主题变化
        qconfig.themeChanged.connect(self._apply_style)

    def _apply_style(self):
        """应用样式，支持主题切换"""
        StyleSheet.NAV_INTERFACE.apply(self)
    
    def on_activated(self):
        pass

    def on_deactivated(self):
        pass