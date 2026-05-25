"""Geofabrik 下载器"""
import json
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from osm_tool.core.downloader.base import BaseDownloader
from osm_tool.models.download_task import DownloadTask
from osm_tool.models.task_state import TaskState

GEOFABRIK_INDEX_URL = "https://download.geofabrik.de/index-v1.json"
_HEADERS = {"User-Agent": "OSM-Tool/0.1", "Accept-Encoding": "gzip, deflate"}


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

    CACHE_DIR = Path.cwd() / ".cache"
    CACHE_FILE = CACHE_DIR / "geofabrik_regions.json"

    def __init__(self):
        self._regions: list[RegionInfo] = []

    def fetch_index(self, use_cache: bool = True) -> list[RegionInfo]:
        if use_cache:
            cached = self._load_cache()
            if cached is not None:
                self._regions = cached
                return self._regions

        resp = requests.get(GEOFABRIK_INDEX_URL, timeout=30, headers=_HEADERS)
        resp.raise_for_status()
        data = resp.json()
        self._regions = self._parse_index(data)
        self._save_cache()
        return self._regions

    def _load_cache(self) -> list[RegionInfo] | None:
        try:
            if not self.CACHE_FILE.exists():
                return None
            with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                items = json.load(f)
            return [RegionInfo(**item) for item in items]
        except Exception:
            return None

    def _save_cache(self) -> None:
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        items = [
            {
                "id": r.id,
                "name": r.name,
                "parent_id": r.parent_id,
                "url": r.url,
                "size_bytes": r.size_bytes,
                "updated": r.updated,
            }
            for r in self._regions
        ]
        with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

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
    """Geofabrik 下载器，支持断点续传和自动重试"""

    CHUNK_SIZE = 1024 * 256
    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 10, 20]  # 秒，指数退避

    def download(self) -> None:
        self._set_state(TaskState.DOWNLOADING)
        save_path = Path(self._task.save_path)

        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            if self._is_cancelled:
                return

            try:
                self._do_download(save_path)
                return  # 下载成功，直接返回
            except Exception as e:
                last_error = e
                if self._is_cancelled:
                    return
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAYS[attempt]
                    from osm_tool.utils.logger import setup_logger
                    setup_logger("osm_tool.geofabrik").warning(
                        f"下载失败 (第{attempt + 1}次)，{delay}秒后重试: {e}"
                    )
                    # 等待期间检查取消
                    for _ in range(delay * 10):
                        if self._is_cancelled:
                            return
                        time.sleep(0.1)
                else:
                    if save_path.exists():
                        self._task.to_meta_file()
                    self._report_error(f"下载失败（已重试{self.MAX_RETRIES}次）: {last_error}")

    def _do_download(self, save_path: Path) -> None:
        """单次下载尝试，支持断点续传"""
        existing_size = save_path.stat().st_size if save_path.exists() else 0
        headers = {}
        if existing_size > 0:
            headers["Range"] = f"bytes={existing_size}-"

        resp = requests.get(self._task.url, headers={**headers, **_HEADERS}, stream=True, timeout=600)
        resp.raise_for_status()

        # 服务器可能忽略 Range 返回 200，此时从头开始
        if resp.status_code == 200:
            total = int(resp.headers.get("content-length", 0))
            mode = "wb"
            downloaded = 0
        elif resp.status_code == 206:
            total = int(resp.headers.get("content-length", 0)) + existing_size
            mode = "ab"
            downloaded = existing_size
        else:
            resp.close()
            raise ValueError(f"意外的响应状态码: {resp.status_code}")

        self._task.total_bytes = max(total, existing_size)

        start_time = time.time()
        with open(save_path, mode) as f:
            for chunk in resp.iter_content(chunk_size=self.CHUNK_SIZE):
                if self._is_cancelled:
                    resp.close()
                    return
                f.write(chunk)
                downloaded += len(chunk)

                elapsed = time.time() - start_time
                speed = downloaded / elapsed if elapsed > 0 else 0
                self._report_progress(downloaded, self._task.total_bytes, speed)

        resp.close()
        self._task.downloaded_bytes = downloaded
        self._task.to_meta_file()
        self._set_state(TaskState.COMPLETED)
