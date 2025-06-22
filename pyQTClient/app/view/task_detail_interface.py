# coding:utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QFrame
from PyQt5.QtGui import QPalette

from qfluentwidgets import (TableWidget, StrongBodyLabel, CardWidget, SubtitleLabel,
                            FluentIcon as FIF, IconWidget, BodyLabel, ScrollArea, InfoBar,
                            Theme, isDarkTheme)

from ..api.api_client import api_client


class InfoCard(CardWidget):
    """显示基本信息的卡片"""
    def __init__(self, title, icon, parent=None):
        super().__init__(parent)
        self.iconWidget = IconWidget(icon, self)
        self.titleLabel = SubtitleLabel(title, self)
        self.vBoxLayout = QVBoxLayout(self)
        
        self.hBoxLayout = QHBoxLayout()
        self.hBoxLayout.addWidget(self.iconWidget)
        self.hBoxLayout.addWidget(self.titleLabel)
        self.hBoxLayout.addStretch(1)

        self.separator = QFrame(self)
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        
        self.vBoxLayout.addLayout(self.hBoxLayout)
        self.vBoxLayout.addWidget(self.separator)
        self.vBoxLayout.setSpacing(12)
        
    def add_info_row(self, label, value):
        row_layout = QHBoxLayout()
        row_layout.addWidget(StrongBodyLabel(f"{label}："))
        row_layout.addWidget(BodyLabel(str(value)))
        row_layout.addStretch(1)
        self.vBoxLayout.addLayout(row_layout)


class DataTableCard(CardWidget):
    """显示表格数据的卡片"""
    def __init__(self, title, icon, headers, parent=None):
        super().__init__(parent)
        self.iconWidget = IconWidget(icon, self)
        self.titleLabel = SubtitleLabel(title, self)
        self.vBoxLayout = QVBoxLayout(self)
        
        self.hBoxLayout = QHBoxLayout()
        self.hBoxLayout.addWidget(self.iconWidget)
        self.hBoxLayout.addWidget(self.titleLabel)
        self.hBoxLayout.addStretch(1)
        
        self.table = TableWidget(self)
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.vBoxLayout.addLayout(self.hBoxLayout)
        self.vBoxLayout.addWidget(self.table)
        self.vBoxLayout.setSpacing(12)

    def populate_data(self, data_list, data_keys):
        self.table.setRowCount(0)
        for item in data_list:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, key in enumerate(data_keys):
                self.table.setItem(row, col, QTableWidgetItem(str(item.get(key, ''))))


class TaskDetailInterface(ScrollArea):
    """加工任务详情界面"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("TaskDetailInterface")
        
        # 设置背景透明
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.viewport().setAutoFillBackground(False)
        
        # 创建内容控件
        self.scrollWidget = QWidget()
        self.scrollWidget.setObjectName("scrollWidget")
        self.scrollWidget.setAttribute(Qt.WA_TranslucentBackground)
        
        # 应用样式表
        self.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollArea > QWidget > QScrollBar {
                background: palette(base);
            }
            #scrollWidget {
                background: transparent;
            }
        """)
        
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        
        # 设置布局
        self.main_layout = QVBoxLayout(self.scrollWidget)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        # 界面标题
        self.title = SubtitleLabel("加工任务详情", self.scrollWidget)
        self.main_layout.addWidget(self.title)

        # 初始化各个卡片
        self.task_info_card = InfoCard("任务基本信息", FIF.ROBOT, self.scrollWidget)
        self.tool_info_card = InfoCard("刀具信息", FIF.CODE, self.scrollWidget)
        self.material_info_card = InfoCard("构件信息", FIF.CONSTRACT, self.scrollWidget)
        
        self.sensor_data_card = DataTableCard("传感器数据", FIF.PIE_SINGLE,
                                              ["传感器ID", "类型", "时间戳", "数值"], self.scrollWidget)
        self.quality_card = DataTableCard("加工质量记录", FIF.ACCEPT, 
                                          ["检测员", "表面粗糙度", "尺寸公差", "缺陷类型"], self.scrollWidget)
        self.wear_card = DataTableCard("刀具磨损记录", FIF.SETTING, 
                                       ["记录时间", "磨损类型", "磨损值", "备注"], self.scrollWidget)

        # 创建一个水平布局用于放置顶部的信息卡片
        top_info_layout = QHBoxLayout()
        top_info_layout.addWidget(self.task_info_card, 1)
        top_info_layout.addWidget(self.tool_info_card, 1)
        top_info_layout.addWidget(self.material_info_card, 1)
        
        # 添加到主布局
        self.main_layout.addLayout(top_info_layout)
        self.main_layout.addWidget(self.sensor_data_card)
        self.main_layout.addWidget(self.quality_card)
        self.main_layout.addWidget(self.wear_card)
        self.main_layout.addStretch(1)

    def load_task_details(self, task_id):
        """根据任务ID加载并显示所有详细信息"""
        # 确保在加载数据前清空所有卡片内容
        for child in self.scrollWidget.findChildren(InfoCard):
            # 移除所有子项，除了标题和分隔线
            layout = child.layout()
            if layout:
                for i in reversed(range(layout.count())):
                    item = layout.itemAt(i)
                    if i >= 2:  # 前两个项是标题和分隔线
                        widget = item.widget()
                        if widget:
                            widget.setParent(None)
                            widget.deleteLater()
                        layout.removeItem(item)
        
        # 清空表格数据
        self.sensor_data_card.table.setRowCount(0)
        self.quality_card.table.setRowCount(0)
        self.wear_card.table.setRowCount(0)
        
        self.title.setText(f"加工任务详情 (ID: {task_id})")
        data = api_client.get_processing_task_detail(task_id)

        if not data:
            InfoBar.error("加载失败", "无法获取任务详细信息。", duration=3000, parent=self.window())
            return
        
        # 1. 填充任务基本信息
        self.task_info_card.add_info_row("任务编码", data.get('task_code', 'N/A'))
        self.task_info_card.add_info_row("操作员", data.get('operator', {}).get('full_name', 'N/A'))
        self.task_info_card.add_info_row("加工时间", data.get('processing_time', 'N/A').replace('T', ' '))
        self.task_info_card.add_info_row("状态", data.get('status_display', 'N/A'))
        
        # 2. 填充刀具信息
        tool = data.get('tool', {})
        self.tool_info_card.add_info_row("刀具编码", tool.get('code', 'N/A'))
        self.tool_info_card.add_info_row("刀具类型", tool.get('tool_type', 'N/A'))
        self.tool_info_card.add_info_row("规格", tool.get('tool_spec', 'N/A'))

        # 3. 填充构件信息
        material = data.get('composite_material', {})
        self.material_info_card.add_info_row("构件号", material.get('part_number', 'N/A'))
        self.material_info_card.add_info_row("材料类型", material.get('material_type_display', 'N/A'))
        self.material_info_card.add_info_row("厚度(mm)", material.get('thickness', 'N/A'))
        
        # 4. 填充表格数据
        self.sensor_data_card.populate_data(data.get('sensor_data', []), 
                                            ['sensor_id', 'sensor_type_display', 'timestamp', 'value'])
        self.quality_card.populate_data(data.get('quality_records', []), 
                                         ['inspector_name', 'surface_roughness', 'dimensional_tolerance', 'defect_type_display'])
        self.wear_card.populate_data(data.get('tool_wear_records', []), 
                                     ['record_time', 'wear_type', 'wear_value', 'remarks'])

        InfoBar.success("加载成功", "任务详情已更新。", duration=1500, parent=self.window()) 