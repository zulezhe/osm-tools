"""数据处理 API 路由"""
from fastapi import APIRouter

from osm_tool.api.task_manager import task_manager

router = APIRouter()


@router.post("/start")
async def process_start(body: dict):
    input_path = body.get("input_path")
    output_path = body.get("output_path")
    steps = body.get("steps", [])  # [{type: "compress", params: {...}}, ...]

    if not input_path or not output_path:
        return {"code": 1, "message": "缺少 input_path 或 output_path"}

    from osm_tool.core.processor.base import ProcessingPipeline
    from osm_tool.workers.process_worker import ProcessWorker

    pipeline = ProcessingPipeline()
    for step in steps:
        processor = _get_processor(step)
        if processor:
            pipeline.add_step(processor)

    if not pipeline.steps:
        return {"code": 1, "message": "未指定处理步骤"}

    info = task_manager.create_task("process", {"input_path": input_path, "steps": [s["type"] for s in steps]})

    worker = ProcessWorker(
        pipeline=pipeline,
        input_path=input_path,
        output_path=output_path,
        on_progress=lambda p: task_manager.update_progress(info.task_id, p),
        on_complete=lambda path: task_manager.complete_task(info.task_id, result={"output": path}),
        on_error=lambda msg: task_manager.fail_task(info.task_id, error=msg),
    )
    worker.start()

    return {"code": 0, "data": {"task_id": info.task_id}}


@router.get("/tasks")
async def list_process_tasks():
    return {"code": 0, "data": task_manager.list_tasks("process")}


def _get_processor(step: dict):
    """根据步骤类型创建处理器"""
    step_type = step.get("type")
    params = step.get("params", {})

    if step_type == "compress":
        from osm_tool.core.processor.compressor import Compressor
        return Compressor(level=params.get("level", 6))
    elif step_type == "transform":
        from osm_tool.core.processor.coord_transformer import CoordTransformer
        return CoordTransformer(target_crs=params.get("target_crs", "EPSG:3857"))
    elif step_type == "simplify":
        from osm_tool.core.processor.simplifier import Simplifier
        return Simplifier(algorithm=params.get("algorithm", "dp"), tolerance=params.get("tolerance", 1.0))
    elif step_type == "field_remove":
        from osm_tool.core.processor.field_remover import FieldRemover
        return FieldRemover(fields=params.get("fields", []))
    return None
