"""下载面板"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QLabel, QPushButton,
    QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QDoubleSpinBox, QPlainTextEdit, QComboBox,
    QGroupBox, QMessageBox,
)

from src.osm_tool.models.download_task import DownloadTask


class DownloadPanel(QWidget):
    """下载功能面板"""

    download_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("下载数据")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        self._tabs.addTab(self._create_geofabrik_tab(), "Geofabrik")
        self._tabs.addTab(self._create_overpass_tab(), "Overpass API")
        self._tabs.addTab(self._create_bbox_tab(), "BBox 下载")
        layout.addWidget(self._tabs)

        list_group = QGroupBox("下载队列")
        list_layout = QVBoxLayout(list_group)
        self._download_table = QTableWidget(0, 5)
        self._download_table.setHorizontalHeaderLabels(["文件", "大小", "进度", "状态", "操作"])
        self._download_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        list_layout.addWidget(self._download_table)
        layout.addWidget(list_group)

    def _create_geofabrik_tab(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)

        tree_group = QGroupBox("区域选择")
        tree_layout = QVBoxLayout(tree_group)
        self._region_tree = QTreeWidget()
        self._region_tree.setHeaderLabels(["区域", "大小"])
        self._region_tree.itemClicked.connect(self._on_region_selected)
        tree_layout.addWidget(self._region_tree)
        refresh_btn = QPushButton("刷新区域列表")
        tree_layout.addWidget(refresh_btn)
        layout.addWidget(tree_group, stretch=1)

        info_group = QGroupBox("区域信息")
        info_layout = QFormLayout(info_group)
        self._region_name_label = QLabel("请选择区域")
        self._region_size_label = QLabel("-")
        info_layout.addRow("区域:", self._region_name_label)
        info_layout.addRow("大小:", self._region_size_label)

        path_layout = QHBoxLayout()
        self._geofabrik_path = QLineEdit()
        path_btn = QPushButton("浏览...")
        path_btn.clicked.connect(lambda: self._browse_output(self._geofabrik_path, "pbf"))
        path_layout.addWidget(self._geofabrik_path)
        path_layout.addWidget(path_btn)
        info_layout.addRow("保存到:", path_layout)

        self._geofabrik_download_btn = QPushButton("下载")
        self._geofabrik_download_btn.setEnabled(False)
        self._geofabrik_download_btn.clicked.connect(self._on_geofabrik_download)
        info_layout.addRow(self._geofabrik_download_btn)
        layout.addWidget(info_group, stretch=1)
        return widget

    def _create_overpass_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        query_group = QGroupBox("Overpass QL 查询")
        query_layout = QVBoxLayout(query_group)
        self._overpass_query = QPlainTextEdit()
        self._overpass_query.setPlaceholderText("[out:json];\nway(around:100,39.9,116.4)[\"highway\"];\nout body;\n>;out skel qt;")
        query_layout.addWidget(self._overpass_query)

        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel("输出格式:"))
        self._overpass_format = QComboBox()
        self._overpass_format.addItems(["JSON", "XML"])
        fmt_layout.addWidget(self._overpass_format)
        query_layout.addLayout(fmt_layout)
        layout.addWidget(query_group)

        path_layout = QHBoxLayout()
        self._overpass_path = QLineEdit()
        path_btn = QPushButton("浏览...")
        path_btn.clicked.connect(lambda: self._browse_output(self._overpass_path, "json"))
        path_layout.addWidget(self._overpass_path)
        path_layout.addWidget(path_btn)
        layout.addLayout(path_layout)

        download_btn = QPushButton("执行查询并下载")
        download_btn.clicked.connect(self._on_overpass_download)
        layout.addWidget(download_btn)
        return widget

    def _create_bbox_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        coord_group = QGroupBox("经纬度范围")
        coord_layout = QFormLayout(coord_group)
        self._bbox_left = QDoubleSpinBox(); self._bbox_left.setRange(-180, 180); self._bbox_left.setDecimals(6); self._bbox_left.setValue(116.3)
        self._bbox_bottom = QDoubleSpinBox(); self._bbox_bottom.setRange(-90, 90); self._bbox_bottom.setDecimals(6); self._bbox_bottom.setValue(39.8)
        self._bbox_right = QDoubleSpinBox(); self._bbox_right.setRange(-180, 180); self._bbox_right.setDecimals(6); self._bbox_right.setValue(116.5)
        self._bbox_top = QDoubleSpinBox(); self._bbox_top.setRange(-90, 90); self._bbox_top.setDecimals(6); self._bbox_top.setValue(40.0)
        coord_layout.addRow("左 (经度):", self._bbox_left)
        coord_layout.addRow("下 (纬度):", self._bbox_bottom)
        coord_layout.addRow("右 (经度):", self._bbox_right)
        coord_layout.addRow("上 (纬度):", self._bbox_top)
        layout.addWidget(coord_group)

        path_layout = QHBoxLayout()
        self._bbox_path = QLineEdit()
        path_btn = QPushButton("浏览...")
        path_btn.clicked.connect(lambda: self._browse_output(self._bbox_path, "osm"))
        path_layout.addWidget(self._bbox_path)
        path_layout.addWidget(path_btn)
        layout.addLayout(path_layout)

        download_btn = QPushButton("下载")
        download_btn.clicked.connect(self._on_bbox_download)
        layout.addWidget(download_btn)
        return widget

    def _browse_output(self, line_edit, ext):
        path, _ = QFileDialog.getSaveFileName(self, "选择保存路径", "", f"文件 (*.{ext})")
        if path:
            line_edit.setText(path)

    def _on_region_selected(self, item, column):
        self._region_name_label.setText(item.text(0))
        self._region_size_label.setText(item.text(1))
        self._geofabrik_download_btn.setEnabled(True)

    def _on_geofabrik_download(self):
        if not self._geofabrik_path.text():
            QMessageBox.warning(self, "提示", "请选择保存路径")
            return
        self._add_download_entry("Geofabrik 下载", "等待中")

    def _on_overpass_download(self):
        if not self._overpass_query.toPlainText().strip():
            QMessageBox.warning(self, "提示", "请输入 Overpass QL 查询")
            return
        if not self._overpass_path.text():
            QMessageBox.warning(self, "提示", "请选择保存路径")
            return
        self._add_download_entry("Overpass 查询", "等待中")

    def _on_bbox_download(self):
        if not self._bbox_path.text():
            QMessageBox.warning(self, "提示", "请选择保存路径")
            return
        area = (self._bbox_right.value() - self._bbox_left.value()) * (self._bbox_top.value() - self._bbox_bottom.value())
        if area > 0.25:
            QMessageBox.warning(self, "提示", f"面积 ({area:.2f}°²) 超过 OSM API 限制")
            return
        self._add_download_entry("BBox 下载", "等待中")

    def _add_download_entry(self, name, status):
        row = self._download_table.rowCount()
        self._download_table.insertRow(row)
        self._download_table.setItem(row, 0, QTableWidgetItem(name))
        self._download_table.setItem(row, 1, QTableWidgetItem("-"))
        self._download_table.setItem(row, 2, QTableWidgetItem("0%"))
        self._download_table.setItem(row, 3, QTableWidgetItem(status))
        self._download_table.setItem(row, 4, QTableWidgetItem("取消"))
