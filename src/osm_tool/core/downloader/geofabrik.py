"""Geofabrik 下载器"""
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from src.osm_tool.core.downloader.base import BaseDownloader
from src.osm_tool.models.download_task import DownloadTask
from src.osm_tool.models.task_state import TaskState

GEOFABRIK_INDEX_URL = "https://download.geofabrik.de/index.json"


@dataclass
class RegionInfo:
    """Geofabrik 区域信息"""
    id: str
    name: str
    parent_id: str | None
    url: str
    size_bytes: int
    updated: str | None = None


class GeofabrikIndex:
    """Geofabrik 区域索引"""

    def __init__(self):
        self._regions: list[RegionInfo] = []

    def fetch_index(self) -> list[RegionInfo]:
        resp = requests.get(GEOFABRIK_INDEX_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        self._regions = self._parse_index(data)
        return self._regions

    def _parse_index(self, data: dict) -> list[RegionInfo]:
        regions = []
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            urls = props.get("urls", {})
            regions.append(RegionInfo(
                id=props.get("id", ""),
                name=props.get("name", ""),
                parent_id=props.get("parent"),
                url=urls.get("pbf", ""),
                size_bytes=props.get("size", 0),
            ))
        return regions

    def get_children(self, parent_id: str | None) -> list[RegionInfo]:
        return [r for r in self._regions if r.parent_id == parent_id]

    def get_region(self, region_id: str) -> RegionInfo | None:
        for r in self._regions:
            if r.id == region_id:
                return r
        return None


class GeofabrikDownloader(BaseDownloader):
    """Geofabrik 下载器，支持断点续传"""

    CHUNK_SIZE = 1024 * 64

    def download(self) -> None:
        self._set_state(TaskState.DOWNLOADING)
        save_path = Path(self._task.save_path)

        existing_size = save_path.stat().st_size if save_path.exists() else 0
        headers = {}
        if existing_size > 0:
            headers["Range"] = f"bytes={existing_size}-"

        try:
            resp = requests.get(self._task.url, headers=headers, stream=True, timeout=60)
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            if existing_size > 0 and total > 0:
                total += existing_size
            self._task.total_bytes = max(total, existing_size)

            mode = "ab" if existing_size > 0 else "wb"
            downloaded = existing_size
            start_time = time.time()

            with open(save_path, mode) as f:
                for chunk in resp.iter_content(chunk_size=self.CHUNK_SIZE):
                    if self._is_cancelled:
                        return
                    f.write(chunk)
                    downloaded += len(chunk)

                    elapsed = time.time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0
                    self._report_progress(downloaded, self._task.total_bytes, speed)

            self._task.downloaded_bytes = downloaded
            self._task.to_meta_file()
            self._set_state(TaskState.COMPLETED)

        except Exception as e:
            if save_path.exists():
                self._task.to_meta_file()
            self._report_error(str(e))
