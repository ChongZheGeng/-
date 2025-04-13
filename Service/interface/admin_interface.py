'''
管理员接口
'''


import os
from  conf import settings
from  db import db_handler,models

def admin_register_interface(name,pwd):

    #1查询学生是否存在
    stu_path = os.path.join(
        settings.DB_DIR,'Admin', name
    )

    if os.path.exists(stu_path):
        return False,f'{name} 用户已经存在'
    obj = models.Admin(name,pwd)
    return True,f'{name} 注册成功'