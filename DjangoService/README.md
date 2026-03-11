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


## A_damage 训练与推荐（基于论文表2 9组数据）

推荐模块目录：`DjangoService/process_data/recommendation/`

### 保留的源码与配置
- `seed_damage_points.py`：论文表2的 9 组种子数据（硬编码）
- `generate_damage_dataset.py`：生成扩增训练集（默认 2000 条）
- `train_damage_model.py`：训练并对比模型，输出报告
- `infer_damage_model.py`：单点预测
- `recommend_by_level.py`：按损伤等级推荐参数
- `level_config.json`：损伤等级阈值配置
- `training_report.md`：训练说明与指标

### 1) 生成训练数据
在 `DjangoService/` 目录执行：

```bash
python -m process_data.recommendation.generate_damage_dataset
```

默认会生成：
- `process_data/recommendation/generated_damage_dataset.csv`
- `process_data/recommendation/level_config.json`

### 2) 训练模型
在 `DjangoService/` 目录执行：

```bash
python -m process_data.recommendation.train_damage_model
```

默认会生成模型文件：
- `process_data/recommendation/model.pkl`

> 注意：`model.pkl` / `*.joblib` 属于训练产物，默认不提交到 Git（已在 `.gitignore` 排除）。

### 3) 推荐功能依赖文件
推荐相关 API / 前端页面依赖以下文件：
- `generated_damage_dataset.csv`（用于训练输入）
- `level_config.json`（等级区间映射）
- `model.pkl`（已训练模型）

如果 `model.pkl` 不存在：
- 后端会返回可理解错误（提示“请先训练模型”）
- 前端会显示失败提示，而不会崩溃

### 4) 后端接口
- `POST /api/model/generate-damage-dataset/`
- `POST /api/model/train-damage-model/`
- `POST /api/model/predict-damage/`
- `POST /api/model/recommend-by-level/`
