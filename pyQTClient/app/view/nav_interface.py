from PyQt5.QtWidgets import QWidget

class NavInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
    
    def on_activated(self):
        pass

    def on_deactivated(self):
        pass