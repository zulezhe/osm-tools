"""数据模型测试"""
from pathlib import Path

from src.osm_tool.models.task_state import TaskState
from src.osm_tool.models.download_task import DownloadTask


def test_task_state_values():
    assert TaskState.PENDING.value == "pending"
    assert TaskState.DOWNLOADING.value == "downloading"
    assert TaskState.PAUSED.value == "paused"
    assert TaskState.COMPLETED.value == "completed"
    assert TaskState.FAILED.value == "failed"
    assert TaskState.CANCELLED.value == "cancelled"


def test_create_download_task():
    task = DownloadTask(
        url="https://example.com/test.osm.pbf",
        save_path="/tmp/test.osm.pbf",
        source_type="geofabrik",
    )
    assert task.url == "https://example.com/test.osm.pbf"
    assert task.source_type == "geofabrik"
    assert task.state == TaskState.PENDING
    assert task.total_bytes == 0
    assert task.progress == 0.0


def test_download_task_progress():
    task = DownloadTask(
        url="https://example.com/test.osm.pbf",
        save_path="/tmp/test.osm.pbf",
        source_type="geofabrik",
        total_bytes=1000,
        downloaded_bytes=500,
    )
    assert task.progress == 50.0


def test_download_task_to_meta(tmp_dir):
    task = DownloadTask(
        url="https://example.com/test.osm.pbf",
        save_path=str(tmp_dir / "test.osm.pbf"),
        source_type="geofabrik",
        total_bytes=1000,
        downloaded_bytes=500,
        etag="abc123",
    )
    meta_path = task.to_meta_file()
    assert meta_path.exists()

    loaded = DownloadTask.from_meta_file(meta_path)
    assert loaded.url == task.url
    assert loaded.total_bytes == task.total_bytes
    assert loaded.downloaded_bytes == task.downloaded_bytes
    assert loaded.etag == task.etag
