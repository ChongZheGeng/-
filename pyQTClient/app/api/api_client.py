import requests
from ..common import config

# API 服务器的基础URL
API_BASE_URL = "http://127.0.0.1:8000/api"


class ApiClient:
    """ 一个使用会话来处理认证的API客户端 """

    def __init__(self):
        self.session = requests.Session()
        self.csrf_token = None
        self.current_user = None
        
        # 性能优化配置
        self.session.headers.update({
            'Connection': 'keep-alive',  # 保持连接
            'Accept-Encoding': 'gzip, deflate',  # 启用压缩
        })
        
        # 设置适配器以支持连接池
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # 连接池大小
            pool_maxsize=10       # 最大连接数
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def login(self, username, password):
        """ 调用新的JSON登录接口 """
        login_url = f"{API_BASE_URL}/login/"
        try:
            # 首先获取CSRF令牌
            self.session.get(API_BASE_URL)
            
            # 发送登录请求
            response = self.session.post(login_url, json={'username': username, 'password': password})
            
            if response.status_code == 200:
                # 登录成功，保存CSRF令牌（如果有）
                if 'csrftoken' in self.session.cookies:
                    self.csrf_token = self.session.cookies['csrftoken']
                
                # 保存当前用户信息
                self.current_user = response.json()
                is_superuser = self.current_user.get('is_superuser', False)
                config.set_admin_status(is_superuser)
                return True, "登录成功"
            
            # 从响应中获取更详细的错误信息
            error_message = response.json().get('error', '未知错误')
            return False, error_message

        except requests.exceptions.RequestException as e:
            print(f"API 登录错误: {e}")
            return False, f"网络错误，请检查后端服务是否运行。"

    def _request(self, method, endpoint, **kwargs):
        """ 使用会话封装请求逻辑 """
        url = f"{API_BASE_URL}/{endpoint}/"
        
        # 添加CSRF令牌到所有请求的头部
        headers = kwargs.pop('headers', {})
        if self.csrf_token:
            headers['X-CSRFToken'] = self.csrf_token
        
        if headers:
            kwargs['headers'] = headers
            
        try:
            # session对象会自动发送cookies
            response = self.session.request(method, url, **kwargs)
            
            response.raise_for_status()
            if response.status_code == 204:  # No Content for DELETE
                return True
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error ({method.upper()} {url}): {e}")
            return None

    # --- Tool Management ---

    def get_tools(self):
        """ 获取所有刀具 """
        return self._request('get', 'tools')

    def add_tool(self, data):
        """ 新增刀具 """
        return self._request('post', 'tools', json=data)

    def update_tool(self, tool_id, data):
        """ 更新刀具 """
        return self._request('put', f'tools/{tool_id}', json=data)

    def delete_tool(self, tool_id):
        """ 删除刀具 """
        return self._request('delete', f'tools/{tool_id}')

    # --- User Management ---

    def get_users(self):
        """ 获取所有用户 """
        return self._request('get', 'users')

    def add_user(self, data):
        """ 新增用户 """
        return self._request('post', 'users', json=data)

    def update_user(self, user_id, data):
        """ 更新用户 """
        return self._request('put', f'users/{user_id}', json=data)

    def delete_user(self, user_id):
        """ 删除用户 """
        return self._request('delete', f'users/{user_id}')

    # --- Composite Material Management ---

    def get_composite_materials(self):
        """ 获取所有复合材料构件 """
        return self._request('get', 'composite-materials')

    def add_composite_material(self, data):
        """ 新增复合材料构件 """
        return self._request('post', 'composite-materials', json=data)

    def update_composite_material(self, material_id, data):
        """ 更新复合材料构件 """
        return self._request('put', f'composite-materials/{material_id}', json=data)

    def delete_composite_material(self, material_id):
        """ 删除复合材料构件 """
        return self._request('delete', f'composite-materials/{material_id}')

    # --- Processing Task Management ---

    def get_processing_tasks(self, params=None):
        """ 获取所有加工任务 """
        return self._request('get', 'processing-tasks', params=params)

    def add_processing_task(self, data):
        """ 新增加工任务 """
        return self._request('post', 'processing-tasks', json=data)

    def update_processing_task(self, task_id, data):
        """ 更新加工任务 """
        return self._request('put', f'processing-tasks/{task_id}', json=data)

    def delete_processing_task(self, task_id):
        """ 删除加工任务 """
        return self._request('delete', f'processing-tasks/{task_id}')

    def get_processing_task_detail(self, task_id):
        """ 获取单个加工任务的详细信息 """
        return self._request('get', f'processing-tasks/{task_id}')

    def clone_processing_task(self, task_id):
        """ 克隆加工任务 """
        return self._request('post', f'processing-tasks/{task_id}/clone')

    # --- Task Group Management ---

    def get_task_groups(self):
        """ 获取所有任务组 """
        return self._request('get', 'task-groups')

    def get_task_groups_with_tasks(self):
        """ 获取任务组及其关联的任务数据 """
        return self._request('get', 'task-groups/with_tasks')

    def add_task_group(self, data):
        """ 新增任务组 """
        return self._request('post', 'task-groups', json=data)

    def update_task_group(self, group_id, data):
        """ 更新任务组 """
        return self._request('put', f'task-groups/{group_id}', json=data)

    def delete_task_group(self, group_id):
        """ 删除任务组 """
        return self._request('delete', f'task-groups/{group_id}')

    # --- Sensor Data Management ---

    def get_sensor_data(self, params=None):
        """ 获取所有传感器数据 """
        return self._request('get', 'sensor-data', params=params)

    def add_sensor_data(self, data):
        """ 新增传感器数据 """
        return self._request('post', 'sensor-data', json=data)

    def update_sensor_data(self, data_id, data):
        """ 更新传感器数据 """
        return self._request('put', f'sensor-data/{data_id}', json=data)

    def delete_sensor_data(self, data_id):
        """ 删除传感器数据 """
        return self._request('delete', f'sensor-data/{data_id}')

    def delete_sensor_file_from_webdav(self, file_url):
        """ 从WebDAV删除传感器数据文件 """
        from ..common.config import get_webdav_credentials
        from webdav4.client import Client
        import os
        
        # 检查WebDAV配置
        credentials = get_webdav_credentials()
        if not credentials or not credentials['enabled']:
            return False, "WebDAV未配置或未启用"
        
        try:
            # 准备WebDAV客户端
            client = Client(
                base_url=credentials['url'],
                auth=(credentials['username'], credentials['password'])
            )
            
            # 从完整URL中提取相对路径
            base_url = credentials['url'].rstrip('/')
            if file_url.startswith(base_url):
                relative_path = file_url[len(base_url):].lstrip('/')
                
                # 检查文件是否存在
                if client.exists(relative_path):
                    client.remove(relative_path)
                    return True, f"文件删除成功: {os.path.basename(relative_path)}"
                else:
                    return False, "文件不存在"
            else:
                return False, "文件URL格式不正确"
                
        except Exception as e:
            return False, f"删除文件失败: {str(e)}"

    def sync_sensor_files_with_database(self):
        """ 同步WebDAV文件与数据库记录 """
        from ..common.config import get_webdav_credentials
        from webdav4.client import Client
        import os
        
        # 检查WebDAV配置
        credentials = get_webdav_credentials()
        if not credentials or not credentials['enabled']:
            return False, "WebDAV未配置或未启用", []
        
        try:
            # 准备WebDAV客户端
            client = Client(
                base_url=credentials['url'],
                auth=(credentials['username'], credentials['password'])
            )
            
            sensor_data_dir = 'sensor_data'
            unmanaged_dir = 'sensor_data/unmanaged'
            
            # 检查sensor_data目录是否存在
            if not client.exists(sensor_data_dir):
                return True, "sensor_data目录不存在，无需同步", []
            
            # 创建unmanaged目录（如果不存在）
            if not client.exists(unmanaged_dir):
                client.mkdir(unmanaged_dir)
            
            # 获取所有传感器数据记录中的文件URL
            sensor_data_response = self.get_sensor_data()
            if not sensor_data_response or 'results' not in sensor_data_response:
                return False, "无法获取传感器数据记录", []
            
            # 提取数据库中所有的文件名
            db_files = set()
            base_url = credentials['url'].rstrip('/')
            for record in sensor_data_response['results']:
                file_url = record.get('file_url', '')
                if file_url.startswith(base_url):
                    relative_path = file_url[len(base_url):].lstrip('/')
                    if relative_path.startswith('sensor_data/') and not relative_path.startswith('sensor_data/unmanaged/'):
                        filename = os.path.basename(relative_path)
                        db_files.add(filename)
            
            # 获取WebDAV中sensor_data目录的所有文件
            webdav_files = []
            for item in client.ls(sensor_data_dir, detail=True):
                if item['type'] == 'file':
                    filename = os.path.basename(item['name'])
                    webdav_files.append(filename)
            
            # 找出多余的文件（在WebDAV中存在但数据库中没有记录的文件）
            unmanaged_files = []
            for filename in webdav_files:
                if filename not in db_files:
                    # 移动文件到unmanaged目录
                    src_path = f"{sensor_data_dir}/{filename}"
                    dst_path = f"{unmanaged_dir}/{filename}"
                    
                    try:
                        client.move(src_path, dst_path)
                        unmanaged_files.append(filename)
                    except Exception as e:
                        print(f"移动文件 {filename} 失败: {e}")
            
            if unmanaged_files:
                message = f"已将 {len(unmanaged_files)} 个未管理的文件移动到 unmanaged 目录"
            else:
                message = "所有文件都有对应的数据库记录，无需移动"
                
            return True, message, unmanaged_files
            
        except Exception as e:
            return False, f"文件同步失败: {str(e)}", []

    def upload_sensor_file_to_webdav(self, file_path, task_id, sensor_type, sensor_id=None, description=None):
        """ 上传传感器数据文件到WebDAV并创建数据库记录 """
        from ..common.config import get_webdav_credentials
        from webdav4.client import Client
        from datetime import datetime
        import os
        
        # 检查WebDAV配置
        credentials = get_webdav_credentials()
        if not credentials or not credentials['enabled']:
            return False, "WebDAV未配置或未启用"
        
        try:
            # 准备WebDAV客户端
            client = Client(
                base_url=credentials['url'],
                auth=(credentials['username'], credentials['password'])
            )
            
            # 检查或创建目标目录
            remote_dir = 'sensor_data'
            if not client.exists(remote_dir):
                client.mkdir(remote_dir)
            
            # 生成文件名
            file_name = os.path.basename(file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            remote_filename = f"{timestamp}_{file_name}"
            remote_path = f"{remote_dir}/{remote_filename}"
            
            # 上传文件
            client.upload_file(from_path=file_path, to_path=remote_path, overwrite=True)
            
            # 构建文件URL
            file_url = f"{credentials['url'].rstrip('/')}/{remote_path}"
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            # 创建数据库记录
            sensor_data = {
                'sensor_type': sensor_type,
                'file_name': remote_filename,
                'file_url': file_url,
                'file_size': file_size,
                'processing_task': task_id,
                'sensor_id': sensor_id or '',
                'description': description or ''
            }
            
            result = self.add_sensor_data(sensor_data)
            if result:
                return True, f"文件上传成功: {remote_filename}"
            else:
                return False, "文件上传成功但数据库记录创建失败"
                
        except Exception as e:
            return False, f"上传失败: {str(e)}"

    def get_current_user_info(self):
        """ 获取当前登录用户信息 """
        try:
            response = self._request('get', 'user-info')
            if response:
                self.current_user = response
            return response
        except Exception as e:
            print(f"获取当前用户信息失败: {e}")
            return None

    def set_current_user_personnel(self, personnel_id):
        """ 设置当前用户关联的人员 """
        try:
            return self._request('post', 'user-info', json={'personnel_id': personnel_id})
        except Exception as e:
            print(f"设置当前用户人员关联失败: {e}")
            return None


# 创建一个全局的api客户端实例
api_client = ApiClient() 