"""FastAPI 应用"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from osm_tool.utils.logger import setup_logger

logger = setup_logger("osm_tool")


def create_app() -> FastAPI:
    app = FastAPI(title="OSM Data Toolbox", version="0.1.0")

    # 确保输出目录存在
    outdata = Path.cwd() / "outdata"
    outdata.mkdir(parents=True, exist_ok=True)

    # CORS（开发模式前后端分离时需要）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册 API 路由
    from osm_tool.api.routes import download, convert, split, process, publish, system, extract
    from osm_tool.api.events import sse_endpoint

    app.add_api_route("/api/v1/events", sse_endpoint, methods=["GET"])
    app.include_router(download.router, prefix="/api/v1/download", tags=["download"])
    app.include_router(extract.router, prefix="/api/v1/extract", tags=["extract"])
    app.include_router(convert.router, prefix="/api/v1/convert", tags=["convert"])
    app.include_router(split.router, prefix="/api/v1/split", tags=["split"])
    app.include_router(process.router, prefix="/api/v1/process", tags=["process"])
    app.include_router(publish.router, prefix="/api/v1/publish", tags=["publish"])
    app.include_router(system.router, prefix="/api/v1", tags=["system"])

    # 生产模式：托管前端静态文件
    web_dir = Path(__file__).parent / "web"
    if web_dir.is_dir() and not os.getenv("OSM_DEV"):
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

    logger.info("FastAPI 应用已创建")
    return app


app = create_app()
