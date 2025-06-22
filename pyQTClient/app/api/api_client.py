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
        
        # 添加CSRF令牌到请求头（如果有）
        headers = kwargs.pop('headers', {})
        if method in ['post', 'put', 'patch', 'delete'] and self.csrf_token:
            headers['X-CSRFToken'] = self.csrf_token
        
        if headers:
            kwargs['headers'] = headers
            
        try:
            # session对象会自动发送cookies
            response = self.session.request(method, url, **kwargs)
            
            # 打印请求和响应信息，用于调试
            print(f"Request: {method.upper()} {url}")
            print(f"Headers: {kwargs.get('headers', {})}")
            print(f"Response Status: {response.status_code}")
            print(f"Response Content: {response.content[:200]}...")
            
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

    def get_processing_tasks(self):
        """ 获取所有加工任务 """
        return self._request('get', 'processing-tasks')

    def add_processing_task(self, data):
        """ 新增加工任务 """
        return self._request('post', 'processing-tasks', json=data)

    def update_processing_task(self, task_id, data):
        """ 更新加工任务 """
        return self._request('put', f'processing-tasks/{task_id}', json=data)

    def delete_processing_task(self, task_id):
        """ 删除加工任务 """
        return self._request('delete', f'processing-tasks/{task_id}')

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