"""数据拆分面板（占位）"""
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SplitPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("数据拆分 - 开发中")
        label.setStyleSheet("font-size: 24px; color: #888;")
        layout.addWidget(label)
