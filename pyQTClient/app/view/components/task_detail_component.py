# coding:utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QTableWidgetItem, QHeaderView, QGridLayout, \
    QTableWidget

from qfluentwidgets import (TableWidget, StrongBodyLabel, IconWidget, BodyLabel, PrimaryPushButton, PushButton, HeaderCardWidget)


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
        self.viewLayout.addWidget(grid_widget)  # 将该 widget 添加到卡片的视图布局中
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
        self.table.horizontalHeader().setSectionResizeMode(self.table.columnCount() - 1, QHeaderView.Fixed)
        # 初始设置操作列宽度（数据加载后会重新计算）
        self.table.horizontalHeader().resizeSection(self.table.columnCount() - 1, 90)

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
        self.table.horizontalHeader().resizeSection(self.table.columnCount() - 1, total_width)
