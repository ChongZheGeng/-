'''
数据处理层
'''
import os
import pickle
from conf import settings

#查询数据
def select_data(cls,name):
    obj_path = os.path.join(
        settings.DB_DIR, cls.__name__, name
    )
    if not os.path.exists(obj_path):
        return
    with open(obj_path,'rb') as f:
        obj = pickle.load(f)
        return obj

def save_data(obj):
    class_name = obj.__class__.__name__
    obj_dir = os.path.join(
        settings.DB_DIR,class_name
    )
    if not os.path.isdir(obj_dir):
        os.makedirs(obj_dir)
    obj_path = os.path.join(
        obj_dir,obj.name
    )

    with open(obj_path,'wb') as f:
        pickle.dump(obj,f)

