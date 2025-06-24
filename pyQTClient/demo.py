# coding:utf-8
import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentTranslator, qconfig

from app.common.config import cfg
from app.view.login_window import LoginWindow
from app.view.main_window import MainWindow
    

class ApplicationManager:
    """应用管理器，用于控制窗口流程"""
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.setup_app_style()
        self.setup_exception_handling()

        self.login_window = LoginWindow()
        self.login_window.loginSuccess.connect(self.show_main_window)
        
        self.main_window = None

    def setup_app_style(self):
        """设置应用的基础样式和国际化"""
        # enable dpi scale
        if cfg.get(cfg.dpiScale) == "Auto":
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        else:
            os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
            os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))

        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        self.app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

        # internationalization
        locale = cfg.get(cfg.language).value
        translator = FluentTranslator(locale)
        self.app.installTranslator(translator)
    
    def setup_exception_handling(self):
        """设置全局异常处理"""
        import traceback
        import logging
        
        # 设置日志记录
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('app_debug.log', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
        # 设置Qt异常处理
        def qt_exception_hook(exctype, value, tb):
            error_msg = ''.join(traceback.format_exception(exctype, value, tb))
            self.logger.error(f"未捕获的异常:\n{error_msg}")
            self.logger.critical(f"应用程序异常:\n{error_msg}")
            
            # 显示错误对话框
            try:
                from qfluentwidgets import MessageBox
                if hasattr(self, 'main_window') and self.main_window:
                    parent = self.main_window
                elif hasattr(self, 'login_window') and self.login_window:
                    parent = self.login_window
                else:
                    parent = None
                    
                msg = MessageBox(
                    "程序错误", 
                    f"程序遇到未处理的错误:\n{str(value)}\n\n详细信息已保存到 app_debug.log", 
                    parent
                )
                msg.exec()
            except:
                pass  # 如果连错误对话框都显示不了，就忽略
        
        # 设置全局异常钩子
        sys.excepthook = qt_exception_hook
        
        # 记录应用启动
        self.logger.info("应用程序启动")

    def run(self):
        """启动应用"""
        self.login_window.show()
        sys.exit(self.app.exec_())

    def show_main_window(self):
        """显示主窗口"""
        self.main_window = MainWindow()
        # Connect the logout signal after showing the main window
        self.main_window.setting_interface.logoutSignal.connect(self.show_login_window)
        
        # 看板界面会在初始化时自动加载数据，标记为已加载
        self.main_window.loaded_interfaces.add("DashboardInterface")
        
        self.main_window.show()

        if self.login_window:
            self.login_window.close()

    def show_login_window(self):
        """显示登录窗口"""
        # 在显示新窗口前先关闭旧的，避免闪烁
        if self.main_window:
            self.main_window.is_logout = True # 标记为登出
            self.main_window.close()

        self.login_window = LoginWindow()
        self.login_window.loginSuccess.connect(self.show_main_window)
        self.login_window.show()


# --- 主程序入口 ---
if __name__ == '__main__':
    try:
        # --- 应用初始化 ---
        # 启用高分屏缩放
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

        app = QApplication(sys.argv)
        app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

        # --- 国际化 ---
        # translator = FluentTranslator(locals())
        # app.installTranslator(translator)

        # --- 应用管理器 ---
        manager = ApplicationManager()
        manager.run()

        sys.exit(app.exec_())
        
    except Exception as e:
        import traceback
        import logging
        
        error_msg = f"应用程序启动失败: {str(e)}\n{traceback.format_exc()}"
        
        # 设置基本日志
        logging.basicConfig(level=logging.ERROR)
        logger = logging.getLogger(__name__)
        logger.critical(error_msg)
        
        # 尝试写入错误日志
        try:
            with open('startup_error.log', 'w', encoding='utf-8') as f:
                f.write(error_msg)
            logger.info("错误信息已保存到 startup_error.log")
        except:
            pass
        
        sys.exit(1)