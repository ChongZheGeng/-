# coding:utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QAction

from qfluentwidgets import (TreeView, SubtitleLabel, PushButton,
                            RoundMenu, InfoBar, MessageBox, Action, FluentIcon as FIF)

from ..api.api_client import api_client
from ..api.data_manager import data_manager
from .nav_interface import NavInterface
import logging
import time

# 设置logger
logger = logging.getLogger(__name__)

from .components.task_group_component import GroupNameDialog


class TaskGroupInterface(NavInterface):
    """ 任务分组管理界面 """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("TaskGroupInterface")
        self.copied_task_id = None  # 用于存储复制的任务ID
        self.groups_worker = None
        self.tasks_worker = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # --- 任务组树状图 ---
        # 标题与工具栏
        group_title = SubtitleLabel("任务分组管理")
        self.add_group_button = PushButton("新建组")
        
        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(group_title)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.add_group_button)
        
        self.main_layout.addLayout(toolbar_layout)

        # 树状视图
        self.group_tree = TreeView(self)
        self.group_model = QStandardItemModel(self)
        self.group_tree.setModel(self.group_model)
        
        self.main_layout.addWidget(self.group_tree)

        # --- 信号连接 ---
        self.add_group_button.clicked.connect(self.add_group)
        self.group_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.group_tree.customContextMenuRequested.connect(self.show_group_context_menu)

        # 移除初始化时的数据加载调用，改为在on_activated中加载

    def on_activated(self):
        """界面激活时的回调方法 - 按需加载数据"""
        try:
            self.populate_group_tree(preserve_old_data=True)
        except Exception as e:
            logger.error(f"激活任务分组界面时加载数据出错: {e}")
            self.on_groups_data_error(str(e))

    def on_deactivated(self):
        """
        当界面被切换离开时调用。
        可以在此处进行一些清理工作，如取消正在进行的请求。
        """
        # 取消正在进行的数据加载请求
        if hasattr(self, 'groups_worker') and self.groups_worker and self.groups_worker.isRunning():
            self.groups_worker.cancel()
        if hasattr(self, 'tasks_worker') and self.tasks_worker and self.tasks_worker.isRunning():
            self.tasks_worker.cancel()
        logger.debug("TaskGroupInterface 被切换离开，已取消数据加载请求")

    def populate_group_tree(self, preserve_old_data=True):
        """ 异步从API获取数据并填充树形控件 """
        # 取消之前的请求
        if self.groups_worker and self.groups_worker.isRunning():
            self.groups_worker.cancel()
        if self.tasks_worker and self.tasks_worker.isRunning():
            self.tasks_worker.cancel()

        # 设置加载状态
        self._is_loading = True

        try:
            logger.debug("使用数据管理器加载任务分组数据")
            
            # 只有在不保留旧数据时才立即清空
            if not preserve_old_data:
                self.group_model.clear()
                self.group_model.setHorizontalHeaderLabels(["分组 / 任务"])
            
            # 使用数据管理器获取任务分组数据
            self.groups_worker = data_manager.get_data_async(
                data_type='task_groups',
                success_callback=self.on_groups_data_received,
                error_callback=self.on_groups_data_error,
                force_refresh=True
            )
        except Exception as e:
            logger.error(f"加载任务分组数据时出错: {e}")
            self.on_groups_data_error(str(e))
            self._is_loading = False
    
    def on_groups_data_received(self, response_data):
        """处理接收到的任务分组数据"""
        try:
            if not self or not hasattr(self, 'group_tree') or not self.group_tree:
                logger.warning("任务分组数据回调时界面已销毁")
                return
                
            if response_data is None:
                self._is_loading = False
                return

            # 检查是否正在加载中，避免重复处理
            if not getattr(self, '_is_loading', False):
                logger.debug("不在加载状态，跳过分组数据处理")
                return

            # 清空模型并重新设置标题
            self.group_model.clear()
            self.group_model.setHorizontalHeaderLabels(["分组 / 任务"])

            groups_data = response_data.get('results', [])
            logger.debug(f"接收到 {len(groups_data)} 个任务分组数据")
            
            # 保存分组数据以供任务分配时使用
            self._current_groups_data = groups_data
            
            # 异步获取所有任务
            self.tasks_worker = data_manager.get_data_async(
                data_type='processing_tasks',
                success_callback=self.on_tasks_data_received,
                error_callback=self.on_tasks_data_error,
                force_refresh=True
            )
            
        except Exception as e:
            logger.error(f"处理任务分组数据时出错: {e}")
            self._is_loading = False
    
    def on_groups_data_error(self, error_message):
        """处理任务分组数据加载错误"""
        logger.error(f"任务分组数据加载失败: {error_message}")
        self._is_loading = False
        if self and hasattr(self, 'parent') and self.parent():
            InfoBar.error("加载失败", f"任务分组数据加载失败: {error_message}", parent=self)
    
    def on_tasks_data_received(self, tasks_response):
        """处理接收到的任务数据并构建完整的树状结构"""
        try:
            if not self or not hasattr(self, 'group_tree') or not self.group_tree:
                logger.warning("任务数据回调时界面已销毁")
                return
            
            if not getattr(self, '_is_loading', False) or not hasattr(self, '_current_groups_data'):
                logger.debug("不在加载状态或没有分组数据，跳过任务数据处理")
                return
                
            groups_data = self._current_groups_data
            root_item = self.group_model.invisibleRootItem()
            groups_map = {}

            # 创建"未归档任务"节点
            unarchived_item = QStandardItem("未归档任务")
            unarchived_item.setData({"name": "未归档任务", "is_default": True, "id": None}, Qt.UserRole)
            unarchived_item.setEditable(False)

            # 创建分组节点
            for group in groups_data:
                group_item = QStandardItem(group['name'])
                group_item.setData(group, Qt.UserRole)
                group_item.setEditable(False)
                groups_map[group['id']] = group_item

            # 分配任务到对应分组
            if tasks_response and 'results' in tasks_response:
                logger.debug(f"接收到 {len(tasks_response['results'])} 个任务数据")
                for task in tasks_response['results']:
                    task_display_text = f"{task['task_code']} ({task.get('processing_type_display', 'N/A')})"
                    task_item = QStandardItem(task_display_text)
                    task_item.setData(task, role=Qt.UserRole + 1)
                    task_item.setEditable(False)
                    task_item.setToolTip(f"状态: {task.get('status_display', 'N/A')}")

                    group_id = task.get('group')
                    if group_id and group_id in groups_map:
                        groups_map[group_id].appendRow(task_item)
                    else:
                        unarchived_item.appendRow(task_item)

            # 添加节点到模型（显示任务数量）
            unarchived_count = unarchived_item.rowCount()
            unarchived_item.setText(f"未归档任务 ({unarchived_count})")
            root_item.appendRow(unarchived_item)

            for group_id, group_item in groups_map.items():
                task_count = group_item.rowCount()
                group_data = group_item.data(Qt.UserRole)
                if group_data:
                    group_item.setText(f"{group_data['name']} ({task_count})")
                    root_item.appendRow(group_item)
            
            self.group_tree.expandAll()
            logger.info(f"任务分组树状结构构建完成，共 {len(groups_data)} 个分组")
            
            # 清理状态
            if hasattr(self, '_current_groups_data'):
                delattr(self, '_current_groups_data')
            self._is_loading = False
            
        except Exception as e:
            logger.error(f"处理任务数据时出错: {e}")
            self._is_loading = False
    
    def on_tasks_data_error(self, error_message):
        """处理任务数据加载错误"""
        logger.error(f"任务数据加载失败: {error_message}")
        self._is_loading = False
        if hasattr(self, '_current_groups_data'):
            delattr(self, '_current_groups_data')
        if self and hasattr(self, 'parent') and self.parent():
            InfoBar.error("加载失败", f"任务数据加载失败: {error_message}", parent=self)

    def add_group(self):
        """ 新建任务组 """
        dialog = GroupNameDialog("新建任务组", parent=self.window())
        if dialog.exec():
            name = dialog.getName()
            if name:
                result = api_client.add_task_group({'name': name})
                if result:
                    InfoBar.success("成功", f"任务组 '{name}' 已创建。", parent=self)
                    self.populate_group_tree(preserve_old_data=False)
                else:
                    InfoBar.error("失败", "创建任务组失败。", parent=self)

    def show_group_context_menu(self, pos):
        """ 显示任务组或任务的右键菜单 """
        index = self.group_tree.indexAt(pos)
        if not index.isValid():
            return
            
        item = self.group_model.itemFromIndex(index)
        
        # 检查点击的是分组还是任务
        group_data = item.data(Qt.UserRole)
        task_data = item.data(Qt.UserRole + 1)

        menu = RoundMenu(parent=self)
        
        if task_data: # 点击的是任务
            copy_action = Action(FIF.COPY, "复制任务")
            copy_action.triggered.connect(lambda: self.copy_task(item))
            menu.addAction(copy_action)

        elif group_data: # 点击的是分组
            add_group_action = Action(FIF.ADD, "新建组")
            add_group_action.triggered.connect(self.add_group)
            menu.addAction(add_group_action)
            
            if self.copied_task_id:
                paste_action = Action(FIF.PASTE, "粘贴任务")
                paste_action.triggered.connect(lambda: self.paste_task(item))
                menu.addAction(paste_action)

            # 默认的"未归档任务"组不能重命名和删除
            if not group_data.get('is_default', False):
                menu.addSeparator()
                rename_action = Action(FIF.EDIT, "重命名")
                rename_action.triggered.connect(lambda: self.rename_group(item))
                menu.addAction(rename_action)

                delete_action = Action(FIF.DELETE, "删除")
                delete_action.triggered.connect(lambda: self.delete_group(item))
                menu.addAction(delete_action)

        # 如果菜单有内容，则显示
        if menu.actions():
            menu.exec(self.group_tree.mapToGlobal(pos))

    def copy_task(self, item):
        """ 复制任务ID到剪贴板 """
        task_data = item.data(Qt.UserRole + 1)
        if task_data and 'id' in task_data:
            self.copied_task_id = task_data['id']
            task_code = task_data.get('task_code', '')
            InfoBar.success("成功", f"任务 '{task_code}' 已复制。", parent=self)

    def paste_task(self, group_item):
        """ 粘贴任务到指定分组 """
        if not self.copied_task_id:
            InfoBar.warning("提示", "剪贴板中没有任务。", parent=self)
            return

        group_data = group_item.data(Qt.UserRole)
        target_group_id = group_data.get('id') if group_data else None
        
        # 1. 获取源任务的详细信息
        original_task = api_client.get_processing_task_detail(self.copied_task_id)
        if not original_task:
            InfoBar.error("失败", "粘贴任务失败：无法获取源任务信息。", parent=self)
            return
            
        # 2. 生成一个新的唯一任务编码
        import datetime
        timestamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")
        new_task_code = f"{original_task.get('task_code', 'Task')}-Copy-{timestamp}"
            
        # 3. 准备新任务数据
        new_task_data = {
            "task_code": new_task_code,
            "processing_time": original_task.get("processing_time"),
            "processing_type": original_task.get("processing_type"),
            "status": "planned",  # 新任务默认为"计划中"状态
            "tool": original_task.get("tool", {}).get("id"),
            "composite_material": original_task.get("composite_material", {}).get("id"),
            "operator": original_task.get("operator", {}).get("id"),
            "duration": original_task.get("duration"),
            "notes": original_task.get("notes"),
            "group": target_group_id
        }
        
        # 4. 获取原任务的参数
        parameters = []
        if "parameters" in original_task and original_task["parameters"]:
            for param in original_task["parameters"]:
                parameters.append({
                    "parameter_name": param.get("parameter_name"),
                    "parameter_value": param.get("parameter_value"),
                    "unit": param.get("unit")
                })
        
        new_task_data["parameters"] = parameters
        
        # 5. 直接创建新任务
        created_task = api_client.add_processing_task(new_task_data)
        
        if created_task:
            InfoBar.success("成功", f"任务已复制并粘贴到 '{group_data.get('name', '未归档任务')}'。", parent=self)
            self.populate_group_tree(preserve_old_data=False)
        else:
            InfoBar.error("失败", "粘贴任务失败：无法创建新任务。", parent=self)

    def rename_group(self, item):
        """ 重命名任务组 """
        group_data = item.data(Qt.UserRole)
        dialog = GroupNameDialog(f"重命名 '{group_data['name']}'", 
                                 initial_text=group_data['name'], 
                                 parent=self.window())
        
        if dialog.exec():
            name = dialog.getName()
            if name and name != group_data['name']:
                result = api_client.update_task_group(group_data['id'], {'name': name})
                if result:
                    InfoBar.success("成功", "任务组已重命名。", parent=self)
                    self.populate_group_tree(preserve_old_data=False)
                else:
                    InfoBar.error("失败", "重命名失败。", parent=self)

    def delete_group(self, item):
        """ 删除任务组 """
        group_data = item.data(Qt.UserRole)
        title = "确认删除"
        content = f"您确定要删除任务组 '{group_data['name']}' 吗？\n注意：只有组内没有任务时才能删除。"
        w = MessageBox(title, content, self.window())

        if w.exec():
            success = api_client.delete_task_group(group_data['id'])
            if success:
                InfoBar.success("成功", "任务组已删除。", parent=self)
                self.populate_group_tree(preserve_old_data=False)
            else:
                InfoBar.error("失败", "删除失败，请确保组内没有任务。", parent=self)

    def __del__(self):
        """ 确保在销毁时取消工作线程 """
        if hasattr(self, 'groups_worker') and self.groups_worker:
            self.groups_worker.cancel()
        if hasattr(self, 'tasks_worker') and self.tasks_worker:
            self.tasks_worker.cancel() 