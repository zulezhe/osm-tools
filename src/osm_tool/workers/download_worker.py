"""下载工作线程"""
import threading

from osm_tool.core.downloader.base import BaseDownloader
from osm_tool.models.task_state import TaskState


class DownloadWorker:
    """异步下载工作线程"""

    def __init__(
        self,
        downloader: BaseDownloader,
        on_progress=None,
        on_complete=None,
        on_error=None,
        on_state_change=None,
    ):
        self._downloader = downloader
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_error = on_error
        self._on_state_change = on_state_change
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            self._downloader.download()
            state = self._downloader.task.state
            if state == TaskState.COMPLETED:
                if self._on_complete:
                    self._on_complete(self._downloader.task.save_path)
            elif state == TaskState.FAILED:
                if self._on_error:
                    self._on_error(self._downloader.task.error_message or "下载失败")
        except Exception as e:
            if self._on_error:
                self._on_error(str(e))

    def cancel(self) -> None:
        self._downloader.cancel()

    def pause(self) -> None:
        self._downloader.pause()

    def resume(self) -> None:
        self._downloader.resume()
