"""Overpass API 下载器"""
from pathlib import Path

import requests

from osm_tool.core.downloader.base import BaseDownloader
from osm_tool.models.task_state import TaskState


class OverpassDownloader(BaseDownloader):
    """Overpass API 下载器"""

    CHUNK_SIZE = 1024 * 256
    HEADERS = {"User-Agent": "OSM-Tool/0.1", "Accept-Encoding": "gzip, deflate"}

    def __init__(self, task, query: str, output_format: str = "json", **kwargs):
        super().__init__(task, **kwargs)
        self._query = query
        self._output_format = output_format

    def download(self) -> None:
        self._set_state(TaskState.DOWNLOADING)
        save_path = Path(self._task.save_path)

        try:
            resp = requests.post(
                self._task.url,
                data={"data": self._query},
                headers=self.HEADERS,
                stream=True,
                timeout=600,
            )
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            self._task.total_bytes = total
            downloaded = 0
            start_time = __import__("time").time()

            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=self.CHUNK_SIZE):
                    if self._is_cancelled:
                        return
                    f.write(chunk)
                    downloaded += len(chunk)
                    elapsed = __import__("time").time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0
                    self._report_progress(downloaded, total, speed)

            self._task.downloaded_bytes = downloaded
            self._set_state(TaskState.COMPLETED)

        except requests.exceptions.Timeout:
            self._report_error("Overpass 查询超时，请缩小查询范围或稍后重试")
        except Exception as e:
            self._report_error(str(e))
