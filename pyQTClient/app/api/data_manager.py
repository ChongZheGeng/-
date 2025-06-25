import time
import logging
from PyQt5.QtCore import QObject, pyqtSignal
from .async_api import AsyncApiWorker

logger = logging.getLogger(__name__)


class DataManager(QObject):
    """统一的数据管理器，负责API调用、缓存和请求去重"""
    
    # 数据更新信号
    data_updated = pyqtSignal(str, object)  # (data_type, data)
    data_error = pyqtSignal(str, str)       # (data_type, error_message)
    
    def __init__(self):
        super().__init__()
        self.cache = {}
        self.active_requests = {}
        self.cache_timeout = 30  # 缓存30秒
        
        # 数据类型到API方法的映射
        self.api_methods = {
            'users': 'get_users',
            'tools': 'get_tools', 
            'sensor_data': 'get_sensor_data',
            'processing_tasks': 'get_processing_tasks',
            'composite_materials': 'get_composite_materials',
            'task_groups': 'get_task_groups'
        }
        
        # 支持params参数的方法
        self.methods_with_params = {
            'sensor_data', 'processing_tasks'
        }
    
    def get_data_async(self, data_type, success_callback=None, error_callback=None, 
                      params=None, force_refresh=False):
        """
        统一的异步数据获取方法
        
        Args:
            data_type: 数据类型 ('users', 'tools', 'sensor_data', etc.)
            success_callback: 成功回调函数
            error_callback: 错误回调函数
            params: API参数
            force_refresh: 是否强制刷新缓存
            
        Returns:
            AsyncApiWorker or None
        """
        try:
            # 检查缓存
            if not force_refresh and self._is_cache_valid(data_type):
                logger.debug(f"使用缓存数据: {data_type}")
                if success_callback:
                    success_callback(self.cache[data_type]['data'])
                self.data_updated.emit(data_type, self.cache[data_type]['data'])
                return None
            
            # 避免重复请求
            if data_type in self.active_requests:
                logger.debug(f"合并到现有请求: {data_type}")
                # 将回调添加到现有请求
                if success_callback or error_callback:
                    self.active_requests[data_type]['callbacks'].append((success_callback, error_callback))
                return self.active_requests[data_type]['worker']
            
            # 获取API客户端和方法
            api_method = self._get_api_method(data_type)
            if not api_method:
                error_msg = f"未知的数据类型: {data_type}"
                logger.error(error_msg)
                if error_callback:
                    error_callback(error_msg)
                self.data_error.emit(data_type, error_msg)
                return None
            
            # 创建新的异步请求
            logger.debug(f"创建新的异步请求: {data_type}")
            # 只对支持params的方法传递params参数
            if data_type in self.methods_with_params and params is not None:
                worker = AsyncApiWorker(api_method, params=params)
            elif data_type in self.methods_with_params:
                # 对于支持params的方法，即使params为None也要传递
                worker = AsyncApiWorker(api_method, params=None)
            else:
                # 对于不支持params的方法，不传递params参数
                worker = AsyncApiWorker(api_method)
            
            # 包装回调以处理缓存和多个回调
            def wrapped_success(data):
                self._update_cache(data_type, data)
                callbacks = self.active_requests.pop(data_type, {}).get('callbacks', [])
                if success_callback:
                    callbacks.append((success_callback, error_callback))
                
                # 触发所有回调
                for success_cb, _ in callbacks:
                    if success_cb:
                        try:
                            success_cb(data)
                        except Exception as e:
                            logger.error(f"回调执行失败: {e}")
                
                # 发送全局信号（只有在没有特定回调时才发送，避免重复）
                if not callbacks:
                    self.data_updated.emit(data_type, data)
            
            def wrapped_error(error):
                callbacks = self.active_requests.pop(data_type, {}).get('callbacks', [])
                if error_callback:
                    callbacks.append((success_callback, error_callback))
                
                # 触发所有错误回调
                for _, error_cb in callbacks:
                    if error_cb:
                        try:
                            error_cb(error)
                        except Exception as e:
                            logger.error(f"错误回调执行失败: {e}")
                
                # 发送全局错误信号（只有在没有特定回调时才发送，避免重复）
                if not callbacks:
                    self.data_error.emit(data_type, error)
            
            worker.finished.connect(wrapped_success)
            worker.error.connect(wrapped_error)
            
            # 记录活跃请求
            self.active_requests[data_type] = {
                'worker': worker,
                'callbacks': [(success_callback, error_callback)] if (success_callback or error_callback) else []
            }
            
            worker.start()
            return worker
            
        except Exception as e:
            error_msg = f"创建异步请求失败: {str(e)}"
            logger.error(error_msg)
            if error_callback:
                error_callback(error_msg)
            self.data_error.emit(data_type, error_msg)
            return None
    
    def cancel_request(self, data_type):
        """取消指定类型的数据请求"""
        if data_type in self.active_requests:
            worker = self.active_requests[data_type]['worker']
            if worker and worker.isRunning():
                worker.cancel()
                logger.debug(f"已取消请求: {data_type}")
            del self.active_requests[data_type]
    
    def cancel_all_requests(self):
        """取消所有活跃请求"""
        for data_type in list(self.active_requests.keys()):
            self.cancel_request(data_type)
        logger.debug("已取消所有活跃请求")
    
    def clear_cache(self, data_type=None):
        """清除缓存"""
        if data_type:
            if data_type in self.cache:
                del self.cache[data_type]
                logger.debug(f"已清除缓存: {data_type}")
        else:
            self.cache.clear()
            logger.debug("已清除所有缓存")
    
    def get_cached_data(self, data_type):
        """获取缓存的数据"""
        if self._is_cache_valid(data_type):
            return self.cache[data_type]['data']
        return None
    
    def _is_cache_valid(self, data_type):
        """检查缓存是否有效"""
        if data_type not in self.cache:
            return False
        
        cache_time = self.cache[data_type]['timestamp']
        return (time.time() - cache_time) < self.cache_timeout
    
    def _update_cache(self, data_type, data):
        """更新缓存"""
        self.cache[data_type] = {
            'data': data,
            'timestamp': time.time()
        }
        logger.debug(f"已更新缓存: {data_type}")
    
    def _get_api_method(self, data_type):
        """获取对应的API方法"""
        try:
            from .api_client import api_client
            method_name = self.api_methods.get(data_type)
            if method_name and hasattr(api_client, method_name):
                return getattr(api_client, method_name)
            return None
        except ImportError as e:
            logger.error(f"无法导入api_client: {e}")
            return None


class InterfaceDataLoader:
    """界面数据加载助手"""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
    
    def load_for_interface(self, interface, data_type, table_widget=None, force_refresh=False, preserve_old_data=False):
        """
        为界面自动加载数据的简化方法
        
        Args:
            interface: 目标界面对象
            data_type: 数据类型
            table_widget: 表格控件（可选，会自动清空）
            force_refresh: 是否强制刷新
            preserve_old_data: 是否保留旧数据直到新数据加载完成
        """
        # 只有在不保留旧数据时才立即清空表格
        if table_widget and not preserve_old_data:
            table_widget.setRowCount(0)
        
        # 取消之前的请求
        if hasattr(interface, 'worker') and interface.worker:
            interface.worker.cancel()
        
        # 定义成功回调
        def success_callback(data):
            try:
                # 如果保留旧数据，在新数据到达时才清空表格
                if table_widget and preserve_old_data:
                    table_widget.setRowCount(0)
                
                # 尝试调用界面的标准数据接收方法
                method_name = f'on_{data_type}_data_received'
                if hasattr(interface, method_name):
                    getattr(interface, method_name)(data)
                else:
                    logger.warning(f"界面 {interface.__class__.__name__} 没有方法 {method_name}")
            except Exception as e:
                logger.error(f"处理数据时出错: {e}")
        
        # 定义错误回调
        def error_callback(error):
            try:
                # 如果保留旧数据且发生错误，不清空表格，保持原有数据
                # 尝试调用界面的标准错误处理方法
                method_name = f'on_{data_type}_data_error'
                if hasattr(interface, method_name):
                    getattr(interface, method_name)(error)
                else:
                    logger.warning(f"界面 {interface.__class__.__name__} 没有方法 {method_name}")
            except Exception as e:
                logger.error(f"处理错误时出错: {e}")
        
        # 发起数据请求
        worker = self.data_manager.get_data_async(
            data_type=data_type,
            success_callback=success_callback,
            error_callback=error_callback,
            force_refresh=force_refresh
        )
        
        # 保存worker引用到界面
        if hasattr(interface, 'worker'):
            interface.worker = worker
        
        return worker


# 创建全局数据管理器实例
data_manager = DataManager()
interface_loader = InterfaceDataLoader(data_manager) 