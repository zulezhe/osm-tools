"""格式转换工作线程"""
from PySide6.QtCore import QThread, Signal

from src.osm_tool.core.converter.manager import ConversionManager


class ConvertWorker(QThread):
    """异步执行格式转换"""

    progress = Signal(int)
    finished_ok = Signal(object)
    error = Signal(str)

    def __init__(self, input_path: str, output_path: str, output_format=None, options: dict | None = None, parent=None):
        super().__init__(parent)
        self._input_path = input_path
        self._output_path = output_path
        self._output_format = output_format
        self._options = options

    def run(self) -> None:
        try:
            mgr = ConversionManager()
            result = mgr.convert(self._input_path, self._output_path, self._output_format, self._options)
            if result.success:
                self.finished_ok.emit(result)
            else:
                self.error.emit(result.error_message or "转换失败")
        except Exception as e:
            self.error.emit(str(e))
