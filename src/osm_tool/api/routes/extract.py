"""数据提取 API 路由"""
import threading

from fastapi import APIRouter

from osm_tool.api.task_manager import task_manager

router = APIRouter()


@router.post("/scan")
async def scan_fields(body: dict):
    """扫描数据文件中的所有字段"""
    file_path = body.get("file_path")
    if not file_path:
        return {"code": 1, "message": "缺少 file_path"}

    try:
        from osm_tool.core.extractor.extractor import scan_fields
        fields = scan_fields(file_path)
        return {"code": 0, "data": fields}
    except FileNotFoundError as e:
        return {"code": 1, "message": str(e)}
    except ValueError as e:
        return {"code": 1, "message": str(e)}
    except Exception as e:
        return {"code": 1, "message": f"扫描失败: {e}"}


@router.post("/start")
async def extract_start(body: dict):
    """按字段条件提取数据"""
    file_path = body.get("file_path")
    output_path = body.get("output_path")
    filters = body.get("filters", [])  # [{key: "highway", values: ["primary"]}]

    if not file_path or not output_path:
        return {"code": 1, "message": "缺少 file_path 或 output_path"}
    if not filters:
        return {"code": 1, "message": "请至少选择一个过滤字段"}

    info = task_manager.create_task("extract", {
        "file_path": file_path,
        "filters": [f["key"] for f in filters],
    })

    def run_extract():
        try:
            from osm_tool.core.extractor.extractor import extract
            result = extract(file_path, filters, output_path)
            task_manager.complete_task(info.task_id, result=result)
        except Exception as e:
            task_manager.fail_task(info.task_id, error=str(e))

    thread = threading.Thread(target=run_extract, daemon=True)
    thread.start()

    return {"code": 0, "data": {"task_id": info.task_id}}


@router.post("/tag-dictionary")
async def tag_dictionary(body: dict):
    """查询标签字典"""
    from osm_tool.core.extractor.tag_dictionary import TAG_DICTIONARY, search_tags

    query = body.get("query", "")
    if query:
        results = search_tags(query)
        return {"code": 0, "data": results}

    # 返回全部
    data = [
        {"key": k, "label": v["label"], "desc": v["desc"], "values": v["values"]}
        for k, v in TAG_DICTIONARY.items()
    ]
    return {"code": 0, "data": data}


@router.get("/tasks")
async def list_extract_tasks():
    return {"code": 0, "data": task_manager.list_tasks("extract")}
