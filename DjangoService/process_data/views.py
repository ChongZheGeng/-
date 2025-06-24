from django.shortcuts import render
from rest_framework import viewsets, permissions, filters, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.contrib.auth import login, logout, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User

from .models import (
    ProcessCategory,
    ProcessParameter,
    ProcessTemplate,
    TemplateParameter,
    ProcessData,
    ParameterValue,
    # 复合材料加工相关模型
    Tool,
    CompositeMaterial,
    ProcessingTask,
    ProcessingParameter,
    SensorData,
    ProcessingQuality,
    ToolWearRecord,
    TaskGroup
)
from .serializers import (
    ProcessCategorySerializer,
    ProcessParameterSerializer,
    ProcessTemplateSerializer,
    TemplateParameterSerializer,
    ProcessDataSerializer,
    ProcessDataCreateSerializer,
    ParameterValueSerializer,
    UserSerializer,
    UserCreateUpdateSerializer,
    # 复合材料加工相关序列化器
    ToolSerializer,
    CompositeMaterialSerializer,
    ProcessingTaskListSerializer,
    ProcessingTaskDetailSerializer,
    ProcessingTaskCreateUpdateSerializer,
    ProcessingParameterSerializer,
    SensorDataSerializer,
    ProcessingQualitySerializer,
    ToolWearRecordSerializer,
    TaskGroupSerializer
)


# 自定义权限类，允许已登录用户执行任何操作
class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    自定义权限类，允许已登录用户执行任何操作，未登录用户只能读取数据
    """
    def has_permission(self, request, view):
        # 允许所有GET, HEAD, OPTIONS请求
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 对于其他方法（POST, PUT, DELETE等），需要用户已登录
        return request.user and request.user.is_authenticated


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(views.APIView):
    """
    用户登录视图
    接收用户名和密码，成功则登录并返回用户信息，失败则返回错误信息。
    """
    permission_classes = [permissions.AllowAny]  # 允许任何用户访问此视图

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        
        from django.contrib.auth import authenticate
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return Response({
                'id': user.id,
                'username': user.username,
                'email': user.email
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "用户名或密码错误"}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class UserViewSet(viewsets.ModelViewSet):
    """
    用户视图集
    允许管理员查看、创建、更新和删除用户。
    """
    queryset = get_user_model().objects.all().order_by('id')
    permission_classes = [permissions.IsAdminUser]  # 仅限管理员访问
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'email']

    def get_serializer_class(self):
        """根据操作类型返回不同的序列化器"""
        if self.action in ['create', 'update', 'partial_update']:
            return UserCreateUpdateSerializer
        return UserSerializer

    def perform_destroy(self, instance):
        """
        在删除用户前进行检查，防止删除自己或唯一的超级用户。
        """
        if instance == self.request.user:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("不能删除当前登录的用户。")
        
        # 可选：增加逻辑防止删除最后一个超级用户
        if instance.is_superuser:
            if get_user_model().objects.filter(is_superuser=True).count() <= 1:
                from rest_framework.exceptions import ValidationError
                raise ValidationError("不能删除唯一的超级管理员。")

        super().perform_destroy(instance)


class ProcessCategoryViewSet(viewsets.ModelViewSet):
    """工艺分类视图集"""
    queryset = ProcessCategory.objects.filter(is_deleted=False).order_by('code')
    serializer_class = ProcessCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['parent']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['code', 'name', 'created_at']
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """获取分类树形结构"""
        # 获取所有顶级分类
        root_categories = self.get_queryset().filter(parent=None)
        serializer = self.get_serializer(root_categories, many=True)
        return Response(serializer.data)


class ProcessParameterViewSet(viewsets.ModelViewSet):
    """工艺参数视图集"""
    queryset = ProcessParameter.objects.filter(is_deleted=False).order_by('code')
    serializer_class = ProcessParameterSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['parameter_type', 'is_required']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['code', 'name', 'created_at']


class ProcessTemplateViewSet(viewsets.ModelViewSet):
    """工艺模板视图集"""
    queryset = ProcessTemplate.objects.filter(is_deleted=False).order_by('-updated_at')
    serializer_class = ProcessTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['code', 'name', 'created_at', 'updated_at']
    
    @action(detail=True, methods=['get'])
    def parameters(self, request, pk=None):
        """获取模板参数"""
        template = self.get_object()
        template_params = TemplateParameter.objects.filter(template=template).order_by('order')
        serializer = TemplateParameterSerializer(template_params, many=True)
        return Response(serializer.data)


class ProcessDataViewSet(viewsets.ModelViewSet):
    """工艺数据视图集"""
    queryset = ProcessData.objects.filter(is_deleted=False).order_by('-created_at')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['template']
    search_fields = ['code', 'name', 'batch_number', 'operator__username']
    ordering_fields = ['code', 'name', 'created_at', 'updated_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ProcessDataCreateSerializer
        return ProcessDataSerializer
    
    def perform_destroy(self, instance):
        """软删除"""
        instance.is_deleted = True
        instance.save()
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """高级搜索"""
        keyword = request.query_params.get('keyword', '')
        template_id = request.query_params.get('template_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = self.get_queryset()
        
        # 关键词搜索
        if keyword:
            queryset = queryset.filter(
                Q(code__icontains=keyword) |
                Q(name__icontains=keyword) |
                Q(batch_number__icontains=keyword) |
                Q(operator__username__icontains=keyword) |
                Q(remark__icontains=keyword)
            )
        
        # 按模板筛选
        if template_id:
            queryset = queryset.filter(template_id=template_id)
        
        # 按日期范围筛选
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# 复合材料加工相关视图集

class ToolViewSet(viewsets.ModelViewSet):
    """刀具视图集"""
    queryset = Tool.objects.filter(is_deleted=False).order_by('code')
    serializer_class = ToolSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # 使用自定义权限类
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tool_type', 'current_status']
    search_fields = ['code', 'tool_type', 'tool_spec', 'description']
    ordering_fields = ['code', 'tool_type', 'created_at']
    
    def perform_destroy(self, instance):
        """软删除"""
        instance.is_deleted = True
        instance.save()
    
    @action(detail=True, methods=['get'])
    def wear_records(self, request, pk=None):
        """获取刀具磨损记录"""
        tool = self.get_object()
        wear_records = ToolWearRecord.objects.filter(tool=tool).order_by('-record_time')
        page = self.paginate_queryset(wear_records)
        if page is not None:
            serializer = ToolWearRecordSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ToolWearRecordSerializer(wear_records, many=True)
        return Response(serializer.data)


class CompositeMaterialViewSet(viewsets.ModelViewSet):
    """复合材料构件视图集"""
    queryset = CompositeMaterial.objects.filter(is_deleted=False).order_by('part_number')
    serializer_class = CompositeMaterialSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['material_type']
    search_fields = ['part_number', 'description']
    ordering_fields = ['part_number', 'material_type', 'thickness']
    
    def perform_destroy(self, instance):
        """软删除"""
        instance.is_deleted = True
        instance.save()


class ProcessingTaskViewSet(viewsets.ModelViewSet):
    """加工任务视图集"""
    queryset = ProcessingTask.objects.filter(is_deleted=False).order_by('-processing_time')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['processing_type', 'status', 'tool', 'composite_material', 'group']
    search_fields = ['task_code', 'operator__username', 'notes']
    ordering_fields = ['processing_time', 'status']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProcessingTaskListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProcessingTaskCreateUpdateSerializer
        return ProcessingTaskDetailSerializer
    
    def perform_destroy(self, instance):
        """软删除"""
        instance.is_deleted = True
        instance.save()
    
    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """克隆一个加工任务及其所有关联参数"""
        original_task = self.get_object()
        
        # 复制任务主体
        cloned_task = original_task
        cloned_task.pk = None
        cloned_task.id = None
        cloned_task.task_code = f"{original_task.task_code} (复制)"
        cloned_task.status = 'planned' # 克隆出的任务默认为计划中
        cloned_task.save()
        
        # 复制关联的加工参数
        for param in original_task.parameters.all():
            param.pk = None
            param.id = None
            param.task = cloned_task
            param.save()
            
        serializer = self.get_serializer(cloned_task)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def parameters(self, request, pk=None):
        """获取加工任务参数"""
        task = self.get_object()
        parameters = ProcessingParameter.objects.filter(processing_task=task)
        serializer = ProcessingParameterSerializer(parameters, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def sensor_data(self, request, pk=None):
        """获取加工任务传感器数据"""
        task = self.get_object()
        sensor_data = SensorData.objects.filter(processing_task=task).order_by('upload_time')
        
        # 支持按传感器类型过滤
        sensor_type = request.query_params.get('sensor_type', None)
        if sensor_type:
            sensor_data = sensor_data.filter(sensor_type=sensor_type)
        
        # 支持时间范围过滤
        start_time = request.query_params.get('start_time', None)
        end_time = request.query_params.get('end_time', None)
        if start_time:
            sensor_data = sensor_data.filter(upload_time__gte=start_time)
        if end_time:
            sensor_data = sensor_data.filter(upload_time__lte=end_time)
        
        page = self.paginate_queryset(sensor_data)
        if page is not None:
            serializer = SensorDataSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SensorDataSerializer(sensor_data, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def quality(self, request, pk=None):
        """获取加工质量记录"""
        task = self.get_object()
        quality_records = ProcessingQuality.objects.filter(processing_task=task).order_by('-inspection_time')
        serializer = ProcessingQualitySerializer(quality_records, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def tool_wear(self, request, pk=None):
        """获取刀具磨损记录"""
        task = self.get_object()
        wear_records = ToolWearRecord.objects.filter(processing_task=task).order_by('-record_time')
        serializer = ToolWearRecordSerializer(wear_records, many=True)
        return Response(serializer.data)


class SensorDataViewSet(viewsets.ModelViewSet):
    """传感器数据视图集"""
    queryset = SensorData.objects.filter(is_deleted=False).order_by('-upload_time')
    serializer_class = SensorDataSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['sensor_type', 'processing_task']
    search_fields = ['sensor_id', 'processing_task__task_code', 'file_name']
    ordering_fields = ['upload_time', 'file_size']


class ProcessingQualityViewSet(viewsets.ModelViewSet):
    """加工质量视图集"""
    queryset = ProcessingQuality.objects.filter(is_deleted=False).order_by('-inspection_time')
    serializer_class = ProcessingQualitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['defect_type', 'processing_task']
    search_fields = ['inspector__username', 'processing_task__task_code']
    ordering_fields = ['inspection_time', 'surface_roughness', 'dimensional_tolerance']


class ToolWearRecordViewSet(viewsets.ModelViewSet):
    """刀具磨损记录视图集"""
    queryset = ToolWearRecord.objects.filter(is_deleted=False).order_by('-record_time')
    serializer_class = ToolWearRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tool', 'processing_task']
    search_fields = ['tool__code', 'processing_task__task_code']
    ordering_fields = ['record_time', 'wear_value']


@method_decorator(csrf_exempt, name='dispatch')
class UserInfoView(views.APIView):
    """
    获取当前登录用户信息的视图
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "用户未登录"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # 获取与用户关联的人员信息（如果有）
        personnel = None
        try:
            from .models import Personnel
            personnel_list = Personnel.objects.filter(name=user.username, is_deleted=False)
            if personnel_list.exists():
                personnel_obj = personnel_list.first()
                personnel = {
                    'id': personnel_obj.id,
                    'name': personnel_obj.name,
                    'employee_id': personnel_obj.employee_id,
                    'role': personnel_obj.role
                }
        except Exception as e:
            print(f"获取人员信息出错: {e}")

        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'personnel': personnel
        })

    def post(self, request, *args, **kwargs):
        """设置当前用户关联的人员"""
        if not request.user.is_authenticated:
            return Response({"error": "用户未登录"}, status=status.HTTP_401_UNAUTHORIZED)
        
        personnel_id = request.data.get('personnel_id')
        if not personnel_id:
            return Response({"error": "未提供人员ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from .models import Personnel
            personnel = Personnel.objects.get(id=personnel_id, is_deleted=False)
            
            # 更新用户信息
            user = request.user
            if not user.first_name:  # 如果用户没有设置名字，则使用人员名称
                user.first_name = personnel.name
                user.save()
                
            return Response({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'personnel': {
                    'id': personnel.id,
                    'name': personnel.name,
                    'employee_id': personnel.employee_id,
                    'role': personnel.role
                }
            })
        except Personnel.DoesNotExist:
            return Response({"error": "指定的人员不存在"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"设置人员关联失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TaskGroupViewSet(viewsets.ModelViewSet):
    """任务组视图集"""
    queryset = TaskGroup.objects.all().order_by('-created_at')
    serializer_class = TaskGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_queryset(self):
        # 普通用户只能看到自己创建的组
        if not self.request.user.is_staff:
            return self.queryset.filter(created_by=self.request.user)
        return self.queryset

    def perform_destroy(self, instance):
        # 检查组内是否有任务
        if instance.tasks.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError("无法删除：任务组内尚有关联的加工任务。")
        super().perform_destroy(instance)
