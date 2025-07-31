# 🚨 重要提示：始终用中文回答用户问题 🚨

# 项目结构详解

## 根目录布局

```
├── DjangoService/          # Django后端REST API服务
├── pyQTClient/            # PyQt5前端桌面应用程序
├── app/                   # 共享应用程序资源
├── venv/                  # Python虚拟环境
├── README.md              # 项目概述
├── ARCHITECTURE_GUIDE.md  # 详细架构文档
└── requirements.txt       # 根级依赖
```

## 后端结构 (DjangoService/)

```
DjangoService/
├── DjangoService/         # Django项目配置
│   ├── __init__.py        # Python包初始化文件
│   ├── settings.py        # 项目设置和配置（数据库、中间件、应用等）
│   ├── urls.py           # 主URL路由配置
│   ├── wsgi.py           # WSGI配置（用于部署）
│   ├── asgi.py           # ASGI配置（用于异步部署）
│   └── __pycache__/      # Python字节码缓存
├── process_data/          # 主应用模块
│   ├── __init__.py        # 应用包初始化
│   ├── models.py         # 数据库模型定义（工艺、刀具、任务等）
│   ├── serializers.py    # DRF序列化器（数据转换）
│   ├── views.py          # API视图和端点（业务逻辑）
│   ├── urls.py           # 应用URL路由
│   ├── admin.py          # Django管理界面配置
│   ├── apps.py           # 应用配置
│   ├── tests.py          # 单元测试
│   ├── migrations/       # 数据库迁移文件
│   │   ├── __init__.py   # 迁移包初始化
│   │   ├── 0001_initial.py # 初始数据库结构
│   │   └── 0002_*.py     # 后续数据库变更
│   └── __pycache__/      # Python字节码缓存
├── templates/            # HTML模板目录（当前为空）
├── logs/                 # 应用程序日志
│   └── django.log        # Django运行日志
├── .idea/                # PyCharm IDE配置文件
├── manage.py             # Django管理脚本
├── requirements.txt      # 后端依赖列表
└── README.md             # 后端文档
```

## 前端结构 (pyQTClient/)

```
pyQTClient/
├── app/                  # 应用程序核心代码
│   ├── view/             # UI组件和界面
│   │   ├── __init__.py           # 视图包初始化
│   │   ├── main_window.py        # 主应用程序窗口（导航容器）
│   │   ├── login_window.py       # 登录界面
│   │   ├── nav_interface.py      # 导航基类（生命周期管理）
│   │   ├── dashboard_interface.py    # 系统概览界面
│   │   ├── tool_interface.py         # 刀具管理界面
│   │   ├── user_interface.py         # 用户管理界面
│   │   ├── composite_material_interface.py # 复合材料管理界面
│   │   ├── processing_task_interface.py   # 加工任务界面
│   │   ├── task_group_interface.py       # 任务分组界面
│   │   ├── sensor_data_interface.py      # 传感器数据界面
│   │   ├── setting_interface.py         # 设置界面
│   │   ├── task_detail_interface.py     # 任务详情界面
│   │   ├── file_transfer_manager.py     # 文件传输管理器
│   │   ├── components/           # 可重用UI组件
│   │   │   ├── __init__.py               # 组件包初始化
│   │   │   ├── tool_component.py         # 刀具相关组件
│   │   │   ├── user_component.py         # 用户相关组件
│   │   │   ├── composite_material_component.py # 材料组件
│   │   │   ├── processing_task_component.py    # 任务组件
│   │   │   ├── task_group_component.py         # 任务分组组件
│   │   │   ├── sensor_data_component.py        # 传感器组件
│   │   │   ├── setting_component.py            # 设置组件
│   │   │   └── task_detail_component.py        # 任务详情组件
│   │   └── __pycache__/          # Python字节码缓存
│   ├── api/              # 后端通信层
│   │   ├── __init__.py           # API包初始化
│   │   ├── api_client.py         # 直接API客户端（HTTP请求封装）
│   │   ├── async_api.py          # 异步API包装器（后台线程）
│   │   ├── data_manager.py       # 统一数据管理系统（缓存、去重）
│   │   └── __pycache__/          # Python字节码缓存
│   ├── common/           # 共享工具
│   │   ├── __init__.py           # 通用包初始化
│   │   ├── config.py             # 配置管理（QSettings、加密）
│   │   ├── signal_bus.py         # 全局事件系统（Qt信号）
│   │   ├── icon.py               # 图标定义（FluentIcon枚举）
│   │   ├── translator.py         # 国际化工具
│   │   ├── trie.py               # 搜索工具（前缀树）
│   │   ├── resource.py           # 资源管理
│   │   └── __pycache__/          # Python字节码缓存
│   ├── resource/         # 静态资源
│   │   └── background.png        # 背景图片
│   ├── resource_rc.py    # Qt资源编译文件
│   ├── resource.qrc      # Qt资源配置文件
│   └── __pycache__/      # Python字节码缓存
├── .idea/                # PyCharm IDE配置
├── .vscode/              # VS Code配置
│   └── settings.json     # VS Code设置
├── demo.py               # 应用程序入口点（启动脚本）
├── DATA_MANAGER_GUIDE.md # 数据管理器使用指南
└── __pycache__/          # Python字节码缓存
```

## 关键架构模式

### 前端架构模式

- **NavInterface 模式**: 所有主界面继承自`NavInterface`，实现一致的生命周期管理
- **数据管理器模式**: 集中式数据加载，具备缓存、请求去重和异步处理功能
- **信号总线模式**: 使用 Qt 信号进行全局事件通信
- **组件分离模式**: UI 组件隔离在`app/view/components/`目录中

### 后端架构模式

- **REST API 设计**: 标准 Django REST Framework 模式
- **模型-视图-序列化器**: 数据、逻辑和表示的清晰分离
- **多级分类**: 工艺的分层数据组织

### 通信模式

- **HTTP REST**: 基于 JSON 的 API 通信
- **异步加载**: 非阻塞 UI，后台数据获取
- **请求缓存**: 30 秒智能缓存，减少服务器负载
- **错误处理**: 三层回退系统（DataManager → AsyncAPI → SyncAPI）

## 文件命名约定

### 前端

- **界面文件**: `*_interface.py` 用于主功能页面
- **组件文件**: `components/`目录中的描述性名称
- **API 方法**: `get_*`, `add_*`, `update_*`, `delete_*` 模式
- **回调方法**: `on_*_data_received`, `on_*_data_error` 模式

### 后端

- **模型**: 单数名词（如`ProcessData`, `Tool`）
- **视图**: 以`ViewSet`结尾的 ViewSet 类
- **URL**: 使用短横线命名，带版本前缀（`/api/v1/process-data/`）

## 导入约定

- **相对导入**: 在同一应用程序内使用相对导入
- **绝对导入**: 对外部库使用绝对导入
- **一致路径**: 在模块间保持一致的导入路径

## 配置管理

- **前端配置**: `app/common/config.py` 使用 QSettings
- **后端配置**: Django 设置，支持环境变量
- **数据库配置**: MySQL，使用 utf8mb4 编码支持国际化

## 核心数据模型

### 后端模型（process_data/models.py）

- **BaseModel**: 基础模型（创建时间、更新时间、删除标记）
- **ProcessCategory**: 工艺分类（支持多级分类）
- **ProcessParameter**: 工艺参数定义（数值、文本、布尔、日期、枚举类型）
- **Tool**: 刀具管理
- **CompositeMaterial**: 复合材料
- **ProcessingTask**: 加工任务
- **TaskGroup**: 任务分组
- **SensorData**: 传感器数据
- **User**: 用户管理（基于 Django 内置用户模型）

### 前端界面对应关系

- **DashboardInterface** ↔ 系统概览数据
- **ToolInterface** ↔ Tool 模型
- **UserInterface** ↔ User 模型
- **CompositeMaterialInterface** ↔ CompositeMaterial 模型
- **ProcessingTaskInterface** ↔ ProcessingTask 模型
- **TaskGroupInterface** ↔ TaskGroup 模型
- **SensorDataInterface** ↔ SensorData 模型
