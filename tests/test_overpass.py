"""Overpass 下载器测试"""
from unittest.mock import patch, MagicMock

from src.osm_tool.core.downloader.overpass import OverpassDownloader
from src.osm_tool.models.download_task import DownloadTask
from src.osm_tool.models.task_state import TaskState


def test_overpass_download(tmp_dir):
    save_path = str(tmp_dir / "overpass.json")
    task = DownloadTask(url="https://overpass-api.de/api/interpreter", save_path=save_path, source_type="overpass")

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [b'{"elements":[]}']
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        dl = OverpassDownloader(task=task, query="[out:json];way(around:100,39.9,116.4);out;")
        dl.download()

    assert task.state == TaskState.COMPLETED


def test_overpass_cancel(tmp_dir):
    save_path = str(tmp_dir / "overpass.json")
    task = DownloadTask(url="https://overpass-api.de/api/interpreter", save_path=save_path, source_type="overpass")
    dl = OverpassDownloader(task=task, query="[out:json];way(around:100,39.9,116.4);out;")
    dl.cancel()
    assert task.state == TaskState.CANCELLED
