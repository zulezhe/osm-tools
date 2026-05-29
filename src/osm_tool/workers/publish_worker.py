"""矢量切片发布工作线程"""
import threading

from osm_tool.core.publisher.base import TileConfig
from osm_tool.core.publisher.manager import PublishManager


class PublishWorker:
    """异步执行切片发布"""

    def __init__(
        self,
        input_path: str,
        output_path: str,
        config: TileConfig,
        on_progress=None,
        on_complete=None,
        on_error=None,
    ):
        self._input = input_path
        self._output = output_path
        self._config = config
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_error = on_error
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            mgr = PublishManager()
            publisher = mgr.get_publisher()
            if self._on_progress:
                publisher._on_progress = self._on_progress
            result = publisher.publish(self._input, self._output, self._config)
            if result.success:
                if self._on_complete:
                    self._on_complete(result)
            else:
                if self._on_error:
                    self._on_error(result.error_message or "发布失败")
        except Exception as e:
            if self._on_error:
                self._on_error(str(e))
