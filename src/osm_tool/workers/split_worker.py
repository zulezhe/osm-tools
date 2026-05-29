"""数据拆分工作线程"""
import threading

from osm_tool.core.splitter.base import BaseSplitter


class SplitWorker:
    """异步执行数据拆分"""

    def __init__(
        self,
        splitter: BaseSplitter,
        input_path: str,
        output_dir: str,
        options: dict | None = None,
        on_progress=None,
        on_complete=None,
        on_error=None,
    ):
        self._splitter = splitter
        self._input = input_path
        self._output_dir = output_dir
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
            if self._on_progress:
                self._splitter._on_progress = self._on_progress
            result = self._splitter.split(self._input, self._output_dir, self._options)
            if self._on_complete:
                self._on_complete(result)
        except Exception as e:
            if self._on_error:
                self._on_error(str(e))
