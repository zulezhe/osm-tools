"""系统托盘图标模块"""
import os
from typing import Callable

import pystray
from PIL import Image, ImageDraw

_state = {
    "icon": None,
    "url": None,
    "shutdown_callback": None,
    "window_ref": None,
}


def create_icon_image() -> Image.Image:
    """生成托盘图标（64x64 紫色闪电）"""
    width, height = 64, 64
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    purple = (134, 59, 255, 255)
    dc.polygon([
        (38, 4), (14, 30), (28, 30),
        (26, 60), (50, 34), (36, 34),
    ], fill=purple)
    return image


def _toggle_window(icon, item):
    """显示主窗口"""
    win = _state.get("window_ref")
    if win:
        win.show()
        win.restore()


def _quit(icon, item):
    """退出应用"""
    icon.notify("正在退出...", "OSM Data Toolbox")
    cb = _state["shutdown_callback"]
    if cb:
        cb()
    icon.stop()
    os._exit(0)


def create_tray_icon(url: str, shutdown_callback: Callable, window_ref=None) -> pystray.Icon:
    """创建并返回托盘图标（尚未运行）"""
    _state["url"] = url
    _state["shutdown_callback"] = shutdown_callback
    _state["window_ref"] = window_ref

    icon = pystray.Icon(
        "OSM Data Toolbox",
        icon=create_icon_image(),
        hover_text="OSM Data Toolbox",
        menu=pystray.Menu(
            pystray.MenuItem(
                "显示窗口",
                _toggle_window,
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", _quit),
        ),
    )
    _state["icon"] = icon
    return icon


def run_tray(icon: pystray.Icon) -> None:
    """运行托盘图标事件循环（阻塞）"""
    icon.run()
