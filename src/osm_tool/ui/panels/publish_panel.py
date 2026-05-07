"""矢量切片发布面板（占位）"""
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PublishPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("矢量切片发布 - 开发中")
        label.setStyleSheet("font-size: 24px; color: #888;")
        layout.addWidget(label)
