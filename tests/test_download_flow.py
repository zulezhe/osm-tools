"""下载功能端到端测试

测试场景:
1. Overpass 查询生成 + 下载启动
2. Geofabrik 下载启动
3. 完整 Overpass 下载流程 (mock HTTP)
4. 完整 Geofabrik 下载流程 (mock HTTP)
5. 任务管理器生命周期
"""
import time
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from osm_tool.app import create_app
from osm_tool.api.task_manager import task_manager, TaskInfo
from osm_tool.models.download_task import DownloadTask
from osm_tool.models.task_state import TaskState
from osm_tool.core.downloader.overpass import OverpassDownloader


@pytest.fixture
def client():
    """FastAPI 测试客户端"""
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_tasks():
    """每个测试前后清空任务管理器"""
    task_manager._tasks.clear()
    yield
    task_manager._tasks.clear()


# ── 1. API 路由测试 ──

class TestOverpassQueryAPI:
    """Overpass 查询生成 API"""

    def test_generate_bbox_query(self, client):
        """测试 bbox 查询生成"""
        resp = client.post("/api/v1/download/overpass/query", json={
            "type": "bbox",
            "output_format": "json",
            "left": 116.0,
            "bottom": 39.0,
            "right": 117.0,
            "top": 40.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "query" in data["data"]
        assert "[out:json]" in data["data"]["query"]
        assert "node(39.0,116.0,40.0,117.0)" in data["data"]["query"]

    def test_generate_polygon_query(self, client):
        """测试多边形查询生成"""
        resp = client.post("/api/v1/download/overpass/query", json={
            "type": "polygon",
            "output_format": "json",
            "coordinates": [[116.0, 39.0], [117.0, 39.0], [117.0, 40.0], [116.0, 40.0]],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "poly:" in data["data"]["query"]

    def test_generate_circle_query(self, client):
        """测试圆形查询生成"""
        resp = client.post("/api/v1/download/overpass/query", json={
            "type": "circle",
            "output_format": "xml",
            "center_lat": 39.9,
            "center_lng": 116.4,
            "radius": 1000,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "around:1000,39.9,116.4" in data["data"]["query"]
        assert "[out:xml]" in data["data"]["query"]

    def test_query_missing_params(self, client):
        """测试缺少参数"""
        resp = client.post("/api/v1/download/overpass/query", json={
            "type": "bbox",
        })
        data = resp.json()
        assert data["code"] == 1


class TestOverpassDownloadAPI:
    """Overpass 下载启动 API"""

    @patch("osm_tool.workers.download_worker.DownloadWorker.start")
    def test_start_overpass_download(self, mock_start, client, tmp_dir):
        """测试启动 Overpass 下载"""
        save_path = str(tmp_dir / "test_overpass.json")
        resp = client.post("/api/v1/download/overpass/start", json={
            "query": "[out:json];node(39.0,116.0,40.0,117.0);out body;>;out skel qt;",
            "save_path": save_path,
            "output_format": "json",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "task_id" in data["data"]

        # 验证任务已创建
        task_id = data["data"]["task_id"]
        task = task_manager.get_task(task_id)
        assert task is not None
        assert task.task_type == "download"
        assert task.status == TaskState.PENDING.value

    def test_start_overpass_missing_query(self, client):
        """测试缺少 query 参数"""
        resp = client.post("/api/v1/download/overpass/start", json={
            "save_path": "/tmp/test.json",
        })
        data = resp.json()
        assert data["code"] == 1

    def test_start_overpass_missing_save_path(self, client):
        """测试缺少 save_path 参数"""
        resp = client.post("/api/v1/download/overpass/start", json={
            "query": "[out:json];node(39,116,40,117);out;",
        })
        data = resp.json()
        assert data["code"] == 1


class TestGeofabrikDownloadAPI:
    """Geofabrik 下载启动 API"""

    @patch("osm_tool.workers.download_worker.DownloadWorker.start")
    def test_start_geofabrik_download(self, mock_start, client, tmp_dir):
        """测试启动 Geofabrik 下载"""
        save_path = str(tmp_dir / "test_geofabrik.pbf")
        resp = client.post("/api/v1/download/geofabrik/start", json={
            "url": "https://download.geofabrik.de/asia/china-latest.osm.pbf",
            "save_path": save_path,
            "region_name": "中国",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "task_id" in data["data"]

    def test_start_geofabrik_missing_url(self, client):
        """测试缺少 url"""
        resp = client.post("/api/v1/download/geofabrik/start", json={
            "save_path": "/tmp/test.pbf",
        })
        data = resp.json()
        assert data["code"] == 1


class TestConfigAPI:
    """配置 API"""

    def test_default_save_path(self, client):
        """测试默认保存路径"""
        resp = client.get("/api/v1/download/config/default-save-path")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "path" in data["data"]
        assert "outdata" in data["data"]["path"]


class TestTasksAPI:
    """任务管理 API"""

    @patch("osm_tool.workers.download_worker.DownloadWorker.start")
    def test_list_tasks(self, mock_start, client, tmp_dir):
        """测试列出任务"""
        save_path = str(tmp_dir / "test.json")
        # 创建一个任务
        client.post("/api/v1/download/overpass/start", json={
            "query": "[out:json];node(39,116,40,117);out;",
            "save_path": save_path,
        })
        # 查询任务列表
        resp = client.get("/api/v1/download/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert len(data["data"]) >= 1

    @patch("osm_tool.workers.download_worker.DownloadWorker.start")
    def test_cancel_task(self, mock_start, client, tmp_dir):
        """测试取消任务"""
        save_path = str(tmp_dir / "test.json")
        resp = client.post("/api/v1/download/overpass/start", json={
            "query": "[out:json];node(39,116,40,117);out;",
            "save_path": save_path,
        })
        task_id = resp.json()["data"]["task_id"]

        resp = client.post(f"/api/v1/download/tasks/{task_id}/cancel")
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["cancelled"] is True


# ── 2. Overpass 下载器集成测试 ──

class TestOverpassDownloaderIntegration:
    """Overpass 下载器完整流程"""

    def test_full_download_flow(self, tmp_dir):
        """测试完整 Overpass 下载流程 (mock HTTP)"""
        save_path = str(tmp_dir / "overpass_result.json")
        task = DownloadTask(
            url="https://overpass-api.de/api/interpreter",
            save_path=save_path,
            source_type="overpass",
        )

        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [b'{"elements":[],"version":0.6}']
        mock_resp.raise_for_status = MagicMock()
        mock_resp.headers = {"content-length": "36"}

        with patch("requests.post", return_value=mock_resp) as mock_post:
            dl = OverpassDownloader(task=task, query="[out:json];node(39,116,40,117);out body;>;out skel qt;")
            dl.download()

            # 验证 HTTP 请求正确
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args
            assert call_kwargs[1]["headers"]["User-Agent"] == "OSM-Tool/0.1"
            assert "data" in call_kwargs[1]

        # 验证状态
        assert task.state == TaskState.COMPLETED
        assert task.downloaded_bytes > 0

        # 验证文件
        with open(save_path) as f:
            content = f.read()
        assert "elements" in content

    def test_download_with_timeout(self, tmp_dir):
        """测试下载超时"""
        import requests

        save_path = str(tmp_dir / "timeout.json")
        task = DownloadTask(
            url="https://overpass-api.de/api/interpreter",
            save_path=save_path,
            source_type="overpass",
        )

        with patch("requests.post", side_effect=requests.exceptions.Timeout()):
            dl = OverpassDownloader(task=task, query="[out:json];node(39,116,40,117);out;")
            dl.download()

        assert task.state == TaskState.FAILED
        assert "超时" in task.error_message


# ── 3. Geofabrik 下载器集成测试 ──

class TestGeofabrikDownloaderIntegration:
    """Geofabrik 下载器完整流程"""

    def test_full_download_flow(self, tmp_dir):
        """测试完整 Geofabrik 下载流程 (mock HTTP)"""
        from osm_tool.core.downloader.geofabrik import GeofabrikDownloader

        save_path = str(tmp_dir / "china.osm.pbf")
        task = DownloadTask(
            url="https://download.geofabrik.de/asia/china-latest.osm.pbf",
            save_path=save_path,
            source_type="geofabrik",
        )

        # mock PBF 数据
        pbf_data = b"\x00" * 1024
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [pbf_data]
        mock_resp.raise_for_status = MagicMock()
        mock_resp.headers = {"content-length": "1024"}

        with patch("requests.get", return_value=mock_resp) as mock_get:
            dl = GeofabrikDownloader(task=task)
            dl.download()

            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args
            assert "User-Agent" in call_kwargs[1]["headers"]

        assert task.state == TaskState.COMPLETED
        assert task.downloaded_bytes == 1024
        assert (tmp_dir / "china.osm.pbf").exists()


# ── 4. Worker 集成测试 ──

class TestDownloadWorkerIntegration:
    """下载工作线程集成测试"""

    def test_worker_completes(self, tmp_dir):
        """测试 worker 完成下载"""
        from osm_tool.workers.download_worker import DownloadWorker
        from osm_tool.core.downloader.overpass import OverpassDownloader

        save_path = str(tmp_dir / "worker_test.json")
        task = DownloadTask(
            url="https://overpass-api.de/api/interpreter",
            save_path=save_path,
            source_type="overpass",
        )

        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [b'{"elements":[]}']
        mock_resp.raise_for_status = MagicMock()
        mock_resp.headers = {"content-length": "16"}

        results = {"completed": None, "error": None}

        with patch("requests.post", return_value=mock_resp):
            dl = OverpassDownloader(task=task, query="[out:json];node(39,116,40,117);out;")
            worker = DownloadWorker(
                dl,
                on_complete=lambda p: results.update({"completed": p}),
                on_error=lambda e: results.update({"error": e}),
            )
            worker.start()
            # 等待线程完成
            if worker._thread:
                worker._thread.join(timeout=5)

        assert results["completed"] is not None
        assert results["error"] is None
        assert task.state == TaskState.COMPLETED

    def test_worker_handles_error(self, tmp_dir):
        """测试 worker 处理错误"""
        from osm_tool.workers.download_worker import DownloadWorker
        from osm_tool.core.downloader.overpass import OverpassDownloader
        import requests

        save_path = str(tmp_dir / "error_test.json")
        task = DownloadTask(
            url="https://overpass-api.de/api/interpreter",
            save_path=save_path,
            source_type="overpass",
        )

        results = {"completed": None, "error": None}

        with patch("requests.post", side_effect=requests.exceptions.Timeout()):
            dl = OverpassDownloader(task=task, query="[out:json];node(39,116,40,117);out;")
            worker = DownloadWorker(
                dl,
                on_complete=lambda p: results.update({"completed": p}),
                on_error=lambda e: results.update({"error": e}),
            )
            worker.start()
            if worker._thread:
                worker._thread.join(timeout=5)

        assert results["completed"] is None
        assert results["error"] is not None


# ── 5. 完整 API 集成流程测试 ──

class TestFullAPIFlow:
    """完整 API 集成流程: 查询生成 → 启动下载 → 查询状态"""

    @patch("osm_tool.workers.download_worker.DownloadWorker.start")
    def test_overpass_full_flow(self, mock_start, client, tmp_dir):
        """测试 Overpass 完整流程"""
        # Step 1: 生成查询
        query_resp = client.post("/api/v1/download/overpass/query", json={
            "type": "bbox",
            "output_format": "json",
            "left": 116.3,
            "bottom": 39.8,
            "right": 116.5,
            "top": 40.0,
        })
        assert query_resp.json()["code"] == 0
        query = query_resp.json()["data"]["query"]
        assert "[out:json]" in query

        # Step 2: 启动下载
        save_path = str(tmp_dir / "full_flow.json")
        start_resp = client.post("/api/v1/download/overpass/start", json={
            "query": query,
            "save_path": save_path,
            "output_format": "json",
        })
        assert start_resp.json()["code"] == 0
        task_id = start_resp.json()["data"]["task_id"]

        # Step 3: 查询任务状态
        tasks_resp = client.get("/api/v1/download/tasks")
        tasks = tasks_resp.json()["data"]
        task = next(t for t in tasks if t["task_id"] == task_id)
        assert task["task_type"] == "download"

    @patch("osm_tool.workers.download_worker.DownloadWorker.start")
    def test_geofabrik_full_flow(self, mock_start, client, tmp_dir):
        """测试 Geofabrik 完整流程"""
        save_path = str(tmp_dir / "geofabrik_flow.pbf")
        start_resp = client.post("/api/v1/download/geofabrik/start", json={
            "url": "https://download.geofabrik.de/asia/china-latest.osm.pbf",
            "save_path": save_path,
            "region_name": "中国",
        })
        assert start_resp.json()["code"] == 0
        task_id = start_resp.json()["data"]["task_id"]

        # 查询任务
        tasks_resp = client.get("/api/v1/download/tasks")
        tasks = tasks_resp.json()["data"]
        task = next(t for t in tasks if t["task_id"] == task_id)
        assert task is not None

        # 取消任务
        cancel_resp = client.post(f"/api/v1/download/tasks/{task_id}/cancel")
        assert cancel_resp.json()["code"] == 0
