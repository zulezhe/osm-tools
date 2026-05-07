"""BBox 下载器测试"""
from unittest.mock import patch, MagicMock

from src.osm_tool.core.downloader.bbox import BBoxDownloader
from src.osm_tool.models.download_task import DownloadTask
from src.osm_tool.models.task_state import TaskState


def test_bbox_download(tmp_dir):
    save_path = str(tmp_dir / "bbox.osm")
    task = DownloadTask(url="https://api.openstreetmap.org/api/0.6/map", save_path=save_path, source_type="bbox")

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "200"}
        mock_resp.iter_content.return_value = [b"x" * 200]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        dl = BBoxDownloader(task=task, left=116.3, bottom=39.8, right=116.5, top=40.0)
        dl.download()

    assert task.state == TaskState.COMPLETED
    assert task.downloaded_bytes == 200


def test_bbox_area_too_large(tmp_dir):
    save_path = str(tmp_dir / "bbox.osm")
    task = DownloadTask(url="https://api.openstreetmap.org/api/0.6/map", save_path=save_path, source_type="bbox")
    dl = BBoxDownloader(task=task, left=116.0, bottom=39.0, right=117.0, top=40.0)
    dl.download()
    assert task.state == TaskState.FAILED
    assert "过大" in task.error_message
