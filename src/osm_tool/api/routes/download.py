"""下载相关 API 路由"""
import os
import tempfile

from fastapi import APIRouter, UploadFile, File

from osm_tool.api.task_manager import task_manager

router = APIRouter()


def _create_fast_downloader(task, info):
    """根据环境自动选择最快下载器: aria2c > Python 断点续传"""
    from osm_tool.core.downloader.aria2_downloader import Aria2Downloader, is_aria2_available
    from osm_tool.core.downloader.geofabrik import GeofabrikDownloader
    from osm_tool.utils.logger import setup_logger

    logger = setup_logger("osm_tool.download")

    on_progress = lambda d, t, s: task_manager.update_progress(
        info.task_id, round(d / t * 100, 1) if t > 0 else 0,
        downloaded_bytes=int(d), total_bytes=int(t), speed=s,
    )
    on_state_change = lambda state: task_manager.update_progress(
        info.task_id, info.progress, status=state.value
    )

    if is_aria2_available():
        logger.info("使用 aria2c 多线程下载器")
        return Aria2Downloader(
            task=task,
            on_progress=on_progress,
            on_state_change=on_state_change,
        )
    else:
        logger.info("aria2c 不可用，使用 Python 断点续传下载器")
        return GeofabrikDownloader(
            task=task,
            on_progress=on_progress,
            on_state_change=on_state_change,
        )


@router.get("/geofabrik/regions")
async def geofabrik_regions():
    """获取 Geofabrik 区域树"""
    from osm_tool.core.downloader.geofabrik import GeofabrikIndex

    try:
        index = GeofabrikIndex()
        regions = index.fetch_index(use_cache=True)
        return {
            "code": 0,
            "data": [
                {
                    "id": r.id,
                    "name": r.name,
                    "parent_id": r.parent_id,
                    "url": r.url,
                    "size_bytes": r.size_bytes,
                }
                for r in regions
            ],
        }
    except Exception as e:
        return {"code": 1, "message": str(e)}


@router.post("/geofabrik/start")
async def geofabrik_start(body: dict):
    """开始 Geofabrik 下载（自动选择最快下载器）"""
    url = body.get("url")
    save_path = body.get("save_path")
    region_name = body.get("region_name", "Geofabrik")

    if not url or not save_path:
        return {"code": 1, "message": "缺少 url 或 save_path"}

    from osm_tool.models.download_task import DownloadTask
    from osm_tool.workers.download_worker import DownloadWorker

    task = DownloadTask(url=url, save_path=save_path, source_type="geofabrik")
    info = task_manager.create_task("download", {"region_name": region_name, "save_path": save_path, "url": url, "source": "geofabrik"})

    downloader = _create_fast_downloader(task, info)

    def on_complete(path):
        task_manager.complete_task(info.task_id, result=path)

    def on_error(msg):
        task_manager.fail_task(info.task_id, error=msg)

    worker = DownloadWorker(downloader, on_complete=on_complete, on_error=on_error)
    info._cancel_fn = worker.cancel
    worker.start()

    return {"code": 0, "data": {"task_id": info.task_id}}


@router.post("/geofabrik/refresh")
async def geofabrik_refresh():
    """强制刷新 Geofabrik 区域缓存"""
    from osm_tool.core.downloader.geofabrik import GeofabrikIndex

    try:
        index = GeofabrikIndex()
        regions = index.fetch_index(use_cache=False)
        return {"code": 0, "data": {"count": len(regions)}}
    except Exception as e:
        return {"code": 1, "message": str(e)}


@router.post("/overpass/start")
async def overpass_start(body: dict):
    """开始 Overpass 查询下载"""
    query = body.get("query")
    save_path = body.get("save_path")
    output_format = body.get("output_format", "json")
    url = body.get("url", "https://overpass-api.de/api/interpreter")

    if not query or not save_path:
        return {"code": 1, "message": "缺少 query 或 save_path"}

    from osm_tool.models.download_task import DownloadTask
    from osm_tool.core.downloader.overpass import OverpassDownloader
    from osm_tool.workers.download_worker import DownloadWorker

    task = DownloadTask(url=url, save_path=save_path, source_type="overpass")
    info = task_manager.create_task("download", {"query": query, "save_path": save_path, "url": url, "output_format": output_format, "source": "overpass"})

    downloader = OverpassDownloader(
        task=task,
        query=query,
        output_format=output_format,
        on_progress=lambda d, t, s: task_manager.update_progress(
            info.task_id, round(d / t * 100, 1) if t > 0 else 0,
            downloaded_bytes=int(d), total_bytes=int(t), speed=s,
        ),
    )

    worker = DownloadWorker(
        downloader,
        on_complete=lambda path: task_manager.complete_task(info.task_id, result=path),
        on_error=lambda msg: task_manager.fail_task(info.task_id, error=msg),
    )
    worker.start()

    return {"code": 0, "data": {"task_id": info.task_id}}


@router.get("/config/default-save-path")
async def default_save_path():
    """获取默认保存路径"""
    from pathlib import Path
    default_dir = Path.cwd() / "outdata"
    default_dir.mkdir(parents=True, exist_ok=True)
    return {"code": 0, "data": {"path": str(default_dir)}}


@router.post("/import-vector")
async def import_vector(file: UploadFile = File(...)):
    """导入矢量文件，解析返回边界信息"""
    if not file.filename:
        return {"code": 1, "message": "缺少文件名"}

    ext = os.path.splitext(file.filename)[1].lower()
    supported = ['.geojson', '.json', '.kml', '.gpkg', '.zip', '.shp']
    if ext not in supported:
        return {"code": 1, "message": f"不支持的格式: {ext}，支持: {', '.join(supported)}"}

    # 保存到临时文件
    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, file.filename)
    try:
        content = await file.read()
        with open(tmp_path, 'wb') as f:
            f.write(content)

        from osm_tool.core.downloader.vector_parser import parse_vector_file
        result = parse_vector_file(tmp_path, file.filename)

        return {
            "code": 0,
            "data": {
                "bbox": result.bbox,
                "geojson": result.geojson,
                "area_sqkm": result.area_sqkm,
            },
        }
    except Exception as e:
        return {"code": 1, "message": str(e)}
    finally:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass


@router.post("/overpass/query")
async def overpass_query(body: dict):
    """根据几何数据生成 Overpass QL 查询"""
    geom_type = body.get("type")  # bbox / polygon / circle
    output_format = body.get("output_format", "json")

    if geom_type == "bbox":
        left = body.get("left")
        bottom = body.get("bottom")
        right = body.get("right")
        top = body.get("top")
        if None in (left, bottom, right, top):
            return {"code": 1, "message": "缺少 bbox 坐标"}
        query = f'[out:{output_format}];\nnode({bottom},{left},{top},{right});\nout body;\n>;\nout skel qt;'

    elif geom_type == "polygon":
        coordinates = body.get("coordinates")  # [[lng,lat], ...]
        if not coordinates:
            return {"code": 1, "message": "缺少多边形坐标"}
        # Overpass poly 格式: "lat1 lon1 lat2 lon2 ..."
        poly_str = " ".join(f"{lat} {lng}" for lng, lat in coordinates)
        query = f'[out:{output_format}];\nnode(poly:"{poly_str}");\nout body;\n>;\nout skel qt;'

    elif geom_type == "circle":
        center_lat = body.get("center_lat")
        center_lng = body.get("center_lng")
        radius = body.get("radius")  # 米
        if None in (center_lat, center_lng, radius):
            return {"code": 1, "message": "缺少圆形参数"}
        query = f'[out:{output_format}];\nnode(around:{radius},{center_lat},{center_lng});\nout body;\n>;\nout skel qt;'

    else:
        return {"code": 1, "message": f"不支持的几何类型: {geom_type}"}

    return {"code": 0, "data": {"query": query}}


@router.get("/tasks")
async def list_download_tasks():
    return {"code": 0, "data": task_manager.list_tasks("download")}


@router.post("/tasks/{task_id}/cancel")
async def cancel_download(task_id: str):
    ok = task_manager.cancel_task(task_id)
    return {"code": 0, "data": {"cancelled": ok}} if ok else {"code": 1, "message": "任务不存在"}


@router.post("/tasks/{task_id}/pause")
async def pause_download(task_id: str):
    info = task_manager.get_task(task_id)
    if not info:
        return {"code": 1, "message": "任务不存在"}
    # TODO: 暂停逻辑需要 worker 引用
    return {"code": 0}


@router.post("/tasks/{task_id}/resume")
async def resume_download(task_id: str):
    info = task_manager.get_task(task_id)
    if not info:
        return {"code": 1, "message": "任务不存在"}
    # TODO: 恢复逻辑需要 worker 引用
    return {"code": 0}


@router.post("/tasks/{task_id}/retry")
async def retry_download(task_id: str):
    """重试失败的任务"""
    info = task_manager.get_task(task_id)
    if not info:
        return {"code": 1, "message": "任务不存在"}
    if info.status not in ("failed", "cancelled"):
        return {"code": 1, "message": "只能重试失败或已取消的任务"}

    params = info.params
    source = params.get("source", "")

    # 删除旧任务
    task_manager.delete_task(task_id)

    if source == "geofabrik":
        return await geofabrik_start({
            "url": params.get("url"),
            "save_path": params.get("save_path"),
            "region_name": params.get("region_name", "Geofabrik"),
        })
    elif source == "overpass":
        return await overpass_start({
            "query": params.get("query"),
            "save_path": params.get("save_path"),
            "output_format": params.get("output_format", "json"),
            "url": params.get("url", "https://overpass-api.de/api/interpreter"),
        })
    else:
        return {"code": 1, "message": "无法重试：缺少任务参数"}


@router.delete("/tasks/{task_id}")
async def delete_download(task_id: str):
    """删除已完成/失败/已取消的任务"""
    ok = task_manager.delete_task(task_id)
    return {"code": 0, "data": {"deleted": ok}} if ok else {"code": 1, "message": "任务不存在或正在运行"}
