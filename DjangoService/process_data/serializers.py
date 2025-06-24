from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    ProcessCategory,
    ProcessParameter,
    ProcessTemplate,
    TemplateParameter,
    ProcessData,
    ParameterValue,
    # Personnel 已移除
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


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'is_active', 'is_staff', 'is_superuser']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class UserCreateUpdateSerializer(serializers.ModelSerializer):
    """用于创建和更新用户的序列化器"""
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'email', 'is_active', 'is_staff']

    def create(self, validated_data):
        """创建用户并哈希密码"""
        user = User.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        """更新用户信息，并处理密码"""
        password = validated_data.pop('password', None)
        
        # 调用父类的update方法更新其他字段
        instance = super().update(instance, validated_data)

        if password:
            instance.set_password(password)
            instance.save()
            
        return instance


class ProcessCategorySerializer(serializers.ModelSerializer):
    """工艺分类序列化器"""
    class Meta:
        model = ProcessCategory
        fields = '__all__'


class ProcessParameterSerializer(serializers.ModelSerializer):
    """工艺参数序列化器"""
    class Meta:
        model = ProcessParameter
        fields = '__all__'


class TemplateParameterSerializer(serializers.ModelSerializer):
    """模板参数关联序列化器"""
    parameter_info = ProcessParameterSerializer(source='parameter', read_only=True)
    
    class Meta:
        model = TemplateParameter
        fields = ['id', 'template', 'parameter', 'parameter_info', 'order', 
                  'is_required', 'default_value', 'created_at', 'updated_at']


class ProcessTemplateSerializer(serializers.ModelSerializer):
    """工艺模板序列化器"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    template_parameters = TemplateParameterSerializer(
        source='templateparameter_set', many=True, read_only=True
    )
    
    class Meta:
        model = ProcessTemplate
        fields = ['id', 'name', 'code', 'description', 'category', 'category_name',
                 'version', 'is_active', 'created_at', 'updated_at', 'template_parameters']


class ParameterValueSerializer(serializers.ModelSerializer):
    """参数值序列化器"""
    parameter_name = serializers.CharField(source='parameter.name', read_only=True)
    parameter_code = serializers.CharField(source='parameter.code', read_only=True)
    parameter_type = serializers.CharField(source='parameter.parameter_type', read_only=True)
    parameter_unit = serializers.CharField(source='parameter.unit', read_only=True)
    
    class Meta:
        model = ParameterValue
        fields = ['id', 'process_data', 'parameter', 'parameter_name', 'parameter_code', 
                 'parameter_type', 'parameter_unit', 'value', 'created_at', 'updated_at']


class ProcessDataSerializer(serializers.ModelSerializer):
    """工艺数据记录序列化器"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    parameter_values = ParameterValueSerializer(
        source='parameter_values', many=True, read_only=True
    )
    operator_info = UserSerializer(source='operator', read_only=True)
    operator_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessData
        fields = ['id', 'template', 'template_name', 'code', 'name', 'batch_number', 
                 'operator', 'operator_info', 'operator_name', 'remark', 'created_at', 'updated_at', 'parameter_values']
    
    def get_operator_name(self, obj):
        if obj.operator:
            return obj.operator.get_full_name() or obj.operator.username
        return None


class ProcessDataCreateSerializer(serializers.ModelSerializer):
    """创建工艺数据的序列化器"""
    parameter_values = serializers.DictField(child=serializers.CharField(), write_only=True)
    
    class Meta:
        model = ProcessData
        fields = ['template', 'code', 'name', 'batch_number', 'operator', 
                 'remark', 'parameter_values']
    
    def create(self, validated_data):
        # 提取参数值数据并移除
        parameter_values_data = validated_data.pop('parameter_values', {})
        
        # 创建工艺数据记录
        process_data = ProcessData.objects.create(**validated_data)
        
        # 获取模板关联的参数
        template = validated_data.get('template')
        template_parameters = TemplateParameter.objects.filter(template=template)
        
        # 创建参数值记录
        for template_param in template_parameters:
            param_code = template_param.parameter.code
            if param_code in parameter_values_data:
                ParameterValue.objects.create(
                    process_data=process_data,
                    parameter=template_param.parameter,
                    value=parameter_values_data[param_code]
                )
        
        return process_data


# 复合材料加工相关序列化器

class ToolSerializer(serializers.ModelSerializer):
    """刀具序列化器"""
    class Meta:
        model = Tool
        fields = '__all__'


class CompositeMaterialSerializer(serializers.ModelSerializer):
    """复合材料构件序列化器"""
    material_type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    
    class Meta:
        model = CompositeMaterial
        fields = '__all__'


class ProcessingParameterSerializer(serializers.ModelSerializer):
    """加工参数序列化器"""
    class Meta:
        model = ProcessingParameter
        exclude = ['task']


class SensorDataSerializer(serializers.ModelSerializer):
    """传感器数据序列化器"""
    sensor_type_display = serializers.CharField(source='get_sensor_type_display', read_only=True)
    processing_task_code = serializers.CharField(source='processing_task.task_code', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = SensorData
        fields = '__all__'
    
    def get_file_size_mb(self, obj):
        """将文件大小转换为MB"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return None


class SensorDataCreateSerializer(serializers.ModelSerializer):
    """创建传感器数据的序列化器"""
    
    class Meta:
        model = SensorData
        fields = ['sensor_type', 'file_name', 'file_url', 'file_size', 
                 'processing_task', 'sensor_id', 'description']


class ProcessingQualitySerializer(serializers.ModelSerializer):
    """加工质量序列化器"""
    defect_type_display = serializers.CharField(source='get_defect_type_display', read_only=True)
    inspector_info = UserSerializer(source='inspector', read_only=True)
    inspector_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessingQuality
        fields = [
            'id', 'surface_roughness', 'dimensional_tolerance', 'defect_type',
            'defect_type_display', 'inspection_time', 'processing_task',
            'inspector', 'inspector_info', 'inspector_name', 'images', 'remarks',
            'created_at', 'updated_at'
        ]
    
    def get_inspector_name(self, obj):
        if obj.inspector:
            return obj.inspector.get_full_name() or obj.inspector.username
        return None


class ToolWearRecordSerializer(serializers.ModelSerializer):
    """刀具磨损记录序列化器"""
    tool_code = serializers.CharField(source='tool.code', read_only=True)
    
    class Meta:
        model = ToolWearRecord
        fields = '__all__'


class TaskGroupSerializer(serializers.ModelSerializer):
    """任务组序列化器"""
    created_by = UserSerializer(read_only=True)
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = TaskGroup
        fields = ['id', 'name', 'description', 'created_by', 'created_at', 'task_count']

    def get_task_count(self, obj):
        return obj.tasks.count()

    def create(self, validated_data):
        # 自动设置创建者
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ProcessingTaskListSerializer(serializers.ModelSerializer):
    """加工任务列表序列化器 - 使用嵌套序列化器返回完整对象"""
    tool_info = ToolSerializer(source='tool', read_only=True)
    material_info = CompositeMaterialSerializer(source='composite_material', read_only=True)
    operator_info = UserSerializer(source='operator', read_only=True)
    parameters = ProcessingParameterSerializer(many=True, read_only=True)
    processing_type_display = serializers.CharField(source='get_processing_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    group_name = serializers.SerializerMethodField()

    class Meta:
        model = ProcessingTask
        fields = [
            'id', 'task_code', 'processing_type', 'processing_type_display', 
            'status', 'status_display', 'tool', 'tool_info', 
            'composite_material', 'material_info', 'operator', 'operator_info', 
            'processing_time', 'duration', 'notes', 'parameters',
            'group', 'group_name'
        ]
        
    def get_group_name(self, obj):
        if obj.group:
            return obj.group.name
        return "未分配"


class ProcessingTaskDetailSerializer(serializers.ModelSerializer):
    """加工任务详情序列化器"""
    tool = ToolSerializer(read_only=True)
    composite_material = CompositeMaterialSerializer(read_only=True)
    operator = UserSerializer(read_only=True)
    parameters = ProcessingParameterSerializer(source='processingparameter_set', many=True, read_only=True)
    sensor_data = SensorDataSerializer(many=True, read_only=True)
    quality_records = ProcessingQualitySerializer(source='processingquality_set', many=True, read_only=True)
    tool_wear_records = ToolWearRecordSerializer(source='toolwearrecord_set', many=True, read_only=True)
    processing_type_display = serializers.CharField(source='get_processing_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ProcessingTask
        fields = '__all__'


class ProcessingTaskCreateUpdateSerializer(serializers.ModelSerializer):
    """创建和更新加工任务的序列化器"""
    parameters = ProcessingParameterSerializer(many=True, required=False)

    class Meta:
        model = ProcessingTask
        fields = [
            'task_code', 'processing_time', 'processing_type', 'tool',
            'composite_material', 'status', 'duration', 'operator',
            'notes', 'parameters', 'group'
        ]

    def create(self, validated_data):
        """创建任务并关联参数"""
        parameters_data = validated_data.pop('parameters', [])
        task = ProcessingTask.objects.create(**validated_data)
        for param_data in parameters_data:
            ProcessingParameter.objects.create(task=task, **param_data)
        return task

    def update(self, instance, validated_data):
        """更新任务并同步参数"""
        parameters_data = validated_data.pop('parameters', None)
        
        # 更新任务实例本身
        instance = super().update(instance, validated_data)

        # 如果提交了参数数据，则进行同步
        if parameters_data is not None:
            # 先删除旧的参数
            instance.parameters.all().delete()
            # 再创建新的参数
            for param_data in parameters_data:
                ProcessingParameter.objects.create(task=instance, **param_data)
        
        return instance 