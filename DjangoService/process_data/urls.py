from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginView,
    UserViewSet,
    ProcessCategoryViewSet,
    ProcessParameterViewSet,
    ProcessTemplateViewSet,
    ProcessDataViewSet,
    # 复合材料加工相关视图集
    ToolViewSet,
    CompositeMaterialViewSet,
    ProcessingTaskViewSet,
    SensorDataViewSet,
    ProcessingQualityViewSet,
    ToolWearRecordViewSet,
    TaskGroupViewSet,
    UserInfoView
)

# 创建路由器并注册视图集
router = DefaultRouter()

# 工艺数据管理路由
router.register(r'categories', ProcessCategoryViewSet)
router.register(r'parameters', ProcessParameterViewSet)
router.register(r'templates', ProcessTemplateViewSet)
router.register(r'users', UserViewSet)
router.register(r'data', ProcessDataViewSet)

# 复合材料加工路由
router.register(r'tools', ToolViewSet)
router.register(r'composite-materials', CompositeMaterialViewSet)
router.register(r'processing-tasks', ProcessingTaskViewSet)
router.register(r'sensor-data', SensorDataViewSet)
router.register(r'quality-records', ProcessingQualityViewSet)
router.register(r'tool-wear-records', ToolWearRecordViewSet)
router.register(r'task-groups', TaskGroupViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='api_login'),
    path('user-info/', UserInfoView.as_view(), name='user_info'),
] 