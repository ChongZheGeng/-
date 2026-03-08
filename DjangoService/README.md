# 工艺数据管理系统

这是一个基于Django和Django REST framework开发的工艺数据管理系统后端，用于存储和管理工艺数据。

## 功能特点

- 工艺分类管理：支持多级分类结构
- 工艺参数定义：支持数值型、文本型、布尔型、日期型和枚举型参数
- 工艺模板管理：可定义不同工艺的模板，关联多个参数
- 工艺数据记录：基于模板录入具体工艺数据
- REST API接口：提供完整的REST API用于前端集成

## 技术栈

- Python 3.9+
- Django 5.2.1
- Django REST framework 3.15.0
- MySQL 数据库

## 项目结构

```
DjangoService/
├── DjangoService/        # 项目配置目录
│   ├── settings.py       # 项目设置
│   ├── urls.py           # 主URL配置
│   ├── wsgi.py           # WSGI配置
│   └── asgi.py           # ASGI配置
├── process_data/         # 工艺数据应用
│   ├── models.py         # 数据模型
│   ├── serializers.py    # 序列化器
│   ├── views.py          # API视图
│   ├── urls.py           # URL路由
│   ├── admin.py          # 管理界面配置
│   └── tests.py          # 测试用例
├── templates/            # 模板目录
├── manage.py             # Django管理脚本
└── requirements.txt      # 项目依赖
```

## 安装与设置

1. 克隆项目到本地

2. 安装Python依赖
```bash
pip install -r requirements.txt
```

3. 创建数据库和用户
```sql
CREATE DATABASE ProcessData CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

4. 迁移数据库
```bash
python manage.py makemigrations
python manage.py migrate
```

5. 创建管理员用户
```bash
python manage.py createsuperuser
```

6. 启动开发服务器
```bash
python manage.py runserver
```


## 开发环境 SQLite 启动步骤

当 `USE_MYSQL` 未设置为 `1` 时，项目会使用 SQLite（默认数据库文件：`DjangoService/db.sqlite3`）。

1. 初始化开发数据库（迁移 + 开发管理员）

```bash
cd DjangoService
python manage.py init_dev_data
```

> 可选：通过环境变量配置开发管理员密码（默认 `hedgehog123`）
>
> - Linux/macOS: `export DEV_ADMIN_PASSWORD=你的密码`
> - PowerShell: `$env:DEV_ADMIN_PASSWORD="你的密码"`

2. 启动 Django

```bash
python manage.py runserver 127.0.0.1:8000
```

3. 启动前端（PyQt）

```bash
cd ..\pyQTClient
python demo.py
```

4. 默认开发管理员账号

- 用户名：`hedgehog`
- 密码：读取 `DEV_ADMIN_PASSWORD`，未设置时为 `hedgehog123`

### PowerShell 一键初始化示例

```powershell
cd DjangoService
$env:DEV_ADMIN_PASSWORD = "hedgehog123"
python manage.py init_dev_data
python manage.py runserver 127.0.0.1:8000
```

## API接口

系统提供以下API接口：

- `/api/categories/` - 工艺分类管理
- `/api/parameters/` - 工艺参数管理
- `/api/templates/` - 工艺模板管理
- `/api/data/` - 工艺数据记录管理

详细API文档可通过以下地址访问：
- `/docs/` - API文档

## 身份验证

API使用基于会话和基本认证，可以通过以下方式进行身份验证：

- 基本认证: 使用HTTP基本认证提供用户名和密码
- 会话认证: 通过`/api-auth/login/`登录后使用会话认证 

## Windows 一键接口测试

> 在 Windows PowerShell 中，`curl` 常常是 `Invoke-WebRequest` 的别名，参数行为与 Linux 不一致。
> 建议使用 `curl.exe` 或 `Invoke-RestMethod`。

### 1) 健康检查（推荐）

```powershell
cd DjangoService
.\test_health.ps1
```

或直接执行：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health/" -Method GET
```

### 2) 推荐接口（如果仓库中有 `test_recommend_api.ps1`）

```powershell
# 仅当脚本存在时运行
.\test_recommend_api.ps1
```

### 3) 启动顺序（Windows）

1. 先启动 Django：
   ```powershell
   cd DjangoService
   python manage.py runserver 127.0.0.1:8000
   ```
2. 再启动 PyQt 客户端：
   ```powershell
   cd ..\pyQTClient
   python demo.py
   ```
