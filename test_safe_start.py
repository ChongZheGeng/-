#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全启动测试脚本
用于测试修复后的程序是否还会闪退
"""

import sys
import os
import logging
import traceback
from datetime import datetime

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
pyqt_dir = os.path.join(current_dir, 'pyQTClient')
sys.path.insert(0, pyqt_dir)

def setup_logging():
    """设置详细的日志记录"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 创建日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f'test_safe_start_{timestamp}.log'
    
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"测试日志将保存到: {log_file}")
    return logger

def test_imports():
    """测试关键模块导入"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("开始测试模块导入...")
        
        # 测试PyQt5
        logger.debug("导入PyQt5...")
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        logger.debug("PyQt5导入成功")
        
        # 测试qfluentwidgets
        logger.debug("导入qfluentwidgets...")
        from qfluentwidgets import FluentWindow
        logger.debug("qfluentwidgets导入成功")
        
        # 测试应用模块
        logger.debug("导入应用模块...")
        from app.api.api_client import api_client
        logger.debug("api_client导入成功")
        
        from app.api.async_api import async_api
        logger.debug("async_api导入成功")
        
        from app.view.dashboard_interface import DashboardInterface
        logger.debug("dashboard_interface导入成功")
        
        logger.info("所有模块导入测试通过")
        return True
        
    except Exception as e:
        logger.error(f"模块导入失败: {e}")
        logger.error(traceback.format_exc())
        return False

def test_basic_functionality():
    """测试基本功能"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("开始测试基本功能...")
        
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt, QTimer
        
        # 创建应用
        app = QApplication([])
        app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
        
        logger.debug("创建看板界面...")
        from app.view.dashboard_interface import DashboardInterface
        dashboard = DashboardInterface()
        
        logger.debug("测试界面初始化...")
        if hasattr(dashboard, 'user_card') and dashboard.user_card:
            logger.debug("用户卡片初始化成功")
        else:
            logger.warning("用户卡片初始化失败")
            
        if hasattr(dashboard, 'task_card') and dashboard.task_card:
            logger.debug("任务卡片初始化成功")
        else:
            logger.warning("任务卡片初始化失败")
            
        # 测试定时器
        if hasattr(dashboard, 'refresh_timer') and dashboard.refresh_timer:
            logger.debug("定时器初始化成功")
        else:
            logger.warning("定时器初始化失败")
            
        # 测试异步任务管理
        if hasattr(dashboard, 'active_workers'):
            logger.debug("异步任务管理初始化成功")
        else:
            logger.warning("异步任务管理初始化失败")
            
        # 清理
        dashboard.stop_refresh_timer()
        dashboard.cancel_active_workers()
        dashboard.close()
        
        app.quit()
        
        logger.info("基本功能测试通过")
        return True
        
    except Exception as e:
        logger.error(f"基本功能测试失败: {e}")
        logger.error(traceback.format_exc())
        return False

def test_async_api():
    """测试异步API"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("开始测试异步API...")
        
        from app.api.async_api import AsyncApiHelper, AsyncApiWorker
        
        # 测试helper创建
        helper = AsyncApiHelper()
        logger.debug("AsyncApiHelper创建成功")
        
        # 测试worker创建（不实际执行）
        def dummy_api():
            return {"test": "data"}
            
        worker = AsyncApiWorker(dummy_api)
        logger.debug("AsyncApiWorker创建成功")
        
        # 测试取消功能
        worker.cancel()
        logger.debug("Worker取消功能测试成功")
        
        logger.info("异步API测试通过")
        return True
        
    except Exception as e:
        logger.error(f"异步API测试失败: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """主测试函数"""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("开始安全启动测试")
    logger.info("=" * 60)
    
    success = True
    
    # 测试1: 模块导入
    if not test_imports():
        success = False
    
    # 测试2: 基本功能
    if not test_basic_functionality():
        success = False
        
    # 测试3: 异步API
    if not test_async_api():
        success = False
    
    logger.info("=" * 60)
    if success:
        logger.info("✅ 所有测试通过，程序应该可以安全启动")
    else:
        logger.error("❌ 部分测试失败，程序可能仍有问题")
    logger.info("=" * 60)
    
    return success

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"测试脚本本身出错: {e}")
        print(traceback.format_exc())
        sys.exit(1) 