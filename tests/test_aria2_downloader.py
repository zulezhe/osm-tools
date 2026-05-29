"""快速下载器测试 - aria2 + Python 多线程"""
import time
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest

from osm_tool.core.downloader.aria2_downloader import Aria2Downloader, is_aria2_available
from osm_tool.models.download_task import DownloadTask
from osm_tool.models.task_state import TaskState


@pytest.fixture
def mock_task(tmp_dir):
    return DownloadTask(
        url="https://download.geofabrik.de/asia/china-latest.osm.pbf",
        save_path=str(tmp_dir / "test.pbf"),
        source_type="geofabrik",
    )


# ── aria2c 可用性检测 ──

class TestAria2Detection:
    def test_available(self):
        with patch("shutil.which", return_value="/usr/bin/aria2c"):
            assert is_aria2_available() is True

    def test_not_available(self):
        with patch("shutil.which", return_value=None):
            assert is_aria2_available() is False


# ── aria2c 下载流程 ──

class TestAria2Download:
    @patch("osm_tool.core.downloader.aria2_downloader.is_aria2_available", return_value=True)
    def test_aria2_download_success(self, mock_avail, mock_task, tmp_dir):
        """测试 aria2c 下载成功"""
        save_path = tmp_dir / "test.pbf"
        save_path.write_bytes(b"\x00" * 1024)

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdout = iter([
            "FILE: test.pbf\n",
            "(20%)\n",
            "(50%)\n",
            "(100%)\n",
        ])
        mock_proc.wait.return_value = 0

        with patch("subprocess.Popen", return_value=mock_proc):
            dl = Aria2Downloader(task=mock_task)
            dl.download()

        assert mock_task.state == TaskState.COMPLETED
        assert mock_task.downloaded_bytes == 1024

    @patch("osm_tool.core.downloader.aria2_downloader.is_aria2_available", return_value=True)
    def test_aria2_download_failure(self, mock_avail, mock_task):
        """测试 aria2c 下载失败"""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdout = iter([])
        mock_proc.wait.return_value = 1

        with patch("subprocess.Popen", return_value=mock_proc):
            dl = Aria2Downloader(task=mock_task)
            dl.download()

        assert mock_task.state == TaskState.FAILED

    @patch("osm_tool.core.downloader.aria2_downloader.is_aria2_available", return_value=True)
    def test_aria2_cancel(self, mock_avail, mock_task):
        """测试 aria2c 取消"""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdout = iter([])
        mock_proc.wait.return_value = -9

        with patch("subprocess.Popen", return_value=mock_proc):
            dl = Aria2Downloader(task=mock_task)
            dl._process = mock_proc
            dl.cancel()

        assert mock_task.state == TaskState.CANCELLED
        mock_proc.terminate.assert_called()

    @patch("osm_tool.core.downloader.aria2_downloader.is_aria2_available", return_value=True)
    def test_aria2_progress_parsing(self, mock_avail, mock_task, tmp_dir):
        """测试 aria2c 进度解析"""
        save_path = tmp_dir / "test.pbf"
        save_path.write_bytes(b"\x00" * 2048)

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdout = iter([
            "[#a1b2c3 1.2MiB/5.0MiB(24%) CN:8 DL:2.5MiB ETA:1s]\n",
            "[#a1b2c3 3.0MiB/5.0MiB(60%) CN:8 DL:3.1MiB ETA:0s]\n",
            "[#a1b2c3 5.0MiB/5.0MiB(100%)]\n",
        ])
        mock_proc.wait.return_value = 0

        with patch("subprocess.Popen", return_value=mock_proc):
            dl = Aria2Downloader(task=mock_task)
            dl.download()

        assert mock_task.state == TaskState.COMPLETED


# ── Python 多线程下载（aria2c 不可用时）──

class TestThreadedFallback:
    @patch("osm_tool.core.downloader.aria2_downloader.is_aria2_available", return_value=False)
    def test_threaded_download_success(self, mock_avail, mock_task, tmp_dir):
        """测试多线程下载成功"""
        save_path = tmp_dir / "test.pbf"
        test_data = b"\xAB" * (4 * 1024 * 1024)  # 4MB

        # mock HEAD 请求返回支持 Range
        mock_head_resp = MagicMock()
        mock_head_resp.headers = {
            "content-length": str(len(test_data)),
            "accept-ranges": "bytes",
        }
        mock_head_resp.raise_for_status = MagicMock()

        # mock GET 请求返回分段数据
        def mock_get(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            range_header = kwargs.get("headers", {}).get("Range", "")
            if range_header:
                # 解析 Range: bytes=start-end
                import re
                m = re.match(r'bytes=(\d+)-(\d+)', range_header)
                if m:
                    start, end = int(m.group(1)), int(m.group(2))
                    chunk = test_data[start:end + 1]
                else:
                    chunk = test_data
            else:
                chunk = test_data
            resp.iter_content = MagicMock(return_value=[chunk])
            resp.headers = {"content-length": str(len(test_data))}
            return resp

        with patch("requests.head", return_value=mock_head_resp), \
             patch("requests.get", side_effect=mock_get):
            dl = Aria2Downloader(task=mock_task)
            dl.download()

        assert mock_task.state == TaskState.COMPLETED
        save_path = Path(mock_task.save_path)
        assert save_path.exists()
        assert save_path.stat().st_size == len(test_data)

    @patch("osm_tool.core.downloader.aria2_downloader.is_aria2_available", return_value=False)
    def test_threaded_fallback_no_range(self, mock_avail, mock_task, tmp_dir):
        """测试服务器不支持 Range 时降级到单线程"""
        test_data = b"\xCD" * 1024

        mock_head_resp = MagicMock()
        mock_head_resp.headers = {
            "content-length": str(len(test_data)),
            "accept-ranges": "none",
        }
        mock_head_resp.raise_for_status = MagicMock()

        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [test_data]
        mock_resp.raise_for_status = MagicMock()
        mock_resp.headers = {"content-length": str(len(test_data))}

        with patch("requests.head", return_value=mock_head_resp), \
             patch("requests.get", return_value=mock_resp):
            dl = Aria2Downloader(task=mock_task)
            dl.download()

        assert mock_task.state == TaskState.COMPLETED
        assert Path(mock_task.save_path).stat().st_size == 1024

    @patch("osm_tool.core.downloader.aria2_downloader.is_aria2_available", return_value=False)
    def test_threaded_cancel(self, mock_avail, mock_task):
        """测试多线程取消"""
        dl = Aria2Downloader(task=mock_task)
        dl._is_cancelled = False
        dl.cancel()
        assert mock_task.state == TaskState.CANCELLED


# ── Worker 集成测试 ──

class TestFastDownloadWorker:
    @patch("osm_tool.core.downloader.aria2_downloader.is_aria2_available", return_value=False)
    def test_worker_with_threaded(self, mock_avail, tmp_dir):
        """测试 Worker + 多线程下载"""
        from osm_tool.workers.download_worker import DownloadWorker

        save_path = tmp_dir / "worker_test.pbf"
        test_data = b"\x00" * (2 * 1024 * 1024)
        task = DownloadTask(
            url="https://example.com/test.pbf",
            save_path=str(save_path),
            source_type="geofabrik",
        )

        mock_head_resp = MagicMock()
        mock_head_resp.headers = {"content-length": str(len(test_data)), "accept-ranges": "bytes"}
        mock_head_resp.raise_for_status = MagicMock()

        def mock_get(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            range_h = kwargs.get("headers", {}).get("Range", "")
            if range_h:
                import re
                m = re.match(r'bytes=(\d+)-(\d+)', range_h)
                chunk = test_data[int(m.group(1)):int(m.group(2))+1] if m else test_data
            else:
                chunk = test_data
            resp.iter_content = MagicMock(return_value=[chunk])
            return resp

        results = {"done": None, "error": None}

        with patch("requests.head", return_value=mock_head_resp), \
             patch("requests.get", side_effect=mock_get):
            dl = Aria2Downloader(task=task)
            worker = DownloadWorker(
                dl,
                on_complete=lambda p: results.update({"done": p}),
                on_error=lambda e: results.update({"error": e}),
            )
            worker.start()
            if worker._thread:
                worker._thread.join(timeout=10)

        assert results["done"] is not None
        assert results["error"] is None
        assert task.state == TaskState.COMPLETED


# ── API 路由集成测试 ──

class TestFastDownloadAPI:
    @patch("osm_tool.workers.download_worker.DownloadWorker.start")
    def test_geofabrik_uses_fast_downloader(self, mock_start):
        """测试 Geofabrik API 使用快速下载器"""
        from fastapi.testclient import TestClient
        from osm_tool.app import create_app
        from osm_tool.api.task_manager import task_manager
        import tempfile

        task_manager._tasks.clear()
        try:
            app = create_app()
            client = TestClient(app)
            with tempfile.TemporaryDirectory() as tmp:
                resp = client.post("/api/v1/download/geofabrik/start", json={
                    "url": "https://download.geofabrik.de/asia/china-latest.osm.pbf",
                    "save_path": f"{tmp}/china.pbf",
                    "region_name": "中国",
                })
                data = resp.json()
                assert data["code"] == 0
                assert "task_id" in data["data"]
        finally:
            task_manager._tasks.clear()
