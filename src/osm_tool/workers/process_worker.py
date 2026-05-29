"""数据处理工作线程"""
import threading

from osm_tool.core.processor.base import ProcessingPipeline


class ProcessWorker:
    """异步执行数据处理"""

    def __init__(
        self,
        pipeline: ProcessingPipeline,
        input_path: str,
        output_path: str,
        on_progress=None,
        on_step_progress=None,
        on_complete=None,
        on_error=None,
    ):
        self._pipeline = pipeline
        self._input = input_path
        self._output = output_path
        self._on_progress = on_progress
        self._on_step_progress = on_step_progress
        self._on_complete = on_complete
        self._on_error = on_error
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            if self._on_step_progress:
                self._pipeline._on_step_progress = self._on_step_progress
            self._pipeline.execute(self._input, self._output)
            if self._on_complete:
                self._on_complete(self._output)
        except Exception as e:
            if self._on_error:
                self._on_error(str(e))
