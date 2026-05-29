# -*- mode: python ; coding: utf-8 -*-
import importlib.util
import os
import sys


def module_exists(module_name):
    return importlib.util.find_spec(module_name) is not None


datas = []
binaries = []

hiddenimports = [
    "shapely",
    "shapely.geometry",
    "shapely.ops",
    "pyproj",
    "osm_tool",
    "osm_tool.app",
    "osm_tool.main",
    "osm_tool.utils.logger",
    "osm_tool.utils.environment",
    "osm_tool.models.download_task",
    "osm_tool.models.task_state",
    "osm_tool.core.downloader.aria2_downloader",
    "webview",
]

optional_hiddenimports = [
    "osm_tool.api.events",
    "osm_tool.api.task_manager",
    "osm_tool.api.routes.download",
    "osm_tool.api.routes.extract",
    "osm_tool.api.routes.convert",
    "osm_tool.api.routes.split",
    "osm_tool.api.routes.process",
    "osm_tool.api.routes.publish",
    "osm_tool.api.routes.system",
    "osm_tool.core.extractor.extractor",
    "osm_tool.core.extractor.tag_dictionary",
    "osm_tool.tray",
]

for module_name in optional_hiddenimports:
    if module_exists(module_name):
        hiddenimports.append(module_name)

if sys.platform.startswith("win"):
    hiddenimports.extend([
        "pystray",
        "pystray._win32",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "webview.platforms.edgechromium",
        "webview.platforms.winforms",
    ])
elif sys.platform == "darwin":
    hiddenimports.extend([
        "webview.platforms.cocoa",
    ])

web_dir = os.path.join("src", "osm_tool", "web")
if os.path.isdir(web_dir):
    datas.append((web_dir, os.path.join("osm_tool", "web")))

upx_dir = os.path.join("tools", "upx")
if not os.path.isdir(upx_dir):
    upx_dir = None

excludes = [
    "tkinter",
    "_tkinter",
    "turtle",
    "setuptools",
    "wheel",
    "pkg_resources",
    "unittest",
    "pytest",
    "_pytest",
    "doctest",
    "pydoc",
    "pdb",
    "profile",
    "pstats",
    "cProfile",
    "trace",
    "traceback_full",
    "code",
    "codeop",
    "compiler",
    "cython",
    "numpy.distutils",
    "html.parser",
    "xml.dom",
    "xml.sax",
    "xmlrpc",
    "pydoc_data",
    "idlelib",
    "lib2to3",
    "multiprocessing.shared_memory",
    "concurrent.futures.process",
    "numpy.random",
    "numpy.polynomial",
    "numpy.fft",
    "numpy.ma",
    "numpy.testing",
    "numpy.f2py",
    "pydantic.mypy",
    "pydantic.experimental",
    "_pyrepl",
    "curses",
]

upx_exclude = [
    "_ssl.pyd",
    "_hashlib.pyd",
    "libcrypto-3-x64.dll",
    "libssl-3-x64.dll",
    "python313.dll",
    "VCRUNTIME140.dll",
    "VCRUNTIME140_1.dll",
    "pydantic_core.cp313-win_amd64.pyd",
    "_shapely.cpython-313-x86_64-linux-gnu.so",
]

a = Analysis(
    [os.path.join("src", "osm_tool", "main.py")],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
    upx_dir=upx_dir,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="osm-tool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=upx_dir is not None,
    upx_dir=upx_dir,
    upx_exclude=upx_exclude,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
