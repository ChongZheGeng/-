from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QScrollArea
import sys

class MyWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("带滚动区域的窗口")
        self.resize(400, 300)

        # 创建滚动区域
        scrollArea = QScrollArea(self)
        scrollArea.setWidgetResizable(True)

        # 内容容器
        contentWidget = QWidget()
        contentLayout = QVBoxLayout(contentWidget)

        # 添加多个控件以触发滚动
        for i in range(30):
            label = QLabel(f"标签 {i+1}")
            contentLayout.addWidget(label)

        scrollArea.setWidget(contentWidget)

        # 主布局
        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(scrollArea)
        self.setLayout(mainLayout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())