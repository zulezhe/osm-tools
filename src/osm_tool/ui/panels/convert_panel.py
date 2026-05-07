"""格式转换面板"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox,
    QFileDialog, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox,
)

from src.osm_tool.core.converter.base import Format, BaseConverter


class ConvertPanel(QWidget):
    """格式转换面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("格式转换")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        single_group = QGroupBox("单文件转换")
        form = QFormLayout(single_group)

        input_layout = QHBoxLayout()
        self._input_path = QLineEdit()
        input_btn = QPushButton("浏览...")
        input_btn.clicked.connect(self._browse_input)
        input_layout.addWidget(self._input_path)
        input_layout.addWidget(input_btn)
        form.addRow("输入文件:", input_layout)

        self._input_format_label = QLabel("-")
        form.addRow("输入格式:", self._input_format_label)

        self._output_format = QComboBox()
        for fmt in Format:
            self._output_format.addItem(fmt.value, fmt)
        form.addRow("输出格式:", self._output_format)

        output_layout = QHBoxLayout()
        self._output_path = QLineEdit()
        output_btn = QPushButton("浏览...")
        output_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(self._output_path)
        output_layout.addWidget(output_btn)
        form.addRow("输出文件:", output_layout)

        self._encoding_combo = QComboBox()
        self._encoding_combo.addItems(["UTF-8", "GBK", "Latin-1"])
        form.addRow("编码 (SHP):", self._encoding_combo)

        btn_layout = QHBoxLayout()
        self._convert_btn = QPushButton("开始转换")
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        btn_layout.addWidget(self._convert_btn)
        btn_layout.addWidget(self._progress)
        form.addRow(btn_layout)
        layout.addWidget(single_group)

        history_group = QGroupBox("转换历史")
        history_layout = QVBoxLayout(history_group)
        self._history_table = QTableWidget(0, 4)
        self._history_table.setHorizontalHeaderLabels(["输入", "输出格式", "状态", "耗时"])
        self._history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        history_layout.addWidget(self._history_table)
        layout.addWidget(history_group)

    def _browse_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择输入文件", "", "支持格式 (*.pbf *.osm *.geojson *.json *.shp *.gpkg);;所有文件 (*)")
        if path:
            self._input_path.setText(path)
            fmt = BaseConverter.detect_format(path)
            self._input_format_label.setText(fmt.value if fmt else "未知")

    def _browse_output(self):
        fmt = self._output_format.currentData()
        ext_map = {Format.PBF: "pbf", Format.GEOJSON: "geojson", Format.SHAPEFILE: "shp", Format.GEOPACKAGE: "gpkg"}
        ext = ext_map.get(fmt, "*")
        path, _ = QFileDialog.getSaveFileName(self, "选择输出路径", "", f"文件 (*.{ext})")
        if path:
            self._output_path.setText(path)
