"""应用入口"""
import logging
import os
import socket
import sys
import threading
import time
import traceback
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

# PyInstaller console=False 模式下 sys.stdout/stderr 为 None
# uvicorn 等库内部会调用 isatty()/write()，必须提前修补
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

from osm_tool.utils.logger import setup_logger

# 端口文件路径，前后端共享
PORT_FILE = Path.home() / ".osm_tool" / ".port"
DEV_PORT = 8000  # 开发模式固定端口，与 vite proxy 配置一致


def is_port_in_use(port: int) -> bool:
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def find_free_port(start: int = 8000, end: int = 8020) -> int:
    """在指定范围内查找可用端口，找不到则随机"""
    for port in range(start, end):
        if not is_port_in_use(port):
            return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def save_port(port: int) -> None:
    """将端口号写入文件，供外部脚本读取"""
    PORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PORT_FILE.write_text(str(port))


def cleanup_port() -> None:
    """清理端口文件"""
    try:
        PORT_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def wait_for_server(url: str, timeout: float = 5.0) -> bool:
    """轮询健康检查接口，等待服务器就绪"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = urlopen(f"{url}/api/v1/health", timeout=1)
            if resp.getcode() == 200:
                return True
        except (URLError, OSError):
            pass
        time.sleep(0.1)
    return False


def main():
    """启动应用"""
    log_path = Path.home() / ".osm_tool" / "app.log"

    try:
        logger = setup_logger("osm_tool", log_file=log_path)
    except Exception:
        logging.basicConfig(filename=str(log_path), level=logging.INFO)
        logger = logging.getLogger("osm_tool")

    logger.info("应用启动")

    try:
        import uvicorn
        from osm_tool.app import app

        dev_mode = os.getenv("OSM_DEV") == "1"

        if dev_mode:
            if is_port_in_use(DEV_PORT):
                port = find_free_port(DEV_PORT + 1)
                logger.warning(f"端口 {DEV_PORT} 已被占用，自动切换到 {port}")
            else:
                port = DEV_PORT
        else:
            port = find_free_port()

        url = f"http://localhost:{port}"
        save_port(port)
        logger.info(f"启动服务: {url} (dev={dev_mode})")

        config = uvicorn.Config(
            app, host="127.0.0.1", port=port, log_level="warning"
        )
        server = uvicorn.Server(config)

        def shutdown():
            """退出时关闭服务"""
            logger.info("收到退出信号，正在关闭服务...")
            server.should_exit = True

        # 后台线程运行 uvicorn
        server_thread = threading.Thread(
            target=server.run, daemon=True, name="uvicorn"
        )
        server_thread.start()

        # 开发模式：无窗口无托盘，主线程等待服务
        if dev_mode:
            server_thread.join()
            return

        # ---- 生产模式：pywebview 内嵌浏览器 + 系统托盘 ----
        import webview
        from osm_tool.tray import create_tray_icon, run_tray

        loading_html = """<!DOCTYPE html>
<html><head><style>
body{display:flex;justify-content:center;align-items:center;height:100vh;
margin:0;font-family:system-ui;background:#0f172a;color:#94a3b8}
.loader{width:40px;height:40px;border:3px solid #1e293b;
border-top-color:#863bff;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
p{margin-top:16px;font-size:14px}
</style></head><body><div style="text-align:center">
<div class="loader"></div><p>正在启动服务...</p></div></body></html>"""

        window = webview.create_window(
            'OSM Data Toolbox',
            html=loading_html,
            width=1280,
            height=800,
            min_size=(800, 600),
        )

        def on_closing():
            """关闭时隐藏到托盘"""
            window.hide()
            return False

        window.events.closing += on_closing

        def setup():
            """webview GUI 启动后执行：等待服务器就绪、启动托盘"""
            # 等待 FastAPI 服务器就绪
            if wait_for_server(url):
                window.load_url(url)
                logger.info("前端页面已加载")
            else:
                logger.warning("服务器启动超时")

            # 托盘图标（阻塞此线程直到 icon.stop()）
            try:
                icon = create_tray_icon(url, shutdown_callback=shutdown, window_ref=window)
                logger.info("系统托盘图标已创建")
                run_tray(icon)
            except Exception:
                logger.error(f"托盘图标异常:\n{traceback.format_exc()}")

        webview.start(func=setup, gui='edgechromium')
        logger.info("应用已退出")

    except Exception:
        logger.error(f"启动失败:\n{traceback.format_exc()}")
        raise
    finally:
        cleanup_port()


if __name__ == "__main__":
    main()
