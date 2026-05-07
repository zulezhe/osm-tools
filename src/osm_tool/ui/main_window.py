"""主窗口"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget,
    QTextEdit, QToolBar, QStatusBar, QSplitter, QMessageBox,
)

from src.osm_tool.ui.panels.download_panel import DownloadPanel
from src.osm_tool.ui.panels.split_panel import SplitPanel
from src.osm_tool.ui.panels.process_panel import ProcessPanel
from src.osm_tool.ui.panels.convert_panel import ConvertPanel
from src.osm_tool.ui.panels.publish_panel import PublishPanel
from src.osm_tool.utils.logger import setup_logger

logger = setup_logger("osm_tool.ui")


class MainWindow(QMainWindow):
    """应用主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OSM Data Toolbox")
        self.setMinimumSize(1200, 800)
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        self._stack = QStackedWidget()
        self._panels = {
            "download": DownloadPanel(),
            "split": SplitPanel(),
            "process": ProcessPanel(),
            "convert": ConvertPanel(),
            "publish": PublishPanel(),
        }
        for panel in self._panels.values():
            self._stack.addWidget(panel)

        self._log_panel = QTextEdit()
        self._log_panel.setReadOnly(True)
        self._log_panel.setMaximumHeight(150)

        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.addWidget(self._stack)
        right_splitter.addWidget(self._log_panel)
        right_splitter.setStretchFactor(0, 4)
        right_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(right_splitter)
        self.switch_panel("download")

    def _setup_menu(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menu_bar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(lambda: QMessageBox.about(self, "关于", "OSM Data Toolbox v0.1.0\nOSM 数据下载、处理、转换、发布工具"))
        help_menu.addAction(about_action)

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("功能切换")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        for label, key in [("下载数据", "download"), ("数据拆分", "split"), ("数据处理", "process"), ("格式转换", "convert"), ("矢量切片", "publish")]:
            btn = toolbar.addAction(label)
            btn.triggered.connect(lambda checked, k=key: self.switch_panel(k))

    def _setup_statusbar(self) -> None:
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("就绪")

    def switch_panel(self, name: str) -> None:
        if name in self._panels:
            self._stack.setCurrentWidget(self._panels[name])
            self._statusbar.showMessage(f"当前: {name}")
            logger.info(f"切换到面板: {name}")

    def log_message(self, msg: str, level: str = "info") -> None:
        color = {"info": "#333", "warning": "#c90", "error": "#c00"}.get(level, "#333")
        self._log_panel.append(f'<span style="color:{color}">{msg}</span>')
