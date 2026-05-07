"""下载工作线程"""
from PySide6.QtCore import QThread, Signal

from src.osm_tool.core.downloader.base import BaseDownloader
from src.osm_tool.models.task_state import TaskState


class DownloadWorker(QThread):
    """异步下载工作线程"""

    progress = Signal(int, float, int)   # 百分比, 速度, 剩余秒数
    finished_ok = Signal(str)            # 输出路径
    error = Signal(str)                  # 错误信息
    state_changed = Signal(object)       # TaskState

    def __init__(self, downloader: BaseDownloader, parent=None):
        super().__init__(parent)
        self._downloader = downloader

    def run(self) -> None:
        try:
            self._downloader.download()
            state = self._downloader.task.state
            if state == TaskState.COMPLETED:
                self.finished_ok.emit(self._downloader.task.save_path)
            elif state == TaskState.FAILED:
                self.error.emit(self._downloader.task.error_message or "下载失败")
        except Exception as e:
            self.error.emit(str(e))

    def cancel(self) -> None:
        self._downloader.cancel()

    def pause(self) -> None:
        self._downloader.pause()

    def resume(self) -> None:
        self._downloader.resume()
