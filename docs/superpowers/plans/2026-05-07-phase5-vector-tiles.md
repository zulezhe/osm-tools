# Phase 5: 矢量切片发布模块

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现矢量切片生成（MVT 目录/MBTiles/GeoJSON 切片）和地图预览功能

**Architecture:** BasePublisher + TippecanoePublisher/PlanetilerPublisher 两个实现，TilePreviewServer 本地预览

**Tech Stack:** tippecanoe, planetiler (Java), Python http.server, MapLibre GL JS

**Depends on:** Phase 1, Phase 2 完成

---

## 文件结构

```
src/osm_tool/core/publisher/
├── __init__.py
├── base.py              # BasePublisher + TileConfig + LayerConfig
├── tippecanoe_publisher.py
├── planetiler_publisher.py
├── manager.py           # PublishManager
└── preview.py           # TilePreviewServer
src/osm_tool/workers/
└── publish_worker.py
src/osm_tool/ui/panels/
└── publish_panel.py     # 替换占位面板
src/osm_tool/resources/
└── preview.html         # MapLibre 预览页面模板
tests/
└── test_publisher.py
```

---

### Task 1: 发布基类和配置

**Files:**
- Create: `src/osm_tool/core/publisher/__init__.py`
- Create: `src/osm_tool/core/publisher/base.py`

- [ ] **Step 1: 写实现**

```python
# src/osm_tool/core/publisher/__init__.py
"""矢量切片发布模块"""
```

```python
# src/osm_tool/core/publisher/base.py
"""发布器基类和配置"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class OutputFormat(Enum):
    """切片输出格式"""
    MVT_DIRECTORY = "mvt_dir"
    MBTILES = "mbtiles"
    GEOJSON_TILES = "geojson_tiles"


@dataclass
class LayerConfig:
    """图层配置"""
    name: str
    source_layer: str = ""
    minzoom: int = 0
    maxzoom: int = 14


@dataclass
class TileConfig:
    """切片生成配置"""
    minzoom: int = 0
    maxzoom: int = 14
    tile_size: int = 256
    output_format: OutputFormat = OutputFormat.MBTILES
    layers: list[LayerConfig] = field(default_factory=list)
    simplify: bool = True
    drop_tags: list[str] = field(default_factory=list)


@dataclass
class PublishResult:
    """发布结果"""
    output_path: str
    tile_count: int = 0
    total_size_bytes: int = 0
    duration_seconds: float = 0.0
    success: bool = True
    error_message: str | None = None


class BasePublisher(ABC):
    """发布器抽象基类"""

    def __init__(
        self,
        on_progress: Callable[[int], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        self._on_progress = on_progress
        self._on_error = on_error

    @abstractmethod
    def publish(self, input_path: str, output_path: str, config: TileConfig) -> PublishResult:
        """生成矢量切片"""
        ...

    def _report_progress(self, percent: int) -> None:
        if self._on_progress:
            self._on_progress(percent)

    def _report_error(self, msg: str) -> None:
        if self._on_error:
            self._on_error(msg)
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/core/publisher/
git commit -m "feat: add publisher base class with TileConfig"
```

---

### Task 2: Tippecanoe 发布器

**Files:**
- Create: `src/osm_tool/core/publisher/tippecanoe_publisher.py`
- Test: `tests/test_publisher.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_publisher.py
"""矢量切片发布测试"""
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.osm_tool.core.publisher.base import TileConfig, OutputFormat
from src.osm_tool.core.publisher.tippecanoe_publisher import TippecanoePublisher


def test_tippecanoe_build_command_mbtiles():
    """测试 MBTiles 命令构建"""
    publisher = TippecanoePublisher()
    config = TileConfig(minzoom=5, maxzoom=12, output_format=OutputFormat.MBTILES)
    cmd = publisher._build_command("input.geojson", "output.mbtiles", config)
    assert "-z" in cmd
    assert "12" in cmd
    assert "-o" in cmd
    assert "output.mbtiles" in cmd


def test_tippecanoe_build_command_mvt_dir():
    """测试 MVT 目录命令构建"""
    publisher = TippecanoePublisher()
    config = TileConfig(minzoom=0, maxzoom=14, output_format=OutputFormat.MVT_DIRECTORY)
    cmd = publisher._build_command("input.geojson", "output_dir", config)
    assert "-e" in cmd
    assert "output_dir" in cmd


def test_tippecanoe_publish_success(tmp_dir):
    """测试发布成功"""
    publisher = TippecanoePublisher()
    config = TileConfig(output_format=OutputFormat.MBTILES)
    output_path = str(tmp_dir / "output.mbtiles")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="1000 tiles")
        Path(output_path).write_bytes(b"fake mbtiles")

        result = publisher.publish(str(tmp_dir / "input.geojson"), output_path, config)

    assert result.success
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_publisher.py -v
```

- [ ] **Step 3: 写实现**

```python
# src/osm_tool/core/publisher/tippecanoe_publisher.py
"""Tippecanoe 发布器"""
import subprocess
import time
from pathlib import Path

from .base import BasePublisher, TileConfig, OutputFormat, PublishResult


class TippecanoePublisher(BasePublisher):
    """使用 tippecanoe 生成矢量切片

    支持 MVT 目录、MBTiles、GeoJSON 切片三种输出。
    注意: tippecanoe 在 Windows 上需要 WSL。
    """

    def publish(self, input_path: str, output_path: str, config: TileConfig) -> PublishResult:
        start_time = time.time()

        try:
            cmd = self._build_command(input_path, output_path, config)
            self._report_progress(10)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=7200,
            )
            self._report_progress(90)

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                self._report_error(error_msg)
                return PublishResult(
                    output_path=output_path,
                    success=False,
                    error_message=error_msg,
                    duration_seconds=time.time() - start_time,
                )

            # 统计输出
            tile_count = self._parse_tile_count(result.stderr)
            total_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0

            self._report_progress(100)
            return PublishResult(
                output_path=output_path,
                tile_count=tile_count,
                total_size_bytes=total_size,
                duration_seconds=time.time() - start_time,
                success=True,
            )

        except subprocess.TimeoutExpired:
            msg = "切片生成超时"
            self._report_error(msg)
            return PublishResult(output_path=output_path, success=False, error_message=msg, duration_seconds=time.time() - start_time)
        except Exception as e:
            self._report_error(str(e))
            return PublishResult(output_path=output_path, success=False, error_message=str(e), duration_seconds=time.time() - start_time)

    def _build_command(self, input_path: str, output_path: str, config: TileConfig) -> list[str]:
        """构建 tippecanoe 命令行"""
        cmd = ["tippecanoe"]

        # 缩放级别
        cmd.extend(["-z", str(config.maxzoom)])
        cmd.extend(["-Z", str(config.minzoom)])

        # 切片大小
        if config.tile_size != 256:
            cmd.extend(["--tile-size", str(config.tile_size)])

        # 输出格式
        if config.output_format == OutputFormat.MVT_DIRECTORY:
            cmd.extend(["-e", output_path])
        elif config.output_format == OutputFormat.MBTILES:
            cmd.extend(["-o", output_path])
        elif config.output_format == OutputFormat.GEOJSON_TILES:
            cmd.extend(["-e", output_path, "--no-tile-compression"])

        # 图层
        for layer in config.layers:
            cmd.extend(["-l", layer.name])

        # 简化
        if not config.simplify:
            cmd.append("--no-simplification")

        # 删除标签
        for tag in config.drop_tags:
            cmd.extend(["--exclude", tag])

        # 覆盖已有
        cmd.append("--force")

        # 输入文件
        cmd.append(input_path)

        return cmd

    @staticmethod
    def _parse_tile_count(stderr: str) -> int:
        """从 tippecanoe 输出解析切片数"""
        for line in stderr.split("\n"):
            if "tiles" in line.lower():
                parts = line.split()
                for part in parts:
                    if part.isdigit():
                        return int(part)
        return 0
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_publisher.py -v
```

- [ ] **Step 5: 提交**

```bash
git add src/osm_tool/core/publisher/tippecanoe_publisher.py tests/test_publisher.py
git commit -m "feat: add tippecanoe publisher for vector tile generation"
```

---

### Task 3: Planetiler 发布器

**Files:**
- Create: `src/osm_tool/core/publisher/planetiler_publisher.py`

- [ ] **Step 1: 写实现**

```python
# src/osm_tool/core/publisher/planetiler_publisher.py
"""Planetiler 发布器"""
import subprocess
import time
from pathlib import Path

from .base import BasePublisher, TileConfig, OutputFormat, PublishResult


class PlanetilerPublisher(BasePublisher):
    """使用 Planetiler 生成矢量切片

    Planetiler 是 Java 工具，速度极快，适合大规模数据。
    需要安装 JRE 和下载 Planetiler JAR 文件。
    """

    def __init__(self, jar_path: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self._jar_path = jar_path or "planetiler.jar"

    def publish(self, input_path: str, output_path: str, config: TileConfig) -> PublishResult:
        start_time = time.time()

        try:
            cmd = self._build_command(input_path, output_path, config)
            self._report_progress(10)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=7200,
            )
            self._report_progress(90)

            if result.returncode != 0:
                return PublishResult(
                    output_path=output_path,
                    success=False,
                    error_message=result.stderr.strip(),
                    duration_seconds=time.time() - start_time,
                )

            total_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
            self._report_progress(100)
            return PublishResult(
                output_path=output_path,
                total_size_bytes=total_size,
                duration_seconds=time.time() - start_time,
                success=True,
            )

        except Exception as e:
            return PublishResult(output_path=output_path, success=False, error_message=str(e), duration_seconds=time.time() - start_time)

    def _build_command(self, input_path: str, output_path: str, config: TileConfig) -> list[str]:
        cmd = ["java", "-jar", self._jar_path]

        cmd.extend(["--input", input_path])
        cmd.extend(["--output", output_path])

        # 缩放范围
        cmd.append(f"--mbtiles={config.minzoom},{config.maxzoom}")

        # 切片大小
        if config.tile_size != 256:
            cmd.extend(["--tile-size", str(config.tile_size)])

        return cmd
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/core/publisher/planetiler_publisher.py
git commit -m "feat: add planetiler publisher"
```

---

### Task 4: 发布管理器和预览

**Files:**
- Create: `src/osm_tool/core/publisher/manager.py`
- Create: `src/osm_tool/core/publisher/preview.py`
- Create: `src/osm_tool/resources/preview.html`

- [ ] **Step 1: 写实现**

```python
# src/osm_tool/core/publisher/manager.py
"""发布管理器"""
import shutil

from .base import BasePublisher, TileConfig
from .tippecanoe_publisher import TippecanoePublisher
from .planetiler_publisher import PlanetilerPublisher


class PublishManager:
    """自动选择可用的发布器"""

    def __init__(self):
        self._tippecanoe = TippecanoePublisher()
        self._planetiler = PlanetilerPublisher()

    def get_publisher(self) -> BasePublisher:
        """获取可用的发布器"""
        if shutil.which("tippecanoe"):
            return self._tippecanoe
        if shutil.which("java"):
            return self._planetiler
        raise RuntimeError("未找到 tippecanoe 或 java，请安装其中之一")

    def publish(self, input_path: str, output_path: str, config: TileConfig):
        """便捷发布方法"""
        publisher = self.get_publisher()
        return publisher.publish(input_path, output_path, config)
```

```python
# src/osm_tool/core/publisher/preview.py
"""切片预览服务器"""
import http.server
import json
import threading
import webbrowser
from pathlib import Path


PREVIEW_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>OSM Tool - 切片预览</title>
    <link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet" />
    <script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
    <style>
        body { margin: 0; padding: 0; }
        #map { position: absolute; top: 0; bottom: 0; width: 100%; }
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        const params = new URLSearchParams(window.location.search);
        const tilesUrl = params.get('tiles') || '/tiles/{z}/{x}/{y}.pbf';
        const bounds = JSON.parse(params.get('bounds') || '[73, 3, 136, 54]');
        const minzoom = parseInt(params.get('minzoom') || '0');
        const maxzoom = parseInt(params.get('maxzoom') || '14');

        const map = new maplibregl.Map({
            container: 'map',
            style: {
                version: 8,
                sources: {
                    tiles: {
                        type: 'vector',
                        tiles: [tilesUrl],
                        minzoom: minzoom,
                        maxzoom: maxzoom,
                        bounds: bounds
                    }
                },
                layers: []
            },
            center: [(bounds[0]+bounds[2])/2, (bounds[1]+bounds[3])/2],
            zoom: 6
        });
        map.addControl(new maplibregl.NavigationControl());
    </script>
</body>
</html>
"""


class TilePreviewServer:
    """本地切片预览 HTTP 服务器"""

    def __init__(self, tiles_dir: str, port: int = 8765):
        self._tiles_dir = Path(tiles_dir)
        self._port = port
        self._server = None
        self._thread = None

    def start(self) -> str:
        """启动预览服务，返回预览 URL"""
        handler = self._make_handler(self._tiles_dir)
        self._server = http.server.HTTPServer(("localhost", self._port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

        url = f"http://localhost:{self._port}/preview.html?tiles=/{{z}}/{{x}}/{{y}}.pbf"
        webbrowser.open(url)
        return url

    def stop(self) -> None:
        """停止预览服务"""
        if self._server:
            self._server.shutdown()

    @staticmethod
    def _make_handler(tiles_dir: Path):
        class Handler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/preview.html":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(PREVIEW_HTML.encode("utf-8"))
                elif self.path.startswith("/tiles/"):
                    # 解析 /tiles/{z}/{x}/{y}.pbf
                    parts = self.path.replace("/tiles/", "").split("/")
                    if len(parts) == 3:
                        z, x, y_file = parts
                        tile_path = tiles_dir / z / x / y_file
                        if tile_path.exists():
                            self.send_response(200)
                            self.send_header("Content-Type", "application/x-protobuf")
                            self.end_headers()
                            self.wfile.write(tile_path.read_bytes())
                            return
                    self.send_error(404)
                else:
                    super().do_GET()

            def log_message(self, format, *args):
                pass  # 静默日志

        return Handler
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/core/publisher/manager.py src/osm_tool/core/publisher/preview.py
git commit -m "feat: add publish manager and tile preview server"
```

---

### Task 5: 发布 Worker 和面板

**Files:**
- Create: `src/osm_tool/workers/publish_worker.py`
- Modify: `src/osm_tool/ui/panels/publish_panel.py`

- [ ] **Step 1: 写 Worker**

```python
# src/osm_tool/workers/publish_worker.py
"""矢量切片发布工作线程"""
from PySide6.QtCore import QThread, Signal

from src.osm_tool.core.publisher.base import TileConfig, PublishResult
from src.osm_tool.core.publisher.manager import PublishManager


class PublishWorker(QThread):
    """异步执行切片发布"""

    progress = Signal(int)
    finished_ok = Signal(object)  # PublishResult
    error = Signal(str)

    def __init__(self, input_path: str, output_path: str, config: TileConfig, parent=None):
        super().__init__(parent)
        self._input = input_path
        self._output = output_path
        self._config = config

    def run(self) -> None:
        try:
            mgr = PublishManager()
            publisher = mgr.get_publisher()
            publisher._on_progress = lambda p: self.progress.emit(p)
            result = publisher.publish(self._input, self._output, self._config)
            if result.success:
                self.finished_ok.emit(result)
            else:
                self.error.emit(result.error_message or "发布失败")
        except Exception as e:
            self.error.emit(str(e))
```

- [ ] **Step 2: 重写发布面板**

```python
# src/osm_tool/ui/panels/publish_panel.py
"""矢量切片发布面板"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox,
    QFileDialog, QProgressBar, QSpinBox, QCheckBox,
    QListWidget, QMessageBox,
)

from src.osm_tool.core.publisher.base import TileConfig, OutputFormat, LayerConfig


class PublishPanel(QWidget):
    """矢量切片发布面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("矢量切片发布")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 输入文件
        input_group = QGroupBox("输入文件")
        input_layout = QHBoxLayout(input_group)
        self._input_path = QLineEdit()
        input_btn = QPushButton("浏览...")
        input_btn.clicked.connect(lambda: self._browse(self._input_path, "GeoJSON (*.geojson);;PBF (*.pbf)"))
        input_layout.addWidget(self._input_path)
        input_layout.addWidget(input_btn)
        layout.addWidget(input_group)

        # 切片配置
        config_group = QGroupBox("切片配置")
        form = QFormLayout(config_group)

        self._minzoom = QSpinBox(); self._minzoom.setRange(0, 22); self._minzoom.setValue(0)
        self._maxzoom = QSpinBox(); self._maxzoom.setRange(0, 22); self._maxzoom.setValue(14)
        form.addRow("最小缩放:", self._minzoom)
        form.addRow("最大缩放:", self._maxzoom)

        self._tile_size = QComboBox()
        self._tile_size.addItems(["256", "512"])
        form.addRow("切片大小:", self._tile_size)

        self._output_format = QComboBox()
        self._output_format.addItem("MBTiles (单文件)", OutputFormat.MBTILES)
        self._output_format.addItem("MVT 目录", OutputFormat.MVT_DIRECTORY)
        self._output_format.addItem("GeoJSON 切片", OutputFormat.GEOJSON_TILES)
        form.addRow("输出格式:", self._output_format)

        self._simplify_check = QCheckBox("自动简化")
        self._simplify_check.setChecked(True)
        form.addRow("简化:", self._simplify_check)

        layout.addWidget(config_group)

        # 输出路径
        output_layout = QHBoxLayout()
        self._output_path = QLineEdit()
        output_btn = QPushButton("浏览...")
        output_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(QLabel("输出:"))
        output_layout.addWidget(self._output_path)
        output_layout.addWidget(output_btn)
        layout.addLayout(output_layout)

        # 执行 + 进度
        btn_layout = QHBoxLayout()
        self._progress = QProgressBar()
        self._publish_btn = QPushButton("生成切片")
        self._preview_btn = QPushButton("预览")
        self._preview_btn.setEnabled(False)
        btn_layout.addWidget(self._progress)
        btn_layout.addWidget(self._publish_btn)
        btn_layout.addWidget(self._preview_btn)
        layout.addLayout(btn_layout)

    def _browse(self, line_edit, filter_str):
        path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", filter_str)
        if path:
            line_edit.setText(path)

    def _browse_output(self):
        fmt = self._output_format.currentData()
        if fmt == OutputFormat.MBTILES:
            path, _ = QFileDialog.getSaveFileName(self, "输出", "", "MBTiles (*.mbtiles)")
        else:
            path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self._output_path.setText(path)

    def get_config(self) -> TileConfig:
        """获取当前配置"""
        return TileConfig(
            minzoom=self._minzoom.value(),
            maxzoom=self._maxzoom.value(),
            tile_size=int(self._tile_size.currentText()),
            output_format=self._output_format.currentData(),
            simplify=self._simplify_check.isChecked(),
        )
```

- [ ] **Step 3: 提交**

```bash
git add src/osm_tool/workers/publish_worker.py src/osm_tool/ui/panels/publish_panel.py
git commit -m "feat: add publish worker and full publish panel UI"
```

---

### Task 6: 最终验证

- [ ] **运行全部测试**

```bash
uv run pytest tests/ -v
```

- [ ] **最终提交**

```bash
git add -A
git commit -m "chore: finalize Phase 5 - vector tile publishing module"
```
