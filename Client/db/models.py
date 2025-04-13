'''
用来存放类
'''


import datetime
import os
from db import db_handler
from conf import settings

class Base:
    def __init__(self,name):
        self.name = name
        self.reg_data = datetime.datetime.now()


    def save(self):
        db_handler.save_data(self)

    @classmethod
    def select(cls,name):
        db_handler.select_data(cls,name)

#管理员类
class Admin(Base):
    def __init__(self,name,pwd):
        super().__init__(name)
        self.pwd = pwd
        self.locked = False

        # 累计付费人次
        self.pay_num = 0
        # 今日营收
        self.today_money = {}
        # 累计营收
        self.all_money = 0

        # 流水
        self.flow = []
        self.save()


