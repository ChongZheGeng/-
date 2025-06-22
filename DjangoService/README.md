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