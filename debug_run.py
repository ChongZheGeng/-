#!/usr/bin/env python3
# coding: utf-8
"""
调试启动脚本
用于调试程序启动时的问题
"""

import sys
import os
import traceback
import logging

# 设置详细的日志记录
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_startup.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info("=== 开始调试启动 ===")
    
    try:
        # 检查Python版本
        logger.info(f"Python版本: {sys.version}")
        logger.info(f"当前工作目录: {os.getcwd()}")
        
        # 检查PyQt5是否可用
        logger.info("检查PyQt5...")
        try:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtCore import Qt
            logger.info("PyQt5导入成功")
        except ImportError as e:
            logger.error(f"PyQt5导入失败: {e}")
            return
        
        # 检查qfluentwidgets是否可用
        logger.info("检查qfluentwidgets...")
        try:
            from qfluentwidgets import FluentWindow
            logger.info("qfluentwidgets导入成功")
        except ImportError as e:
            logger.error(f"qfluentwidgets导入失败: {e}")
            return
        
        # 添加项目路径
        project_path = os.path.join(os.path.dirname(__file__), 'pyQTClient')
        if project_path not in sys.path:
            sys.path.insert(0, project_path)
            logger.info(f"添加项目路径: {project_path}")
        
        # 检查项目模块
        logger.info("检查项目模块...")
        try:
            from app.api.api_client import ApiClient
            logger.info("API客户端模块导入成功")
        except ImportError as e:
            logger.error(f"API客户端模块导入失败: {e}")
            return
        
        try:
            from app.api.async_api import async_api
            logger.info("异步API模块导入成功")
        except ImportError as e:
            logger.warning(f"异步API模块导入失败: {e}")
        
        # 尝试启动主程序
        logger.info("启动主程序...")
        
        # 导入并运行主程序
        os.chdir(os.path.dirname(__file__))
        exec(open('pyQTClient/demo.py', encoding='utf-8').read())
        
    except Exception as e:
        error_msg = f"启动失败: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        print(f"\n[CRITICAL ERROR] {error_msg}")
        
        # 保存错误信息
        with open('critical_error.log', 'w', encoding='utf-8') as f:
            f.write(error_msg)
        
        input("按回车键退出...")

if __name__ == '__main__':
    main() 