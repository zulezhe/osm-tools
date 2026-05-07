"""BBox 下载器"""
from pathlib import Path

import requests

from src.osm_tool.core.downloader.base import BaseDownloader
from src.osm_tool.models.task_state import TaskState

MAX_BBOX_AREA = 0.25


class BBoxDownloader(BaseDownloader):
    """按经纬度范围下载 OSM 数据"""

    CHUNK_SIZE = 1024 * 64

    def __init__(self, task, left: float, bottom: float, right: float, top: float, **kwargs):
        super().__init__(task, **kwargs)
        self._left = left
        self._bottom = bottom
        self._right = right
        self._top = top

    def download(self) -> None:
        area = (self._right - self._left) * (self._top - self._bottom)
        if area > MAX_BBOX_AREA:
            self._report_error(
                f"请求区域面积 ({area:.2f}°²) 过大，OSM API 限制为 {MAX_BBOX_AREA}°²。"
                f"请缩小范围或使用 Geofabrik 下载。"
            )
            return

        self._set_state(TaskState.DOWNLOADING)
        save_path = Path(self._task.save_path)

        bbox = f"{self._left},{self._bottom},{self._right},{self._top}"
        url = f"{self._task.url}?bbox={bbox}"

        try:
            resp = requests.get(url, stream=True, timeout=120)
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            self._task.total_bytes = total
            downloaded = 0

            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=self.CHUNK_SIZE):
                    if self._is_cancelled:
                        return
                    f.write(chunk)
                    downloaded += len(chunk)
                    self._report_progress(downloaded, total, 0)

            self._task.downloaded_bytes = downloaded
            self._set_state(TaskState.COMPLETED)

        except Exception as e:
            self._report_error(str(e))
