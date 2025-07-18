# coding:utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QAbstractItemView

from qfluentwidgets import (TableWidget, PushButton, StrongBodyLabel, LineEdit, ComboBox,
                            TextEdit, PrimaryPushButton, MessageBox, InfoBar, MessageBoxBase, SubtitleLabel)

from .nav_interface import NavInterface

from ..api.api_client import api_client
from ..api.data_manager import interface_loader
from .components.composite_material_component import CompositeMaterialEditDialog
import logging

# 设置logger
logger = logging.getLogger(__name__)


class CompositeMaterialInterface(NavInterface):
    """ 复合材料构件管理主界面 """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("CompositeMaterialInterface")
        self.worker = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        self.main_layout.addWidget(SubtitleLabel("复合材料构件管理"))

        # --- 工具栏 ---
        toolbar_layout = QHBoxLayout()
        self.add_button = PrimaryPushButton("新增构件")
        self.refresh_button = PushButton("刷新数据")
        toolbar_layout.addWidget(self.add_button)
        toolbar_layout.addWidget(self.refresh_button)
        toolbar_layout.addStretch(1)
        self.main_layout.addLayout(toolbar_layout)

        # --- 数据表格 ---
        self.table = TableWidget(self)
        self.main_layout.addWidget(self.table)
        
        # --- 应用官方示例样式 ---
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)
        # --- 样式应用结束 ---
        
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        self._define_column_mapping()

        # --- 信号与槽连接 ---
        self.refresh_button.clicked.connect(self.populate_table)
        self.add_button.clicked.connect(self.add_material)

    def _define_column_mapping(self):
        """定义表格的列映射关系"""
        self.column_mapping = [
            {'key': 'id', 'header': 'ID', 'width': 60},
            {'key': 'part_number', 'header': '构件编号'},
            {
                'key': 'material_type', 
                'header': '材料类型', 
                'formatter': lambda material_type: dict(CompositeMaterialEditDialog.MATERIAL_TYPE_CHOICES).get(material_type, material_type)
            },
            {'key': 'thickness', 'header': '厚度(mm)'},
            {'key': 'created_at', 'header': '创建时间', 'formatter': lambda t: t.split('T')[0] if t else 'N/A'},
            {'key': 'updated_at', 'header': '更新时间', 'formatter': lambda t: t.split('T')[0] if t else 'N/A'},
            {
                'type': 'buttons',
                'header': '操作',
                'width': 170,
                'buttons': [
                    {'text': '编辑', 'style': 'primary', 'callback': self.edit_material},
                    {'text': '删除', 'style': 'default', 'callback': lambda material: self.delete_material(material['id'])}
                ]
            }
        ]

    def on_activated(self):
        """
        当界面被激活时调用（例如，通过导航切换到此界面）。
        主要负责自动加载数据，为了UI流畅性会保留旧数据。
        """
        logger.info("CompositeMaterialInterface 被激活，开始加载数据")
        self._load_data(preserve_old_data=True)

    def on_deactivated(self):
        """
        当界面被切换离开时调用。
        可以在此处进行一些清理工作，如取消正在进行的请求。
        """
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel()
            logger.debug("CompositeMaterialInterface 被切换离开，已取消数据加载请求")

    def _load_data(self, preserve_old_data: bool):
        """
        内部数据加载方法。
        
        Args:
            preserve_old_data (bool): 是否保留旧数据直到新数据加载完成
        """
        try:
            logger.debug(f"CompositeMaterialInterface._load_data() 被调用，preserve_old_data={preserve_old_data}")
            self.worker = interface_loader.load_for_interface(
                interface=self,
                data_type='composite_materials',
                table_widget=self.table,
                force_refresh=not preserve_old_data,
                preserve_old_data=preserve_old_data,
                column_mapping=self.column_mapping
            )
            logger.debug(f"CompositeMaterialInterface worker 创建成功: {self.worker is not None}")
        except Exception as e:
            logger.error(f"加载构件数据时出错: {e}")
            self.on_composite_materials_data_error(str(e))

    def populate_table(self):
        """ 手动刷新数据（不保留旧数据） """
        logger.debug("手动刷新构件数据")
        self._load_data(preserve_old_data=False)

    def on_composite_materials_data_received(self, response_data):
        """数据管理器使用的标准回调方法"""
        logger.debug(f"CompositeMaterialInterface.on_composite_materials_data_received 被调用，数据类型: {type(response_data)}")
        self.on_materials_data_received(response_data)
    
    def on_composite_materials_data_error(self, error):
        """数据管理器使用的标准错误回调方法"""
        self.on_materials_data_error(error)
    
    def on_materials_data_received(self, response_data):
        """处理接收到的构件数据（现在主要用于日志记录或额外操作）"""
        # 当使用了 column_mapping 自动填充时，表格填充已由 InterfaceDataLoader 自动处理
        # 这里只进行日志记录和任何需要的额外操作
        if hasattr(self, 'column_mapping') and self.column_mapping:
            total = response_data.get('count', 0)
            logger.info(f"CompositeMaterialInterface 成功接收并处理了 {total} 条构件数据。")
            return
        
        # 如果没有使用自动填充，则保留原有的手动处理逻辑
        # （这部分代码在当前实现中已经被移除，因为我们已经完全转向自动填充）
        logger.warning("CompositeMaterialInterface 未使用自动填充配置，但手动填充逻辑已被移除")
    
    def on_materials_data_error(self, error_message):
        """处理构件数据加载错误"""
        # InfoBar 错误提示已由 InterfaceDataLoader 自动处理
        logger.error(f"构件数据加载失败: {error_message}")

    def add_material(self):
        """ 弹出新增对话框 """
        dialog = CompositeMaterialEditDialog(self)
        if dialog.exec():
            data, _ = dialog.get_data()
            if data and api_client.add_composite_material(data):
                InfoBar.success("成功", "新增构件成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "新增构件失败，请查看控制台输出。", duration=3000, parent=self)

    def edit_material(self, material_data):
        """ 弹出编辑对话框 """
        dialog = CompositeMaterialEditDialog(self, material_data)
        if dialog.exec():
            data, _ = dialog.get_data()
            if data and api_client.update_composite_material(material_data['id'], data):
                InfoBar.success("成功", "更新构件成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "更新构件失败，请查看控制台输出。", duration=3000, parent=self)

    def delete_material(self, material_id):
        """ 删除构件 """
        msg_box = MessageBox("确认删除", f"您确定要删除 ID 为 {material_id} 的构件吗？", self.window())
        if msg_box.exec():
            if api_client.delete_composite_material(material_id):
                InfoBar.success("成功", "删除成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "删除失败", duration=3000, parent=self)

    # ... (rest of the existing methods remain unchanged)

    # ... (rest of the existing methods remain unchanged) 