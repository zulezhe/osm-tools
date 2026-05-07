"""Geofabrik 下载器测试"""
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.osm_tool.core.downloader.geofabrik import (
    GeofabrikDownloader, GeofabrikIndex, RegionInfo,
)
from src.osm_tool.models.download_task import DownloadTask
from src.osm_tool.models.task_state import TaskState


def test_region_info_creation():
    region = RegionInfo(id="china", name="China", parent_id="asia", url="https://download.geofabrik.de/asia/china-latest.osm.pbf", size_bytes=1000000)
    assert region.id == "china"
    assert region.name == "China"


def test_geofabrik_index_parse():
    mock_data = {
        "features": [
            {"properties": {"id": "asia", "name": "Asia", "parent": None, "urls": {"pbf": "https://download.geofabrik.de/asia-latest.osm.pbf"}, "size": 5000000000}},
            {"properties": {"id": "china", "name": "China", "parent": "asia", "urls": {"pbf": "https://download.geofabrik.de/asia/china-latest.osm.pbf"}, "size": 1000000000}},
        ]
    }
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        index = GeofabrikIndex()
        regions = index.fetch_index()

    assert len(regions) == 2
    assert regions[0].id == "asia"
    assert regions[1].parent_id == "asia"


def test_geofabrik_download_new(tmp_dir):
    save_path = str(tmp_dir / "test.osm.pbf")
    task = DownloadTask(url="https://example.com/test.osm.pbf", save_path=save_path, source_type="geofabrik")

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"x" * 100]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        states = []
        dl = GeofabrikDownloader(task=task, on_state_change=lambda s: states.append(s))
        dl.download()

    assert task.state == TaskState.COMPLETED
    assert Path(save_path).exists()
    assert task.downloaded_bytes == 100


def test_geofabrik_resume(tmp_dir):
    save_path = str(tmp_dir / "test.osm.pbf")
    Path(save_path).write_bytes(b"x" * 50)

    task = DownloadTask(url="https://example.com/test.osm.pbf", save_path=save_path, source_type="geofabrik", total_bytes=100, downloaded_bytes=50)

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "50"}
        mock_resp.iter_content.return_value = [b"y" * 50]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        dl = GeofabrikDownloader(task=task)
        dl.download()

    assert task.state == TaskState.COMPLETED
    assert len(Path(save_path).read_bytes()) == 100
