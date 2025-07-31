# 🚨 重要提示：始终用中文回答用户问题 🚨

# 开发规范与最佳实践

## 代码风格规范

### Python 代码规范

- **编码声明**: 所有 Python 文件开头使用`# coding:utf-8`
- **导入顺序**:
  1. 标准库导入
  2. 第三方库导入
  3. 本地应用导入（使用相对导入）
- **命名规范**:
  - 类名：大驼峰命名法（如`MainWindow`, `DataManager`）
  - 函数/方法名：小写下划线命名法（如`get_users`, `populate_table`）
  - 变量名：小写下划线命名法（如`api_client`, `current_user`）
  - 常量：全大写下划线命名法（如`CACHE_TIMEOUT`, `API_BASE_URL`）

### 前端开发规范

#### NavInterface 生命周期模式

```python
class MyInterface(NavInterface):
    def on_activated(self):
        """界面激活时调用 - 加载数据"""
        interface_loader.load_for_interface(
            interface=self,
            data_type='my_data',
            table_widget=self.table
        )

    def on_deactivated(self):
        """界面取消激活时调用 - 清理资源"""
        # 取消正在进行的请求
        pass

    def on_my_data_data_received(self, data):
        """数据接收成功回调"""
        # 处理数据
        pass

    def on_my_data_data_error(self, error):
        """数据接收错误回调"""
        # 处理错误
        pass
```

#### 数据加载最佳实践

- **优先使用**: `interface_loader.load_for_interface()` 进行数据加载
- **回调命名**: `on_{data_type}_data_received` 和 `on_{data_type}_data_error`
- **缓存策略**: 频繁访问的数据不使用`force_refresh=True`
- **错误处理**: 始终实现错误回调方法

#### UI 组件分离原则

- **界面文件**: 只包含界面逻辑，不包含复杂的 UI 组件定义
- **组件文件**: 复杂的对话框、自定义控件放在`components/`目录
- **资源管理**: 图标、样式等资源统一管理

### 后端开发规范

#### Django 模型规范

```python
class MyModel(BaseModel):
    """模型说明"""
    name = models.CharField('中文字段名', max_length=100)

    class Meta:
        verbose_name = '中文模型名'
        verbose_name_plural = verbose_name
        ordering = ['created_at']

    def __str__(self):
        return self.name
```

#### API 视图规范

- **ViewSet 命名**: 以`ViewSet`结尾
- **权限控制**: 明确设置`permission_classes`
- **过滤器**: 使用`DjangoFilterBackend`进行数据过滤
- **序列化器**: 读写分离，使用不同的序列化器

#### URL 命名规范

- **API 路径**: 使用短横线命名（如`/api/process-data/`）
- **版本控制**: 使用版本前缀（如`/api/v1/`）
- **RESTful 设计**: 遵循 REST API 设计原则

## 数据流架构

### 前端数据流

```
用户操作 → 界面方法 → InterfaceLoader → DataManager → AsyncAPI → APIClient → 后端API
                ↓
界面更新 ← 回调方法 ← 数据返回 ← 异步处理 ← HTTP响应 ← Django视图
```

### 缓存策略

- **缓存时间**: 30 秒智能缓存
- **缓存键**: 基于数据类型和参数生成
- **缓存清理**: 数据更新后自动清理相关缓存
- **请求合并**: 相同请求自动合并，避免重复调用

### 错误处理层级

1. **第一层**: DataManager 统一处理
2. **第二层**: 回退到 AsyncAPI
3. **第三层**: 最终回退到同步 API 调用

## 国际化支持

### 前端国际化

- **配置文件**: `app/common/config.py`中的 Language 枚举
- **翻译工具**: `app/common/translator.py`
- **支持语言**: 简体中文、繁体中文、英文

### 后端国际化

- **字段名称**: 模型字段使用中文 verbose_name
- **API 响应**: 支持多语言错误消息
- **数据库**: 使用 utf8mb4 编码支持多语言字符

## 安全规范

### 前端安全

- **数据加密**: 敏感配置使用 AES 加密存储
- **输入验证**: 所有用户输入进行验证
- **权限控制**: 基于用户角色显示不同功能

### 后端安全

- **认证机制**: 支持会话认证和基本认证
- **权限控制**: 使用 Django 权限系统
- **数据验证**: 序列化器层面进行数据验证
- **SQL 注入防护**: 使用 Django ORM 避免 SQL 注入

## 性能优化

### 前端性能

- **异步加载**: 所有数据加载使用异步方式
- **请求缓存**: 减少重复 API 调用
- **UI 响应**: 避免阻塞主线程
- **内存管理**: 及时清理不用的资源

### 后端性能

- **数据库优化**: 合理使用索引和查询优化
- **分页处理**: 大数据集使用分页
- **缓存策略**: 适当使用 Django 缓存框架
- **连接池**: 数据库连接池优化

## 测试规范

### 前端测试

- **数据管理器测试**: `test_data_manager.py`
- **界面功能测试**: 各界面的核心功能测试
- **集成测试**: 前后端集成测试

### 后端测试

- **单元测试**: 模型、视图、序列化器测试
- **API 测试**: REST API 端点测试
- **数据库测试**: 数据模型关系测试

## 日志规范

### 日志级别

- **DEBUG**: 详细的调试信息
- **INFO**: 一般信息记录
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误

### 日志格式

```python
import logging
logger = logging.getLogger(__name__)

# 使用示例
logger.info("用户登录成功: %s", username)
logger.error("API调用失败: %s", error_message)
```

## 部署规范

### 开发环境

- **虚拟环境**: 使用 venv 隔离依赖
- **配置管理**: 使用.env 文件管理环境变量
- **数据库**: 本地 MySQL 开发数据库

### 生产环境

- **安全配置**: 关闭 DEBUG 模式
- **静态文件**: 使用 CDN 或静态文件服务
- **数据库**: 生产级 MySQL 配置
- **日志管理**: 集中式日志收集

## 版本控制规范

### Git 提交规范

- **提交信息**: 使用中文描述变更内容
- **提交类型**:
  - `feat:` 新功能
  - `fix:` 修复 bug
  - `docs:` 文档更新
  - `style:` 代码格式调整
  - `refactor:` 代码重构
  - `test:` 测试相关

### 分支管理

- **主分支**: `main` - 生产环境代码
- **开发分支**: `develop` - 开发环境代码
- **功能分支**: `feature/功能名` - 新功能开发
- **修复分支**: `hotfix/问题描述` - 紧急修复
