"""数据拆分 API 路由"""
from fastapi import APIRouter

from osm_tool.api.task_manager import task_manager

router = APIRouter()


@router.post("/start")
async def split_start(body: dict):
    input_path = body.get("input_path")
    output_dir = body.get("output_dir")
    split_type = body.get("split_type", "admin")  # admin / range / attribute / type
    options = body.get("options", {})

    if not input_path or not output_dir:
        return {"code": 1, "message": "缺少 input_path 或 output_dir"}

    from osm_tool.workers.split_worker import SplitWorker

    # 根据 split_type 选择对应的 splitter
    splitter = _get_splitter(split_type, options)
    if splitter is None:
        return {"code": 1, "message": f"不支持的拆分类型: {split_type}"}

    info = task_manager.create_task("split", {"input_path": input_path, "split_type": split_type})

    worker = SplitWorker(
        splitter=splitter,
        input_path=input_path,
        output_dir=output_dir,
        options=options,
        on_progress=lambda p: task_manager.update_progress(info.task_id, p),
        on_complete=lambda files: task_manager.complete_task(info.task_id, result={"files": files}),
        on_error=lambda msg: task_manager.fail_task(info.task_id, error=msg),
    )
    worker.start()

    return {"code": 0, "data": {"task_id": info.task_id}}


@router.get("/tasks")
async def list_split_tasks():
    return {"code": 0, "data": task_manager.list_tasks("split")}


def _get_splitter(split_type: str, options: dict):
    """根据类型获取对应的 splitter 实例"""
    if split_type == "admin":
        from osm_tool.core.splitter.admin_boundaries import AdminBoundarySplitter
        return AdminBoundarySplitter()
    elif split_type == "range":
        from osm_tool.core.splitter.range_splitter import RangeSplitter
        return RangeSplitter()
    elif split_type == "attribute":
        from osm_tool.core.splitter.attribute_splitter import AttributeSplitter
        return AttributeSplitter()
    elif split_type == "type":
        from osm_tool.core.splitter.type_splitter import TypeSplitter
        return TypeSplitter()
    return None
