from PyQt5.QtCore import QThread, pyqtSignal
import logging

# 设置logger
logger = logging.getLogger(__name__)

# 延迟导入避免循环导入问题
def get_api_client():
    try:
        from .api_client import api_client
        return api_client
    except ImportError as e:
        logger.error(f"无法导入api_client: {e}")
        return None


class AsyncApiWorker(QThread):
    """异步API调用工作线程"""
    finished = pyqtSignal(object)  # 返回结果
    error = pyqtSignal(str)  # 返回错误信息
    
    def __init__(self, api_method, *args, **kwargs):
        super().__init__()
        self.api_method = api_method
        self.args = args
        self.kwargs = kwargs
        self._is_cancelled = False
    
    def run(self):
        """在后台线程中执行API调用"""
        try:
            if self._is_cancelled:
                logger.debug(f"异步API调用已取消: {self.api_method.__name__}")
                return
                
            logger.debug(f"开始执行异步API调用: {self.api_method.__name__}")
            # 执行API方法
            result = self.api_method(*self.args, **self.kwargs)
            
            if self._is_cancelled:
                logger.debug(f"异步API调用在完成后被取消: {self.api_method.__name__}")
                return
                
            logger.debug(f"异步API调用成功: {self.api_method.__name__}")
            self.finished.emit(result)
        except Exception as e:
            if self._is_cancelled:
                logger.debug(f"异步API调用在异常时已取消: {self.api_method.__name__}")
                return
                
            import traceback
            error_msg = f"异步API调用失败 {self.api_method.__name__}: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self.error.emit(str(e))
    
    def cancel(self):
        """取消异步调用"""
        self._is_cancelled = True
        logger.debug(f"取消异步API调用: {getattr(self.api_method, '__name__', 'unknown')}")


class AsyncApiHelper:
    """异步API调用助手"""
    
    @staticmethod
    def call_async(api_method, success_callback=None, error_callback=None, *args, **kwargs):
        """
        异步调用API方法
        
        Args:
            api_method: 要调用的API方法
            success_callback: 成功回调函数
            error_callback: 错误回调函数
            *args, **kwargs: API方法的参数
        
        Returns:
            AsyncApiWorker: 工作线程对象
        """
        worker = AsyncApiWorker(api_method, *args, **kwargs)
        
        if success_callback:
            worker.finished.connect(success_callback)
        
        if error_callback:
            worker.error.connect(error_callback)
        
        worker.start()
        return worker
    
    @staticmethod
    def get_sensor_data_async(success_callback=None, error_callback=None, params=None):
        """异步获取传感器数据"""
        api_client = get_api_client()
        if not api_client:
            if error_callback:
                error_callback("API客户端不可用")
            return None
        return AsyncApiHelper.call_async(
            api_client.get_sensor_data,
            success_callback,
            error_callback,
            params=params
        )
    
    @staticmethod
    def get_users_async(success_callback=None, error_callback=None):
        """异步获取用户数据"""
        api_client = get_api_client()
        if not api_client:
            if error_callback:
                error_callback("API客户端不可用")
            return None
        return AsyncApiHelper.call_async(
            api_client.get_users,
            success_callback,
            error_callback
        )
    
    @staticmethod
    def get_processing_tasks_async(success_callback=None, error_callback=None, params=None):
        """异步获取加工任务数据"""
        api_client = get_api_client()
        if not api_client:
            if error_callback:
                error_callback("API客户端不可用")
            return None
        return AsyncApiHelper.call_async(
            api_client.get_processing_tasks,
            success_callback,
            error_callback,
            params=params
        )
    
    @staticmethod
    def get_tools_async(success_callback=None, error_callback=None):
        """异步获取刀具数据"""
        api_client = get_api_client()
        if not api_client:
            if error_callback:
                error_callback("API客户端不可用")
            return None
        return AsyncApiHelper.call_async(
            api_client.get_tools,
            success_callback,
            error_callback
        )
    
    @staticmethod
    def get_composite_materials_async(success_callback=None, error_callback=None):
        """异步获取构件数据"""
        api_client = get_api_client()
        if not api_client:
            if error_callback:
                error_callback("API客户端不可用")
            return None
        return AsyncApiHelper.call_async(
            api_client.get_composite_materials,
            success_callback,
            error_callback
        )
    
    @staticmethod
    def get_task_groups_async(success_callback=None, error_callback=None):
        """异步获取任务分组数据"""
        api_client = get_api_client()
        if not api_client:
            if error_callback:
                error_callback("API客户端不可用")
            return None
        return AsyncApiHelper.call_async(
            api_client.get_task_groups,
            success_callback,
            error_callback
        )


# 创建全局异步API助手实例
async_api = AsyncApiHelper() 