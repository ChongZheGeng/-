# 🚨 重要提示：始终用中文回答用户问题 🚨

# 技术栈

## 后端 (DjangoService)

### 核心框架

- **Django 5.2.1** - Web 框架
- **Django REST Framework 3.15.0** - API 框架
- **Python 3.9+** - 编程语言

### 数据库与存储

- **MySQL** - 主数据库，使用 utf8mb4 编码
- **mysqlclient 2.2.4** - MySQL 数据库适配器

### 附加库

- **django-cors-headers** - 处理 API 的 CORS 跨域访问
- **django-filter** - API 过滤功能
- **python-dotenv** - 环境变量管理
- **Markdown** - 文档渲染
- **coreapi** - API 模式生成

## 前端 (pyQTClient)

### UI 框架

- **PyQt5 5.15.11** - 桌面应用程序框架
- **PyQt-Fluent-Widgets 1.8.1** - 现代 Fluent UI 组件
- **PyQt5-Frameless-Window** - 自定义窗口样式

### 核心库

- **requests 2.32.4** - HTTP 客户端，用于 API 通信
- **httpx 0.28.1** - 异步 HTTP 客户端
- **pillow 11.2.1** - 图像处理
- **numpy 2.2.6** - 数值计算
- **scipy 1.15.3** - 科学计算

### 工具库

- **python-dateutil** - 日期/时间处理
- **darkdetect** - 系统主题检测
- **colorthief** - 从图像提取颜色
- **pycryptodome** - 加密功能

## 常用命令

### 后端开发

```bash
# 进入Django服务目录
cd DjangoService

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 运行开发服务器
python manage.py runserver

# 运行测试
python manage.py test
```

### 前端开发

```bash
# 进入PyQt客户端目录
cd pyQTClient

# 安装依赖（从根目录）
pip install -r requirements.txt

# 运行应用程序
python demo.py

# 运行数据管理器测试
python test_data_manager.py
```

### 项目设置

```bash
# 从根目录安装所有依赖
pip install -r requirements.txt

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

## 开发环境

- **平台**: 跨平台（主要针对 Windows）
- **Python 版本**: 3.9+
- **数据库**: MySQL，使用 utf8mb4 字符集
- **IDE**: 推荐 PyCharm/VS Code
- **版本控制**: Git
