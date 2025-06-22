from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth.models import User

from .models import (
    ProcessCategory,
    ProcessParameter,
    ProcessTemplate,
    TemplateParameter,
    ProcessData,
    ParameterValue,
)


class ProcessCategoryTests(TestCase):
    """测试工艺分类"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpassword'
        )
        self.client.force_authenticate(user=self.user)
        
        # 创建测试数据
        self.category = ProcessCategory.objects.create(
            name='测试分类',
            code='TEST001'
        )
    
    def test_create_category(self):
        """测试创建分类"""
        url = reverse('processcategory-list')
        data = {
            'name': '新分类',
            'code': 'NEW001',
            'description': '这是一个新分类'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProcessCategory.objects.count(), 2)
    
    def test_get_categories(self):
        """测试获取分类列表"""
        url = reverse('processcategory-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class ProcessTemplateTests(TestCase):
    """测试工艺模板"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpassword'
        )
        self.client.force_authenticate(user=self.user)
        
        # 创建测试数据
        self.category = ProcessCategory.objects.create(
            name='测试分类',
            code='TEST001'
        )
        
        self.parameter = ProcessParameter.objects.create(
            name='测试参数',
            code='PARAM001',
            parameter_type='number',
            unit='kg'
        )
        
        self.template = ProcessTemplate.objects.create(
            name='测试模板',
            code='TEMPLATE001',
            category=self.category
        )
        
        self.template_parameter = TemplateParameter.objects.create(
            template=self.template,
            parameter=self.parameter,
            order=1
        )
    
    def test_get_template(self):
        """测试获取模板"""
        url = reverse('processtemplate-detail', args=[self.template.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], '测试模板')
    
    def test_get_template_parameters(self):
        """测试获取模板参数"""
        url = reverse('processtemplate-parameters', args=[self.template.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class ProcessDataTests(TestCase):
    """测试工艺数据"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpassword'
        )
        self.client.force_authenticate(user=self.user)
        
        # 创建测试数据
        self.category = ProcessCategory.objects.create(
            name='测试分类',
            code='TEST001'
        )
        
        self.parameter = ProcessParameter.objects.create(
            name='测试参数',
            code='PARAM001',
            parameter_type='number',
            unit='kg'
        )
        
        self.template = ProcessTemplate.objects.create(
            name='测试模板',
            code='TEMPLATE001',
            category=self.category
        )
        
        self.template_parameter = TemplateParameter.objects.create(
            template=self.template,
            parameter=self.parameter,
            order=1
        )
    
    def test_create_process_data(self):
        """测试创建工艺数据"""
        url = reverse('processdata-list')
        data = {
            'template': self.template.id,
            'code': 'DATA001',
            'name': '测试数据',
            'batch_number': 'BATCH001',
            'operator': '测试员',
            'parameter_values': {
                'PARAM001': '100'
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProcessData.objects.count(), 1)
        
        # 验证参数值是否创建
        process_data = ProcessData.objects.first()
        self.assertEqual(ParameterValue.objects.filter(process_data=process_data).count(), 1)
