'''
用户视图层
'''
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget,QApplication,QMessageBox

from interface import admin_interface,common_interface
from lib import common
from ui.login import Ui_Form as LoginUiMixin
from conf import settings

import logging
from conf import settings

test_logger = logging.getLogger('视图层')

class LoginWindow(LoginUiMixin,QWidget):
    '''
    LoginUiMixin 给窗口对象添加控件功能
    '''
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.admin_is_here = None
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint) # 隐藏边框
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # 背景透明


    def login(self):
        test_logger.debug('登录')
        username = self.lineEdit.text()
        password = self.lineEdit_2.text()
        print(username,password)

    def register(self):
        test_logger.debug('注册')
        name = self.lineEdit_3.text().strip()
        password = self.lineEdit_4.text().strip()
        re_password = self.lineEdit_5.text().strip()

        if password !=re_password:
            QMessageBox.warning(self,'警告','密码不一致')
            return
        # 密码加密
        pwd = common.pwd_to_sha256(password)

        #调用注册接口进行注册

        flag,msg = admin_interface.admin_register_interface(name,pwd)
        QMessageBox.about(self,'提示',msg)

        #注册失败
        if not flag:
            return

        #注册成功 跳转到登录界面
        self.open_login_page()
        self.lineEdit_3.setText('')
        self.lineEdit_4.setText('')
        self.lineEdit_5.setText('')
        self.lineEdit.setText(name)
        self.lineEdit_2.setFocus()



    def open_login_page(self):
        test_logger.debug('打开登录界面')
        self.stackedWidget.setCurrentIndex(0)


    def open_register_page(self):
        test_logger.debug('打开注册界面')
        self.stackedWidget.setCurrentIndex(1)
        #系统只允许有一个管理员 判断是否有管理员
        flag,msg = common_interface.check_admin_is_here()
        if flag:
            self.label_2.setText('学员注册')
            self.admin_is_here = True



def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


def run():
    app = QApplication(sys.argv)

    login_window  = LoginWindow()
    sys.excepthook = except_hook  # 重新定义异常挂钩sys.excepthook
    login_window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    run()