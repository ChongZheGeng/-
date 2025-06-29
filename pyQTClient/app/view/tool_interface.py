# coding:utf-8
import logging

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QAbstractItemView
from qfluentwidgets import (TableWidget, PushButton, PrimaryPushButton, MessageBox, InfoBar, SubtitleLabel)

from .nav_interface import NavInterface
from ..api.api_client import api_client
from ..api.data_manager import interface_loader
from .components.tool_component import ToolEditDialog

# 设置logger
logger = logging.getLogger(__name__)


class ToolInterface(NavInterface):
    """ 刀具管理主界面 """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("ToolInterface")
        self.worker = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        self.main_layout.addWidget(SubtitleLabel("刀具信息管理"))

        # --- 工具栏 ---
        toolbar_layout = QHBoxLayout()
        self.add_button = PrimaryPushButton("新增刀具")
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
        self.add_button.clicked.connect(self.add_tool)

    def _define_column_mapping(self):
        """定义表格的列映射关系"""
        self.column_mapping = [
            {'key': 'id', 'header': 'ID', 'width': 60},
            {'key': 'tool_type', 'header': '类型'},
            {'key': 'tool_spec', 'header': '规格'},
            {'key': 'code', 'header': '编码'},
            {
                'key': 'current_status',
                'header': '状态',
                'formatter': lambda status: dict(ToolEditDialog.TOOL_STATUS_CHOICES).get(status, status)
            },
            {'key': 'created_at', 'header': '创建时间', 'formatter': lambda t: t.split('T')[0] if t else 'N/A'},
            {'key': 'updated_at', 'header': '更新时间', 'formatter': lambda t: t.split('T')[0] if t else 'N/A'},
            {
                'type': 'buttons',
                'header': '操作',
                'width': 170,
                'buttons': [
                    {'text': '编辑', 'style': 'primary', 'callback': self.edit_tool},
                    {'text': '删除', 'style': 'default', 'callback': lambda tool: self.delete_tool(tool['id'])}
                ]
            }
        ]

    def on_activated(self):
        """
        当界面被激活时调用（例如，通过导航切换到此界面）。
        主要负责自动加载数据，为了UI流畅性会保留旧数据。
        """
        logger.info(f"ToolInterface 被激活，开始加载数据")
        self._load_data(preserve_old_data=True)

    def on_deactivated(self):
        """
        当界面被取消激活时调用（例如，切换到其他界面）。
        可用于停止定时器等清理工作。
        """
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel()
            logger.debug("ToolInterface 被切换离开，已取消数据加载请求")

    def _load_data(self, preserve_old_data: bool):
        """
        加载刀具数据的核心私有方法。
        
        :param preserve_old_data: 是否在加载新数据时保留旧数据以避免闪烁。
                                  手动刷新时应为 False，自动加载时应为 True。
        """
        try:
            logger.debug(f"ToolInterface._load_data() 被调用，preserve_old_data={preserve_old_data}")
            self.worker = interface_loader.load_for_interface(
                interface=self,
                data_type='tools',
                table_widget=self.table,
                force_refresh=not preserve_old_data,
                preserve_old_data=preserve_old_data,
                column_mapping=self.column_mapping
            )
            logger.debug(f"ToolInterface worker 创建成功: {self.worker is not None}")
        except Exception as e:
            logger.error(f"加载刀具数据时发生意外错误: {e}")
            InfoBar.error("严重错误", f"加载数据失败: {e}", duration=5000, parent=self)

    def populate_table(self):
        """ 
        手动刷新表格数据。
        该方法由"刷新"按钮调用，不保留旧数据以提供明确的刷新反馈。
        """
        logger.info("用户手动刷新刀具数据。")
        self._load_data(preserve_old_data=False)
        # 注释掉自动加载 ---

    def add_tool(self):
        """ 弹出新增对话框 """
        dialog = ToolEditDialog(self)
        if dialog.exec():
            data, _ = dialog.get_data()
            result = api_client.add_tool(data)
            if result:
                InfoBar.success("成功", "新增成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "新增失败，请查看控制台输出。", duration=3000, parent=self)

    def edit_tool(self, tool_data):
        """ 弹出编辑对话框 """
        dialog = ToolEditDialog(self, tool_data)
        if dialog.exec():
            data, _ = dialog.get_data()
            result = api_client.update_tool(tool_data['id'], data)
            if result:
                InfoBar.success("成功", "更新成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "更新失败，请查看控制台输出。", duration=3000, parent=self)

    def delete_tool(self, tool_id):
        """ 删除刀具 """
        msg_box = MessageBox("确认删除", f"您确定要删除 ID 为 {tool_id} 的刀具吗？", self.window())
        if msg_box.exec():
            if api_client.delete_tool(tool_id):
                InfoBar.success("成功", "删除成功", duration=2000, parent=self)
                self.populate_table()
            else:
                InfoBar.error("失败", "删除失败", duration=3000, parent=self)

    def __del__(self):
        """ 确保在销毁时取消工作线程 """
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel()

    def on_tools_data_received(self, response_data):
        """处理接收到的刀具数据（现在主要用于日志记录或额外操作）"""
        # 当使用了 column_mapping 自动填充时，表格填充已由 InterfaceDataLoader 自动处理
        # 这里只进行日志记录和任何需要的额外操作
        if hasattr(self, 'column_mapping') and self.column_mapping:
            total = response_data.get('count', 0)
            logger.info(f"ToolInterface 成功接收并处理了 {total} 条刀具数据。")
            return

        # 如果没有使用自动填充，则保留原有的手动处理逻辑
        # （这部分代码在当前实现中已经被移除，因为我们已经完全转向自动填充）
        logger.warning("ToolInterface 未使用自动填充配置，但手动填充逻辑已被移除")

    def on_tools_data_error(self, error_message):
        """处理刀具数据加载错误"""
        # InfoBar 错误提示已由 InterfaceDataLoader 自动处理
        logger.error(f"刀具数据加载失败: {error_message}")
