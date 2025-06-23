from django.contrib import admin
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
    ToolWearRecord
)


class TemplateParameterInline(admin.TabularInline):
    model = TemplateParameter
    extra = 1


class ParameterValueInline(admin.TabularInline):
    model = ParameterValue
    extra = 1


@admin.register(ProcessCategory)
class ProcessCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'parent', 'created_at')
    search_fields = ('name', 'code')
    list_filter = ('created_at',)


@admin.register(ProcessTemplate)
class ProcessTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'version', 'category', 'is_active', 'created_at')
    search_fields = ('name', 'code')
    list_filter = ('category', 'is_active', 'created_at')
    inlines = [TemplateParameterInline]


@admin.register(ProcessData)
class ProcessDataAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'template', 'batch_number', 'operator', 'created_at')
    search_fields = ('code', 'name', 'batch_number', 'operator')
    list_filter = ('template', 'created_at')
    inlines = [ParameterValueInline]


@admin.register(ParameterValue)
class ParameterValueAdmin(admin.ModelAdmin):
    list_display = ('process_data', 'parameter', 'value', 'created_at')
    search_fields = ('process_data__code', 'process_data__name', 'parameter__name')
    list_filter = ('parameter', 'created_at')


# 复合材料加工相关管理类

class ProcessingParameterInline(admin.TabularInline):
    model = ProcessingParameter
    extra = 1


class SensorDataInline(admin.TabularInline):
    model = SensorData
    extra = 1
    max_num = 10


class ProcessingQualityInline(admin.TabularInline):
    model = ProcessingQuality
    extra = 1


class ToolWearRecordInline(admin.TabularInline):
    model = ToolWearRecord
    extra = 1


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ('code', 'tool_type', 'tool_spec', 'initial_wear_threshold', 'current_status')
    search_fields = ('code', 'tool_type', 'tool_spec')
    list_filter = ('tool_type', 'current_status')


@admin.register(CompositeMaterial)
class CompositeMaterialAdmin(admin.ModelAdmin):
    list_display = ('part_number', 'material_type', 'thickness')
    search_fields = ('part_number', 'description')
    list_filter = ('material_type',)


@admin.register(ProcessingTask)
class ProcessingTaskAdmin(admin.ModelAdmin):
    list_display = ('task_code', 'processing_type', 'status', 'tool', 'composite_material', 
                   'processing_time', 'operator')
    search_fields = ('task_code', 'operator', 'notes')
    list_filter = ('processing_type', 'status', 'processing_time')
    inlines = [ProcessingParameterInline, ProcessingQualityInline, ToolWearRecordInline]
    date_hierarchy = 'processing_time'


@admin.register(ProcessingParameter)
class ProcessingParameterAdmin(admin.ModelAdmin):
    list_display = ('task', 'parameter_name', 'parameter_value', 'unit', 'created_at')
    search_fields = ('task__task_code', 'parameter_name')
    list_filter = ('created_at',)


@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ('processing_task', 'sensor_type', 'timestamp', 'value', 'unit')
    search_fields = ('processing_task__task_code', 'sensor_id')
    list_filter = ('sensor_type', 'timestamp')
    date_hierarchy = 'timestamp'


@admin.register(ProcessingQuality)
class ProcessingQualityAdmin(admin.ModelAdmin):
    list_display = ('processing_task', 'surface_roughness', 'dimensional_tolerance', 
                   'defect_type', 'inspection_time', 'inspector')
    search_fields = ('processing_task__task_code', 'inspector')
    list_filter = ('defect_type', 'inspection_time')
    date_hierarchy = 'inspection_time'


@admin.register(ToolWearRecord)
class ToolWearRecordAdmin(admin.ModelAdmin):
    list_display = ('tool', 'processing_task', 'wear_value', 'record_time')
    search_fields = ('tool__code', 'processing_task__task_code')
    list_filter = ('record_time',)
    date_hierarchy = 'record_time'
