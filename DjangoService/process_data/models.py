from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class BaseModel(models.Model):
    """基础模型，提供共有字段"""
    created_at = models.DateTimeField('创建时间', default=timezone.now)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    is_deleted = models.BooleanField('是否删除', default=False)
    
    class Meta:
        abstract = True


class ProcessCategory(BaseModel):
    """工艺分类"""
    name = models.CharField('分类名称', max_length=100)
    code = models.CharField('分类编码', max_length=50, unique=True)
    description = models.TextField('描述', blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, verbose_name='父分类', 
                               blank=True, null=True, related_name='children')
    
    class Meta:
        verbose_name = '工艺分类'
        verbose_name_plural = verbose_name
        ordering = ['code']
    
    def __str__(self):
        return self.name


class ProcessParameter(BaseModel):
    """工艺参数定义"""
    PARAMETER_TYPES = (
        ('number', '数值型'),
        ('text', '文本型'),
        ('boolean', '布尔型'),
        ('date', '日期型'),
        ('enum', '枚举型'),
    )
    
    name = models.CharField('参数名称', max_length=100)
    code = models.CharField('参数编码', max_length=50, unique=True)
    description = models.TextField('描述', blank=True, null=True)
    unit = models.CharField('单位', max_length=50, blank=True, null=True)
    parameter_type = models.CharField('参数类型', max_length=20, choices=PARAMETER_TYPES)
    enum_values = models.TextField('枚举值', blank=True, null=True, 
                                  help_text='枚举类型的可选值，用逗号分隔')
    default_value = models.CharField('默认值', max_length=255, blank=True, null=True)
    min_value = models.FloatField('最小值', blank=True, null=True)
    max_value = models.FloatField('最大值', blank=True, null=True)
    is_required = models.BooleanField('是否必填', default=False)
    
    class Meta:
        verbose_name = '工艺参数'
        verbose_name_plural = verbose_name
        ordering = ['code']
    
    def __str__(self):
        return f"{self.name}({self.code})"


class ProcessTemplate(BaseModel):
    """工艺模板"""
    name = models.CharField('模板名称', max_length=100)
    code = models.CharField('模板编码', max_length=50, unique=True)
    description = models.TextField('描述', blank=True, null=True)
    category = models.ForeignKey(ProcessCategory, on_delete=models.CASCADE, 
                                verbose_name='所属分类', related_name='templates')
    parameters = models.ManyToManyField(ProcessParameter, through='TemplateParameter',
                                      verbose_name='工艺参数')
    version = models.CharField('版本号', max_length=20, default='1.0.0')
    is_active = models.BooleanField('是否启用', default=True)
    
    class Meta:
        verbose_name = '工艺模板'
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} v{self.version}"


class TemplateParameter(BaseModel):
    """模板参数关联表"""
    template = models.ForeignKey(ProcessTemplate, on_delete=models.CASCADE, 
                               verbose_name='工艺模板')
    parameter = models.ForeignKey(ProcessParameter, on_delete=models.CASCADE, 
                                verbose_name='工艺参数')
    order = models.IntegerField('排序', default=0)
    is_required = models.BooleanField('是否必填', default=False)
    default_value = models.CharField('默认值', max_length=255, blank=True, null=True)
    
    class Meta:
        verbose_name = '模板参数'
        verbose_name_plural = verbose_name
        ordering = ['order']
        unique_together = ['template', 'parameter']
    
    def __str__(self):
        return f"{self.template.name} - {self.parameter.name}"


class ProcessData(BaseModel):
    """工艺数据记录"""
    template = models.ForeignKey(ProcessTemplate, on_delete=models.CASCADE, 
                               verbose_name='工艺模板', related_name='data_records')
    code = models.CharField('数据编码', max_length=100, unique=True)
    name = models.CharField('数据名称', max_length=100)
    batch_number = models.CharField('批次号', max_length=100)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='操作员')
    remark = models.TextField('备注', blank=True, null=True)
    
    class Meta:
        verbose_name = '工艺数据'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class ParameterValue(BaseModel):
    """参数值记录"""
    process_data = models.ForeignKey(ProcessData, on_delete=models.CASCADE, 
                                   verbose_name='工艺数据', related_name='parameter_values')
    parameter = models.ForeignKey(ProcessParameter, on_delete=models.CASCADE, 
                                verbose_name='工艺参数')
    value = models.TextField('参数值')
    
    class Meta:
        verbose_name = '参数值'
        verbose_name_plural = verbose_name
        unique_together = ['process_data', 'parameter']
    
    def __str__(self):
        return f"{self.process_data.code} - {self.parameter.name}: {self.value}"


# --------- 复合材料加工相关模型 ---------

class Tool(BaseModel):
    """刀具"""
    TOOL_STATUS_CHOICES = (
        ('normal', '正常'),
        ('warning', '警告'),
        ('worn', '已磨损'),
        ('broken', '损坏'),
        ('maintenance', '维护中'),
    )
    
    tool_type = models.CharField('刀具类型', max_length=50)
    tool_spec = models.CharField('刀具规格', max_length=100)
    initial_wear_threshold = models.FloatField('初始磨损阈值')
    current_status = models.CharField('当前状态', max_length=20, choices=TOOL_STATUS_CHOICES, default='normal')
    code = models.CharField('刀具编码', max_length=50, unique=True)
    description = models.TextField('描述', blank=True, null=True)
    
    class Meta:
        verbose_name = '刀具'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.code} - {self.tool_type} ({self.tool_spec})"


class CompositeMaterial(BaseModel):
    """复合材料构件"""
    MATERIAL_TYPE_CHOICES = (
        ('carbon_fiber', '碳纤维'),
        ('glass_fiber', '玻璃纤维'),
        ('aramid', '芳纶'),
        ('hybrid', '混合材料'),
        ('other', '其他'),
    )
    
    part_number = models.CharField('构件编号', max_length=50, unique=True)
    material_type = models.CharField('材料类型', max_length=30, choices=MATERIAL_TYPE_CHOICES)
    thickness = models.FloatField('厚度(mm)')
    processing_requirements = models.TextField('加工要求')
    description = models.TextField('描述', blank=True, null=True)
    
    class Meta:
        verbose_name = '复合材料构件'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.part_number} - {self.get_material_type_display()}"


class ProcessingTask(BaseModel):
    """加工任务"""
    TASK_TYPE_CHOICES = (
        ('drilling', '钻孔'),
        ('milling', '铣削'),
        ('cutting', '切割'),
        ('trimming', '修边'),
        ('other', '其他'),
    )
    
    TASK_STATUS_CHOICES = (
        ('planned', '计划中'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('paused', '已暂停'),
        ('aborted', '已中止'),
    )
    
    processing_time = models.DateTimeField('加工时间')
    processing_type = models.CharField('加工类型', max_length=20, choices=TASK_TYPE_CHOICES)
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE, verbose_name='刀具')
    composite_material = models.ForeignKey(CompositeMaterial, on_delete=models.CASCADE, verbose_name='复合材料构件')
    task_code = models.CharField('任务编码', max_length=50, unique=True)
    status = models.CharField('任务状态', max_length=20, choices=TASK_STATUS_CHOICES, default='planned')
    duration = models.IntegerField('预计持续时间(分钟)', null=True, blank=True)
    actual_duration = models.IntegerField('实际持续时间(分钟)', null=True, blank=True)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='操作员')
    notes = models.TextField('备注', blank=True, null=True)
    group = models.ForeignKey('TaskGroup', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='tasks', verbose_name="所属任务组")
    
    class Meta:
        verbose_name = '加工任务'
        verbose_name_plural = verbose_name
        ordering = ['-processing_time']
    
    def __str__(self):
        return f"{self.task_code} - {self.get_processing_type_display()} ({self.get_status_display()})"


class ProcessingParameter(models.Model):
    """加工参数模型"""
    task = models.ForeignKey(ProcessingTask, on_delete=models.CASCADE, related_name='parameters', verbose_name="关联任务")
    parameter_name = models.CharField(max_length=100, verbose_name="参数名称")
    parameter_value = models.CharField(max_length=100, verbose_name="参数值")
    unit = models.CharField(max_length=50, blank=True, null=True, verbose_name="单位")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    def __str__(self):
        return f"{self.parameter_name}: {self.parameter_value} {self.unit or ''}"

    class Meta:
        verbose_name = "加工参数"
        verbose_name_plural = verbose_name
        ordering = ['created_at']


class SensorData(BaseModel):
    """传感器数据模型"""
    SENSOR_TYPE_CHOICES = (
        ('temperature', '温度'),
        ('vibration', '振动'),
        ('force', '力'),
        ('acoustic', '声学'),
        ('current', '电流'),
        ('other', '其他'),
    )
    
    sensor_type = models.CharField('传感器类型', max_length=20, choices=SENSOR_TYPE_CHOICES)
    timestamp = models.DateTimeField('时间戳')
    value = models.FloatField('数值')
    processing_task = models.ForeignKey(ProcessingTask, on_delete=models.CASCADE, 
                                       verbose_name='加工任务', related_name='sensor_data')
    unit = models.CharField('单位', max_length=20, blank=True, null=True)
    sensor_id = models.CharField('传感器ID', max_length=50, blank=True, null=True)
    
    class Meta:
        verbose_name = '传感器数据'
        verbose_name_plural = verbose_name
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.get_sensor_type_display()} - {self.timestamp}"


class ProcessingQuality(BaseModel):
    """加工质量"""
    DEFECT_TYPE_CHOICES = (
        ('none', '无缺陷'),
        ('delamination', '分层'),
        ('fiber_breakage', '纤维断裂'),
        ('matrix_cracking', '基体开裂'),
        ('burr', '毛刺'),
        ('surface_roughness', '表面粗糙度不合格'),
        ('dimensional', '尺寸超差'),
        ('other', '其他'),
    )
    
    surface_roughness = models.FloatField('表面粗糙度(Ra)')
    dimensional_tolerance = models.FloatField('尺寸公差(mm)')
    defect_type = models.CharField('缺陷类型', max_length=30, choices=DEFECT_TYPE_CHOICES, default='none')
    inspection_time = models.DateTimeField('检测时间')
    processing_task = models.ForeignKey(ProcessingTask, on_delete=models.CASCADE, 
                                      verbose_name='加工任务', related_name='quality_records')
    inspector = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='检验员')
    images = models.TextField('图像路径', blank=True, null=True)
    remarks = models.TextField('备注', blank=True, null=True)
    
    class Meta:
        verbose_name = '加工质量'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"质量 - {self.processing_task.task_code} ({self.inspection_time})"


class ToolWearRecord(BaseModel):
    """刀具磨损记录"""
    wear_value = models.FloatField('磨损值')
    record_time = models.DateTimeField('记录时间')
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE, 
                           verbose_name='刀具', related_name='wear_records')
    processing_task = models.ForeignKey(ProcessingTask, on_delete=models.CASCADE, 
                                      verbose_name='加工任务', related_name='tool_wear_records')
    measurement_method = models.CharField('测量方法', max_length=50, blank=True, null=True)
    position = models.CharField('测量位置', max_length=50, blank=True, null=True)
    images = models.TextField('图像路径', blank=True, null=True)
    
    class Meta:
        verbose_name = '刀具磨损记录'
        verbose_name_plural = verbose_name
        ordering = ['-record_time']
    
    def __str__(self):
        return f"磨损 - {self.tool.code} ({self.record_time})"


class TaskGroup(BaseModel):
    """加工任务组模型"""
    name = models.CharField(max_length=200, unique=True, verbose_name="组名称")
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                 related_name='task_groups', verbose_name="创建者")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "加工任务组"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
