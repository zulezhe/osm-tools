"""矢量切片发布 API 路由"""
from fastapi import APIRouter

from osm_tool.api.task_manager import task_manager

router = APIRouter()


@router.post("/start")
async def publish_start(body: dict):
    input_path = body.get("input_path")
    output_path = body.get("output_path")
    config = body.get("config", {})

    if not input_path or not output_path:
        return {"code": 1, "message": "缺少 input_path 或 output_path"}

    from osm_tool.core.publisher.base import TileConfig, OutputFormat
    from osm_tool.workers.publish_worker import PublishWorker

    fmt = OutputFormat(config.get("output_format", "mbtiles"))
    tile_config = TileConfig(
        minzoom=config.get("minzoom", 0),
        maxzoom=config.get("maxzoom", 14),
        tile_size=config.get("tile_size", 256),
        output_format=fmt,
        simplify=config.get("simplify", True),
    )

    info = task_manager.create_task("publish", {"input_path": input_path, "output_path": output_path})

    worker = PublishWorker(
        input_path=input_path,
        output_path=output_path,
        config=tile_config,
        on_progress=lambda p: task_manager.update_progress(info.task_id, p),
        on_complete=lambda r: task_manager.complete_task(info.task_id, result={"output": r.output_path, "tile_count": r.tile_count}),
        on_error=lambda msg: task_manager.fail_task(info.task_id, error=msg),
    )
    worker.start()

    return {"code": 0, "data": {"task_id": info.task_id}}


@router.get("/tasks")
async def list_publish_tasks():
    return {"code": 0, "data": task_manager.list_tasks("publish")}
