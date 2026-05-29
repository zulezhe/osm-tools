"""系统 API 路由"""
import sys

from fastapi import APIRouter

from osm_tool.utils.environment import check_all_tools

# tkinter 仅在非打包环境可用，用于原生文件对话框
_has_tk = not getattr(sys, "frozen", False)
if _has_tk:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        _has_tk = False

router = APIRouter()


@router.get("/health")
async def health():
    return {"code": 0, "data": {"status": "ok"}}


@router.get("/environment")
async def environment():
    results = check_all_tools()
    return {
        "code": 0,
        "data": {
            name: {"available": r.available, "path": r.path}
            for name, r in results.items()
        },
    }


@router.post("/file-dialog")
async def file_dialog(body: dict):
    """弹出原生文件选择对话框（阻塞式，在后台线程中执行）"""
    if not _has_tk:
        return {"code": -1, "msg": "打包环境不支持原生文件对话框"}

    import asyncio

    mode = body.get("mode", "open_file")  # open_file / save_file / open_dir
    title = body.get("title", "选择文件")
    file_types = body.get("file_types", [])  # [{"label": "PBF", "ext": "*.pbf"}]

    tk_formats = [(f["label"], f["ext"]) for f in file_types] if file_types else [("所有文件", "*.*")]

    loop = asyncio.get_event_loop()

    def _dialog():
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        result = ""
        try:
            if mode == "open_file":
                result = filedialog.askopenfilename(title=title, filetypes=tk_formats)
            elif mode == "save_file":
                result = filedialog.asksaveasfilename(title=title, filetypes=tk_formats)
            elif mode == "open_dir":
                result = filedialog.askdirectory(title=title)
        finally:
            root.destroy()
        return result

    path = await loop.run_in_executor(None, _dialog)
    return {"code": 0, "data": {"path": path}}
