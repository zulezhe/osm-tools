"""格式转换 API 路由"""
from fastapi import APIRouter

from osm_tool.api.task_manager import task_manager

router = APIRouter()


@router.get("/formats")
async def list_formats():
    from osm_tool.core.converter.base import Format
    return {"code": 0, "data": [f.value for f in Format]}


@router.post("/start")
async def convert_start(body: dict):
    input_path = body.get("input_path")
    output_path = body.get("output_path")
    output_format = body.get("output_format")
    options = body.get("options")

    if not input_path or not output_path:
        return {"code": 1, "message": "缺少 input_path 或 output_path"}

    from osm_tool.core.converter.base import Format
    from osm_tool.workers.convert_worker import ConvertWorker

    fmt = Format(output_format) if output_format else None
    info = task_manager.create_task("convert", {"input_path": input_path, "output_path": output_path})

    worker = ConvertWorker(
        input_path=input_path,
        output_path=output_path,
        output_format=fmt,
        options=options,
        on_progress=lambda p: task_manager.update_progress(info.task_id, p),
        on_complete=lambda r: task_manager.complete_task(info.task_id, result={"output": r.output_path, "duration": r.duration_seconds}),
        on_error=lambda msg: task_manager.fail_task(info.task_id, error=msg),
    )
    worker.start()

    return {"code": 0, "data": {"task_id": info.task_id}}


@router.get("/tasks")
async def list_convert_tasks():
    return {"code": 0, "data": task_manager.list_tasks("convert")}
