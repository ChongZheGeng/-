# coding:utf-8
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QFrame, QGridLayout, QLabel, QTableWidget, QFileDialog
from PyQt5.QtGui import QPalette

from qfluentwidgets import (TableWidget, StrongBodyLabel, CardWidget, SubtitleLabel,
                            FluentIcon as FIF, IconWidget, BodyLabel, ScrollArea, InfoBar,
                            Theme, isDarkTheme, PrimaryPushButton, PushButton, HeaderCardWidget)

from ..api.api_client import api_client
import webbrowser
import os


class BaseInfoCard(HeaderCardWidget):
    """显示键值对信息的基础卡片"""
    def __init__(self, title, icon, parent=None):
        super().__init__(parent)
        self.setTitle(title)
        
        # 手动添加图标到标题栏
        if icon:
            self.iconWidget = IconWidget(icon, self)
            self.iconWidget.setFixedSize(16, 16)
            self.headerLayout.insertWidget(0, self.iconWidget)
        
        # 设置透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建一个用于容纳网格布局的 QWidget
        grid_widget = QWidget(self.view)
        self.gridLayout = QGridLayout(grid_widget)
        self.viewLayout.addWidget(grid_widget) # 将该 widget 添加到卡片的视图布局中
        # self.viewLayout.setContentsMargins(0, 0, 0, 0)
        
        self.gridLayout.setContentsMargins(16, 16, 16, 16)
        self.gridLayout.setSpacing(10)
        self.next_row = 0

    def add_info(self, label, value):
        """添加一行信息"""
        self.gridLayout.addWidget(StrongBodyLabel(f"{label}："), self.next_row, 0)
        self.gridLayout.addWidget(BodyLabel(str(value)), self.next_row, 1)
        self.next_row += 1

    def clear_info(self):
        """清空信息"""
        while self.gridLayout.count():
            item = self.gridLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.next_row = 0


class BaseTableCard(HeaderCardWidget):
    """显示表格数据的基础卡片"""
    def __init__(self, title, icon, headers, parent=None):
        super().__init__(parent)
        self.setTitle(title)
        
        # 手动添加图标到标题栏
        if icon:
            self.iconWidget = IconWidget(icon, self)
            self.iconWidget.setFixedSize(16, 16)
            self.headerLayout.insertWidget(0, self.iconWidget)

        # 设置透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.table = TableWidget(self.view)
        self.table.setMinimumHeight(200)

        # --- 应用官方示例样式 ---
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)
        # --- 样式应用结束 ---

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        # 列宽设置：数据列可调整
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        
        self.viewLayout.addWidget(self.table)
        # self.viewLayout.setContentsMargins(0, 0, 0, 0)

    def populate_data(self, data_list, data_keys):
        """填充表格数据"""
        self.table.setRowCount(0)
        for item in data_list:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, key in enumerate(data_keys):
                value = item.get(key, '')
                # 特殊处理
                if key == 'upload_time' and value:
                    value = str(value).replace('T', ' ').split('.')[0]
                elif key == 'file_size_mb' and value:
                    value = f"{value} MB"
                
                self.table.setItem(row, col, QTableWidgetItem(str(value)))
        


    def add_action_buttons(self, data_list, button_configs):
        """为表格添加操作按钮"""
        # 检查是否需要添加操作列
        current_headers = []
        for i in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(i)
            if header_item:
                current_headers.append(header_item.text())
        
        # 如果最后一列不是"操作"列，则添加操作列
        if not current_headers or current_headers[-1] != "操作":
            self.table.setColumnCount(self.table.columnCount() + 1)
            current_headers.append("操作")
            self.table.setHorizontalHeaderLabels(current_headers)
        
        # 操作列固定宽度
        self.table.horizontalHeader().setSectionResizeMode(self.table.columnCount()-1, QHeaderView.Fixed)
        # 初始设置操作列宽度（数据加载后会重新计算）
        self.table.horizontalHeader().resizeSection(self.table.columnCount()-1, 90)

        for row, item in enumerate(data_list):
            buttons_widget = QWidget()
            buttons_layout = QHBoxLayout(buttons_widget)
            buttons_layout.setContentsMargins(2, 2, 2, 2)
            buttons_layout.setSpacing(8)
            
            for config in button_configs:
                if config['text'] == '下载':
                    button = PrimaryPushButton(config['text'])
                else:
                    button = PushButton(config['text'])
                
                # 使用lambda的默认参数来捕获当前循环的变量
                button.clicked.connect(lambda _, data=item, cb=config['callback']: cb(data))
                buttons_layout.addWidget(button)
            
            self.table.setCellWidget(row, self.table.columnCount() - 1, buttons_widget)
        
        # 根据按钮数量动态调整操作列宽度
        button_count = len(button_configs)
        button_width = 75  # 每个按钮约75px
        spacing = 8  # 按钮间距
        margin = 6  # 边距
        total_width = button_count * button_width + (button_count - 1) * spacing + 2 * margin
        self.table.horizontalHeader().resizeSection(self.table.columnCount()-1, total_width)


class TaskDetailInterface(ScrollArea):
    """加工任务详情界面"""
    backRequested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("TaskDetailInterface")
        
        self.view = QWidget()
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.view.setObjectName("TaskDetailView")
        
        # 设置透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.view.setAttribute(Qt.WA_TranslucentBackground)

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(30, 0, 30, 30)
        self.main_layout.setSpacing(20)
        self.main_layout.setAlignment(Qt.AlignTop)

        self.create_title_bar()
        self.create_cards()

        # 布局信息卡片
        top_info_layout = QHBoxLayout()
        top_info_layout.addWidget(self.task_info_card, 1)
        top_info_layout.addWidget(self.tool_info_card, 1)
        
        second_info_layout = QHBoxLayout()
        second_info_layout.addWidget(self.material_info_card, 1)
        second_info_layout.addWidget(self.group_info_card, 1)
        
        self.main_layout.addLayout(top_info_layout)
        self.main_layout.addLayout(second_info_layout)
        self.main_layout.addWidget(self.sensor_data_card)
        self.main_layout.addWidget(self.quality_card)
        self.main_layout.addWidget(self.wear_card)
        self.main_layout.addStretch(1)

        self.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background: transparent; 
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QWidget {
                background: transparent;
            }
            HeaderCardWidget {
                background: transparent;
            }
        """)

    def create_title_bar(self):
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 20, 0, 10)
        
        self.back_button = PushButton("返回")
        self.back_button.setIcon(FIF.RETURN)
        self.back_button.clicked.connect(self.backRequested.emit)
        
        self.title = SubtitleLabel("加工任务详情")
        
        title_layout.addWidget(self.back_button)
        title_layout.addWidget(self.title)
        title_layout.addStretch(1)
        
        self.main_layout.addLayout(title_layout)

    def create_cards(self):
        self.task_info_card = BaseInfoCard("任务基本信息", FIF.ROBOT, self.view)
        self.tool_info_card = BaseInfoCard("刀具信息", FIF.CODE, self.view)
        self.material_info_card = BaseInfoCard("构件信息", FIF.CONSTRACT, self.view)
        self.group_info_card = BaseInfoCard("分组信息", FIF.FOLDER, self.view)

        sensor_headers = ["文件名", "传感器类型", "文件大小", "上传时间", "传感器ID"]
        self.sensor_data_card = BaseTableCard("传感器数据文件", FIF.DOCUMENT, sensor_headers, self.view)

        quality_headers = ["检测员", "表面粗糙度(Ra)", "尺寸公差(mm)", "缺陷类型"]
        self.quality_card = BaseTableCard("加工质量记录", FIF.ACCEPT, quality_headers, self.view)

        wear_headers = ["记录时间", "磨损值", "测量方法", "测量位置"]
        self.wear_card = BaseTableCard("刀具磨损记录", FIF.SETTING, wear_headers, self.view)

    def load_task_details(self, task_id):
        self.title.setText(f"加工任务详情 (ID: {task_id})")
        data = api_client.get_processing_task_detail(task_id)

        if not data:
            InfoBar.error("加载失败", "无法获取任务详细信息。", duration=3000, parent=self.window())
            return

        # 清空旧数据
        self.task_info_card.clear_info()
        self.tool_info_card.clear_info()
        self.material_info_card.clear_info()
        self.group_info_card.clear_info()

        # 填充任务基本信息
        self.task_info_card.add_info("任务编码", data.get('task_code', 'N/A'))
        self.task_info_card.add_info("加工类型", data.get('processing_type_display', 'N/A'))
        self.task_info_card.add_info("操作员", data.get('operator', {}).get('username', 'N/A'))
        self.task_info_card.add_info("加工时间", str(data.get('processing_time', 'N/A')).replace('T', ' '))
        self.task_info_card.add_info("状态", data.get('status_display', 'N/A'))
        
        # 填充刀具信息
        tool = data.get('tool', {})
        self.tool_info_card.add_info("刀具编码", tool.get('code', 'N/A'))
        self.tool_info_card.add_info("刀具类型", tool.get('tool_type', 'N/A'))
        
        # 填充构件信息
        material = data.get('composite_material', {})
        self.material_info_card.add_info("构件号", material.get('part_number', 'N/A'))
        self.material_info_card.add_info("材料类型", material.get('material_type_display', 'N/A'))
        
        # 填充分组信息
        group_id = data.get('group')
        if group_id and (groups := api_client.get_task_groups()) and 'results' in groups:
            group_info = next((g for g in groups['results'] if g['id'] == group_id), None)
            if group_info:
                self.group_info_card.add_info("分组名称", group_info.get('name', 'N/A'))
            else:
                self.group_info_card.add_info("分组状态", "信息不可用")
        else:
            self.group_info_card.add_info("分组状态", "未归档")

        # 填充传感器数据
        sensor_data = data.get('sensor_data', [])
        sensor_keys = ['file_name', 'sensor_type_display', 'file_size_mb', 'upload_time', 'sensor_id']
        self.sensor_data_card.populate_data(sensor_data, sensor_keys)
        if sensor_data:
            self.sensor_data_card.add_action_buttons(sensor_data, [{
                'text': '下载',
                'callback': lambda item: self.download_file(item.get('file_url'), item.get('file_name', 'unknown')),
                'style': 'background-color: #0078d4; color: white;'
            }])

        # 填充质量记录
        quality_records = data.get('quality_records', [])
        quality_keys = ['inspector_name', 'surface_roughness', 'dimensional_tolerance', 'defect_type_display']
        self.quality_card.populate_data(quality_records, quality_keys)
        
        # 填充磨损记录
        wear_records = data.get('tool_wear_records', [])
        wear_keys = ['record_time', 'wear_value', 'measurement_method', 'position']
        self.wear_card.populate_data(wear_records, wear_keys)

        InfoBar.success("加载成功", "任务详情已更新。", duration=1500, parent=self.window())
        
    def download_file(self, file_url, file_name):
        """下载文件"""
        # 获取主窗口的下载按钮
        main_window = self.window()
        if hasattr(main_window, 'download_button'):
            main_window.download_button.start_download(file_name, file_url)
        else:
            InfoBar.error("错误", "下载功能不可用", parent=self) 