#!/usr/bin/env python3
# coding: utf-8
"""
性能测试脚本
测试API调用的响应时间
"""

import time
import requests
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'pyQTClient'))

from pyQTClient.app.api.api_client import ApiClient

# API 服务器的基础URL
API_BASE_URL = "http://127.0.0.1:8000/api"

def test_direct_requests():
    """测试直接使用requests的性能"""
    print("=== 测试直接requests调用 ===")
    
    session = requests.Session()
    
    # 测试多次调用
    times = []
    for i in range(5):
        start_time = time.time()
        response = session.get(f"{API_BASE_URL}/sensor-data/")
        end_time = time.time()
        
        duration = (end_time - start_time) * 1000  # 转换为毫秒
        times.append(duration)
        print(f"第{i+1}次调用: {duration:.2f}ms")
    
    avg_time = sum(times) / len(times)
    print(f"平均响应时间: {avg_time:.2f}ms")
    print()

def test_api_client():
    """测试优化后的ApiClient性能"""
    print("=== 测试优化后的ApiClient ===")
    
    client = ApiClient()
    
    # 先登录
    success, message = client.login("hedgehog", "123456")
    if not success:
        print(f"登录失败: {message}")
        return
    
    print("登录成功，开始测试API调用...")
    
    # 测试多次调用
    times = []
    for i in range(5):
        start_time = time.time()
        response = client.get_sensor_data()
        end_time = time.time()
        
        duration = (end_time - start_time) * 1000  # 转换为毫秒
        times.append(duration)
        print(f"第{i+1}次调用: {duration:.2f}ms")
    
    avg_time = sum(times) / len(times)
    print(f"平均响应时间: {avg_time:.2f}ms")
    print()

def test_batch_calls():
    """测试批量调用性能"""
    print("=== 测试批量API调用 ===")
    
    client = ApiClient()
    
    # 先登录
    success, message = client.login("hedgehog", "123456")
    if not success:
        print(f"登录失败: {message}")
        return
    
    print("测试批量调用（模拟看板刷新）...")
    
    start_time = time.time()
    
    # 模拟看板刷新的三个API调用
    users_data = client.get_users()
    tasks_data = client.get_processing_tasks()
    sensor_data = client.get_sensor_data()
    
    end_time = time.time()
    
    total_duration = (end_time - start_time) * 1000
    print(f"批量调用总耗时: {total_duration:.2f}ms")
    
    # 检查数据
    if users_data:
        print(f"用户数据: {users_data.get('count', 0)} 条")
    if tasks_data:
        print(f"任务数据: {tasks_data.get('count', 0)} 条")
    if sensor_data:
        print(f"传感器数据: {sensor_data.get('count', 0)} 条")
    print()

if __name__ == "__main__":
    print("开始性能测试...")
    print("请确保Django服务器正在运行在 http://127.0.0.1:8000")
    print()
    
    try:
        # 测试直接requests
        test_direct_requests()
        
        # 测试优化后的ApiClient
        test_api_client()
        
        # 测试批量调用
        test_batch_calls()
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        print("请确保Django服务器正在运行且可以访问") 