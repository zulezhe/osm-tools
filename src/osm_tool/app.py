"""应用配置"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.osm_tool.ui.main_window import MainWindow
from src.osm_tool.utils.logger import setup_logger


class OSMToolApp(QApplication):
    """OSM Data Toolbox 应用"""

    def __init__(self, argv=None):
        super().__init__(argv or [])
        self.setApplicationName("OSM Data Toolbox")
        self.setApplicationVersion("0.1.0")

        log_path = Path.home() / ".osm_tool" / "app.log"
        self._logger = setup_logger("osm_tool", log_file=log_path)
        self._logger.info("应用启动")

        self._main_window = MainWindow()
        self._main_window.show()

    @property
    def main_window(self) -> MainWindow:
        return self._main_window
