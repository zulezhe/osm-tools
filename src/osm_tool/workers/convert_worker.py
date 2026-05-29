"""格式转换工作线程"""
import threading

from osm_tool.core.converter.manager import ConversionManager


class ConvertWorker:
    """异步执行格式转换"""

    def __init__(
        self,
        input_path: str,
        output_path: str,
        output_format=None,
        options: dict | None = None,
        on_progress=None,
        on_complete=None,
        on_error=None,
    ):
        self._input_path = input_path
        self._output_path = output_path
        self._output_format = output_format
        self._options = options
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_error = on_error
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            mgr = ConversionManager()
            result = mgr.convert(self._input_path, self._output_path, self._output_format, self._options)
            if result.success:
                if self._on_complete:
                    self._on_complete(result)
            else:
                if self._on_error:
                    self._on_error(result.error_message or "转换失败")
        except Exception as e:
            if self._on_error:
                self._on_error(str(e))
