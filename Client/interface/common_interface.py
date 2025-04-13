'''
公共接口
'''
import os
import logging

from conf import settings
from db import models

common_logger = logging.getLogger('common')

def check_admin_is_here():
    admin_dir = os.path.join(
        settings.DB_DIR,'Admin'
    )
    if os.path.isdir(admin_dir) and os.listdir(admin_dir):
        return True,f'管理员已存在'
    return False,f'管理员不存在'
