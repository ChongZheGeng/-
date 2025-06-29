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
            'task_groups': 'get_task_groups',
            'task_groups_with_tasks': 'get_task_groups_with_tasks'
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
            # 1. 检查缓存
            if not force_refresh and self._is_cache_valid(data_type):
                logger.debug(f"使用缓存数据: {data_type}")
                if success_callback:
                    success_callback(self.cache[data_type]['data'])
                self.data_updated.emit(data_type, self.cache[data_type]['data'])
                return None

            # 2. 检查是否有正在进行的请求
            is_new_request = data_type not in self.active_requests

            if is_new_request:
                logger.debug(f"创建新的异步请求: {data_type}")
                # 获取API客户端和方法
                api_method = self._get_api_method(data_type)
                if not api_method:
                    error_msg = f"未知的数据类型: {data_type}"
                    logger.error(error_msg)
                    if error_callback:
                        error_callback(error_msg)
                    self.data_error.emit(data_type, error_msg)
                    return None

                # 创建新的异步工作线程
                if data_type in self.methods_with_params and params is not None:
                    worker = AsyncApiWorker(api_method, params=params)
                elif data_type in self.methods_with_params:
                    worker = AsyncApiWorker(api_method, params=None)
                else:
                    worker = AsyncApiWorker(api_method)

                # 定义仅在首次创建时需要的包装回调
                def wrapped_success(data):
                    self._update_cache(data_type, data)
                    callbacks = self.active_requests.pop(data_type, {}).get('callbacks', [])

                    # 直接触发所有已注册的回调
                    for success_cb, _ in callbacks:
                        if success_cb:
                            try:
                                success_cb(data)
                            except Exception as e:
                                logger.error(f"回调执行失败: {e}", exc_info=True)

                    # 在所有具体回调执行后，发送全局信号
                    self.data_updated.emit(data_type, data)

                def wrapped_error(error):
                    callbacks = self.active_requests.pop(data_type, {}).get('callbacks', [])

                    # 直接触发所有已注册的错误回调
                    for _, error_cb in callbacks:
                        if error_cb:
                            try:
                                error_cb(error)
                            except Exception as e:
                                logger.error(f"错误回调执行失败: {e}", exc_info=True)
                    
                    # 在所有具体回调执行后，发送全局信号
                    self.data_error.emit(data_type, error)

                worker.finished.connect(wrapped_success)
                worker.error.connect(wrapped_error)

                # 记录活跃请求，回调列表初始化为空
                self.active_requests[data_type] = {
                    'worker': worker,
                    'callbacks': []
                }
                
                worker.start()
            else:
                logger.debug(f"合并到现有请求: {data_type}")

            # 3. 为本次调用注册回调（无论是新请求还是合并请求）
            if success_callback or error_callback:
                self.active_requests[data_type]['callbacks'].append((success_callback, error_callback))

            return self.active_requests[data_type]['worker']

        except Exception as e:
            error_msg = f"创建异步请求失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
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
    
    def load_for_interface(self, interface, data_type, table_widget=None, force_refresh=False, preserve_old_data=False, column_mapping=None):
        """
        为界面自动加载数据的简化方法
        
        Args:
            interface: 目标界面对象
            data_type: 数据类型
            table_widget: 表格控件（可选，会自动清空和填充）
            force_refresh: 是否强制刷新
            preserve_old_data: 是否保留旧数据直到新数据加载完成
            column_mapping: 表格列定义，用于自动填充
        """
        # 只有在不保留旧数据时才立即清空表格
        if table_widget and not preserve_old_data:
            self._prepare_table(table_widget, column_mapping)

        # 取消之前的请求
        if hasattr(interface, 'worker') and interface.worker:
            interface.worker.cancel()
        
        # 定义成功回调
        def success_callback(data):
            try:
                # 如果保留旧数据，在新数据到达时才准备表格
                if table_widget and preserve_old_data:
                    self._prepare_table(table_widget, column_mapping)

                # 根据是否有自动填充配置来决定处理方式
                if table_widget and column_mapping:
                    # 使用自动填充功能
                    self._populate_table_automatically(table_widget, column_mapping, data)
                    # 自动填充后，只调用界面方法进行额外操作（如日志记录），但不进行表格填充
                    # method_name = f'on_{data_type}_data_received'
                    # if hasattr(interface, method_name):
                    #     getattr(interface, method_name)(data)
                else:
                    # 没有自动填充配置时，使用传统的界面处理方法
                    method_name = f'on_{data_type}_data_received'
                    if hasattr(interface, method_name):
                        getattr(interface, method_name)(data)
                    else:
                        logger.warning(f"界面 {interface.__class__.__name__} 没有方法 {method_name} 且未提供自动填充配置")
                
                # 发出成功信息提示
                if hasattr(interface, 'window') and interface.window():
                    from qfluentwidgets import InfoBar
                    InfoBar.success("成功", "数据已刷新", duration=1500, parent=interface)

            except Exception as e:
                logger.error(f"处理数据时出错: {e}", exc_info=True)
        
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
                
                if hasattr(interface, 'window') and interface.window():
                    from qfluentwidgets import InfoBar
                    InfoBar.error("加载失败", str(error), duration=3000, parent=interface)
            except Exception as e:
                logger.error(f"处理错误回调时出错: {e}", exc_info=True)

        interface.worker = self.data_manager.get_data_async(
            data_type, 
            success_callback, 
            error_callback, 
            force_refresh=force_refresh
        )

    def _prepare_table(self, table_widget, column_mapping):
        """准备表格，设置表头和列数"""
        from PyQt5.QtWidgets import QHeaderView
        
        table_widget.setRowCount(0)
        if not column_mapping:
            return
            
        table_widget.setColumnCount(len(column_mapping))
        headers = [col.get('header', '') for col in column_mapping]
        table_widget.setHorizontalHeaderLabels(headers)
        
        # 默认设置为交互模式
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        
        # 寻找需要拉伸的列
        stretch_col_index = -1
        for i, col in enumerate(column_mapping):
            if col.get('stretch'):
                stretch_col_index = i
                break
        
        # 如果没有显式设置stretch的列，则寻找最后一列非固定宽度的列进行拉伸
        if stretch_col_index == -1 and len(column_mapping) > 1:
            for i in range(len(column_mapping) - 1, -1, -1):
                if column_mapping[i].get('width') is None:
                    stretch_col_index = i
                    break
        
        # 设置拉伸列
        if stretch_col_index != -1:
            table_widget.horizontalHeader().setSectionResizeMode(stretch_col_index, QHeaderView.Stretch)
        
        # 设置固定列宽
        for i, col in enumerate(column_mapping):
            if col.get('width'):
                table_widget.horizontalHeader().setSectionResizeMode(i, QHeaderView.Fixed)
                table_widget.horizontalHeader().resizeSection(i, col['width'])
    
    def _populate_table_automatically(self, table_widget, column_mapping, response_data):
        """根据列映射自动填充表格"""
        from PyQt5.QtWidgets import QTableWidgetItem, QWidget, QHBoxLayout
        from qfluentwidgets import PrimaryPushButton, PushButton

        data_list = response_data.get('results', [])
        if not isinstance(data_list, list):
            logger.warning(f"期望获得列表类型的数据，但得到了 {type(data_list)}")
            data_list = []

        table_widget.setRowCount(len(data_list))
        for row_index, data_item in enumerate(data_list):
            for col_index, col_def in enumerate(column_mapping):
                col_type = col_def.get('type', 'text')

                if col_type == 'text':
                    key = col_def.get('key')
                    # 支持嵌套key, e.g., 'user.name'
                    value = data_item
                    if key:
                        for k in key.split('.'):
                            value = value.get(k, {}) if isinstance(value, dict) else ''
                    
                    # 格式化
                    formatter = col_def.get('formatter')
                    if formatter:
                        display_text = formatter(value)
                    else:
                        display_text = str(value) if value is not None else ''
                    
                    table_widget.setItem(row_index, col_index, QTableWidgetItem(display_text))

                elif col_type == 'buttons':
                    buttons = col_def.get('buttons', [])
                    action_widget = QWidget()
                    action_layout = QHBoxLayout(action_widget)
                    action_layout.setContentsMargins(2, 2, 2, 2)
                    action_layout.setSpacing(8)

                    for btn_def in buttons:
                        btn_text = btn_def.get('text', 'Button')
                        btn_type = btn_def.get('style', 'default')
                        callback = btn_def.get('callback')

                        if btn_type == 'primary':
                            button = PrimaryPushButton(btn_text)
                        else:
                            button = PushButton(btn_text)
                        
                        if callback:
                            # 使用lambda确保将当前的data_item和callback传递给槽函数
                            # 修复了lambda延迟绑定的问题，确保每个按钮连接到正确的callback
                            button.clicked.connect(lambda _, item=data_item, cb=callback: cb(item))
                        
                        action_layout.addWidget(button)
                    
                    table_widget.setCellWidget(row_index, col_index, action_widget)


# 创建全局数据管理器实例
data_manager = DataManager()
interface_loader = InterfaceDataLoader(data_manager) 