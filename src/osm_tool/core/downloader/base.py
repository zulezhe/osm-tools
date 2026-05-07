"""下载器抽象基类"""
from abc import ABC, abstractmethod
from typing import Callable

from src.osm_tool.models.download_task import DownloadTask
from src.osm_tool.models.task_state import TaskState


class BaseDownloader(ABC):
    """下载器抽象基类"""

    def __init__(
        self,
        task: DownloadTask,
        on_progress: Callable[[int, int, float], None] | None = None,
        on_state_change: Callable[[TaskState], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        self._task = task
        self._on_progress = on_progress
        self._on_state_change = on_state_change
        self._on_error = on_error
        self._is_cancelled = False
        self._is_paused = False

    @property
    def task(self) -> DownloadTask:
        return self._task

    @abstractmethod
    def download(self) -> None:
        """执行下载"""
        ...

    def cancel(self) -> None:
        self._is_cancelled = True
        self._set_state(TaskState.CANCELLED)

    def pause(self) -> None:
        self._is_paused = True
        self._set_state(TaskState.PAUSED)

    def resume(self) -> None:
        self._is_paused = False
        self._set_state(TaskState.DOWNLOADING)

    def _set_state(self, state: TaskState) -> None:
        self._task.state = state
        if self._on_state_change:
            self._on_state_change(state)

    def _report_progress(self, downloaded: int, total: int, speed: float) -> None:
        self._task.downloaded_bytes = downloaded
        self._task.total_bytes = total
        if self._on_progress:
            self._on_progress(downloaded, total, speed)

    def _report_error(self, msg: str) -> None:
        self._task.error_message = msg
        self._set_state(TaskState.FAILED)
        if self._on_error:
            self._on_error(msg)
