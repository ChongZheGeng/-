# coding: utf-8
from enum import Enum
from qfluentwidgets import StyleSheetBase, Theme, qconfig


class StyleSheet(StyleSheetBase, Enum):
    """ 样式表管理 """

    NAV_INTERFACE = "nav_interface"
    MAIN_WINDOW = "main_window"

    def path(self, theme=Theme.AUTO):
        """获取样式表路径"""
        theme = qconfig.theme if theme == Theme.AUTO else theme
        # 由于我们没有资源文件，直接返回内联样式
        return self._get_inline_style(theme)
    
    def _get_inline_style(self, theme):
        """获取内联样式"""
        if self == StyleSheet.NAV_INTERFACE:
            return self._get_nav_interface_style(theme)
        elif self == StyleSheet.MAIN_WINDOW:
            return self._get_main_window_style(theme)
        return ""
    
    def _get_nav_interface_style(self, theme):
        """获取导航界面样式"""
        if theme == Theme.DARK:
            return """
            NavInterface {
                background-color: transparent;
                background: transparent;
                border: none;
            }
            
            NavInterface #view {
                background-color: transparent;
                background: transparent;
                border: none;
            }
            
            NavInterface QScrollArea {
                border: none;
                background-color: transparent;
                background: transparent;
            }
            
            NavInterface QWidget {
                background-color: transparent;
                background: transparent;
            }
            
            NavInterface QScrollBar:vertical {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 6px;
                width: 12px;
                margin: 0px;
            }
            
            NavInterface QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                min-height: 20px;
            }
            
            NavInterface QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.4);
            }
            
            NavInterface QScrollBar::add-line:vertical, 
            NavInterface QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            """
        else:  # Light theme
            return """
            NavInterface {
                background-color: transparent;
                background: transparent;
                border: none;
            }
            
            NavInterface #view {
                background-color: transparent;
                background: transparent;
                border: none;
            }
            
            NavInterface QScrollArea {
                border: none;
                background-color: transparent;
                background: transparent;
            }
            
            NavInterface QWidget {
                background-color: transparent;
                background: transparent;
            }
            
            NavInterface QScrollBar:vertical {
                background-color: rgba(0, 0, 0, 0.05);
                border: none;
                border-radius: 6px;
                width: 12px;
                margin: 0px;
            }
            
            NavInterface QScrollBar::handle:vertical {
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 6px;
                min-height: 20px;
            }
            
            NavInterface QScrollBar::handle:vertical:hover {
                background-color: rgba(0, 0, 0, 0.3);
            }
            
            NavInterface QScrollBar::add-line:vertical, 
            NavInterface QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            """
    
    def _get_main_window_style(self, theme):
        """获取主窗口样式"""
        return """
        MainWindow QStackedWidget {
            background-color: transparent;
            border: none;
        }
        
        MainWindow > QWidget {
            background-color: transparent;
        }
        """
    
    def apply(self, widget):
        """应用样式到组件"""
        style = self._get_inline_style(qconfig.theme)
        if style:
            widget.setStyleSheet(style)