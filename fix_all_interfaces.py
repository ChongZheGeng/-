#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量修复所有界面的print语句和异步回调安全问题
"""

import os
import re

def fix_interface_file(file_path):
    """修复单个界面文件"""
    print(f"正在修复: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 1. 添加logging导入（如果还没有的话）
    if 'import logging' not in content:
        # 在api_client导入后添加logging
        content = re.sub(
            r'(from \.\.api\.api_client import api_client\n)',
            r'\1import logging\n\n# 设置logger\nlogger = logging.getLogger(__name__)\n\n',
            content
        )
    
    # 2. 修复print语句
    print_patterns = [
        (r'print\(f"\[DEBUG\] ([^"]+)"\)', r'logger.debug(f"\1")'),
        (r'print\(f"\[ERROR\] ([^"]+)"\)', r'logger.error(f"\1")'),
        (r'print\(f"\[WARNING\] ([^"]+)"\)', r'logger.warning(f"\1")'),
        (r'print\(f"\[INFO\] ([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\("\[DEBUG\] ([^"]+)"\)', r'logger.debug("\1")'),
        (r'print\("\[ERROR\] ([^"]+)"\)', r'logger.error("\1")'),
        (r'print\("\[WARNING\] ([^"]+)"\)', r'logger.warning("\1")'),
        (r'print\("\[INFO\] ([^"]+)"\)', r'logger.info("\1")'),
    ]
    
    for pattern, replacement in print_patterns:
        content = re.sub(pattern, replacement, content)
    
    # 3. 添加异步API安全导入（如果还没有的话）
    if 'ASYNC_API_AVAILABLE' not in content and 'async_api' in content:
        # 替换简单的async_api导入
        content = re.sub(
            r'from \.\.api\.async_api import async_api\n',
            '''# 安全导入异步API
try:
    from ..api.async_api import async_api
    ASYNC_API_AVAILABLE = True
    logger.debug("异步API模块导入成功")
except ImportError as e:
    logger.warning(f"异步API模块导入失败: {e}")
    async_api = None
    ASYNC_API_AVAILABLE = False

''',
            content
        )
    
    # 4. 修复异步调用方法，添加安全检查
    async_methods = [
        'get_users_async',
        'get_processing_tasks_async', 
        'get_sensor_data_async',
        'get_tools_async',
        'get_composite_materials_async',
        'get_task_groups_async'
    ]
    
    for method in async_methods:
        # 查找调用这个方法的地方
        pattern = rf'(\s+)async_api\.{method}\(\s*\n?\s*success_callback=([^,]+),\s*\n?\s*error_callback=([^)]+)\s*\)'
        
        def replace_async_call(match):
            indent = match.group(1)
            success_cb = match.group(2)
            error_cb = match.group(3)
            
            return f'''{indent}if ASYNC_API_AVAILABLE and async_api:
{indent}    async_api.{method}(
{indent}        success_callback={success_cb},
{indent}        error_callback={error_cb}
{indent}    )
{indent}else:
{indent}    logger.warning("异步API不可用，回退到同步加载")
{indent}    try:
{indent}        response_data = api_client.{method.replace('_async', '')}()
{indent}        {success_cb}(response_data)
{indent}    except Exception as e:
{indent}        {error_cb}(str(e))'''
        
        content = re.sub(pattern, replace_async_call, content, flags=re.MULTILINE)
    
    # 5. 修复回调函数，添加界面存在性检查
    callback_patterns = [
        (r'def (on_\w+_data_received)\(self, ([^)]+)\):\s*\n(\s+)"""([^"]+)"""\s*\n(\s+)if ([^:]+):', 
         r'def \1(self, \2):\n\3"""\4"""\n\3try:\n\3    if not self or not hasattr(self, \'table\') or not self.table:\n\3        logger.warning("\4回调时界面已销毁")\n\3        return\n\3        \n\3    if \6:'),
        
        (r'def (on_\w+_error)\(self, ([^)]+)\):\s*\n(\s+)"""([^"]+)"""\s*\n(\s+)print\(f"\[ERROR\] ([^"]+)"\)',
         r'def \1(self, \2):\n\3"""\4"""\n\3try:\n\3    logger.error(f"\6")\n\3    if self and hasattr(self, \'parent\') and self.parent():'),
    ]
    
    for pattern, replacement in callback_patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # 只有内容发生变化才写入文件
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 已修复: {file_path}")
        return True
    else:
        print(f"⏩ 跳过: {file_path} (无需修复)")
        return False

def main():
    """主函数"""
    base_dir = os.path.join(os.path.dirname(__file__), 'pyQTClient', 'app', 'view')
    
    interface_files = [
        'user_interface.py',
        'tool_interface.py',
        'task_group_interface.py',
        'sensor_data_interface.py',
        'composite_material_interface.py'
    ]
    
    fixed_count = 0
    
    for file_name in interface_files:
        file_path = os.path.join(base_dir, file_name)
        if os.path.exists(file_path):
            if fix_interface_file(file_path):
                fixed_count += 1
        else:
            print(f"❌ 文件不存在: {file_path}")
    
    print(f"\n修复完成! 共修复了 {fixed_count} 个文件")

if __name__ == '__main__':
    main() 