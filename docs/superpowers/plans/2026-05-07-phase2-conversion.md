# Phase 2: 格式转换模块

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 OSM 数据格式互转（PBF/GeoJSON/Shapefile/GeoPackage），通过 ogr2ogr 和 osmium-tool

**Architecture:** BaseConverter 抽象基类 + GDALConverter(osr2ogr) + OsmiumConverter 两个实现，ConversionManager 自动路由

**Tech Stack:** GDAL (ogr2ogr), osmium-tool, subprocess, fiona

**Depends on:** Phase 1 完成

---

## 文件结构

```
src/osm_tool/core/converter/
├── __init__.py
├── base.py               # BaseConverter + Format 枚举
├── gdal_converter.py     # ogr2ogr 封装
├── osmium_converter.py   # osmium-tool 封装
└── manager.py            # ConversionManager 路由
src/osm_tool/workers/
└── convert_worker.py     # QThread 转换线程
src/osm_tool/ui/panels/
└── convert_panel.py      # 替换占位面板
tests/
├── test_converter.py
└── test_convert_manager.py
```

---

### Task 1: 格式转换基类和枚举

**Files:**
- Create: `src/osm_tool/core/converter/__init__.py`
- Create: `src/osm_tool/core/converter/base.py`

- [ ] **Step 1: 写实现**

```python
# src/osm_tool/core/converter/__init__.py
"""格式转换模块"""
from .base import Format, ConversionResult, BaseConverter

__all__ = ["Format", "ConversionResult", "BaseConverter"]
```

```python
# src/osm_tool/core/converter/base.py
"""格式转换基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable


class Format(Enum):
    """支持的格式"""
    PBF = "pbf"
    GEOJSON = "geojson"
    SHAPEFILE = "shp"
    GEOPACKAGE = "gpkg"


@dataclass
class ConversionResult:
    """转换结果"""
    input_path: str
    output_path: str
    input_format: Format
    output_format: Format
    success: bool
    error_message: str | None = None
    duration_seconds: float = 0.0


class BaseConverter(ABC):
    """格式转换抽象基类"""

    def __init__(
        self,
        on_progress: Callable[[int], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        self._on_progress = on_progress
        self._on_error = on_error

    @abstractmethod
    def convert(
        self,
        input_path: str,
        output_path: str,
        input_format: Format,
        output_format: Format,
        options: dict | None = None,
    ) -> ConversionResult:
        """执行转换

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            input_format: 输入格式
            output_format: 输出格式
            options: 额外选项（编码、坐标参考系等）
        """
        ...

    def _report_progress(self, percent: int) -> None:
        if self._on_progress:
            self._on_progress(percent)

    def _report_error(self, msg: str) -> None:
        if self._on_error:
            self._on_error(msg)

    @staticmethod
    def detect_format(path: str) -> Format | None:
        """根据文件扩展名推断格式"""
        p = Path(path).suffix.lower()
        mapping = {
            ".pbf": Format.PBF,
            ".osm": Format.PBF,
            ".geojson": Format.GEOJSON,
            ".json": Format.GEOJSON,
            ".shp": Format.SHAPEFILE,
            ".gpkg": Format.GEOPACKAGE,
        }
        # 处理复合后缀如 .osm.pbf
        full_name = Path(path).name.lower()
        if full_name.endswith(".osm.pbf"):
            return Format.PBF
        if full_name.endswith(".geojson.gz"):
            return Format.GEOJSON
        return mapping.get(p)
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/core/converter/
git commit -m "feat: add converter base class with Format enum"
```

---

### Task 2: GDAL 转换器

**Files:**
- Create: `src/osm_tool/core/converter/gdal_converter.py`
- Test: `tests/test_converter.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_converter.py
"""格式转换测试"""
from unittest.mock import patch, MagicMock
from src.osm_tool.core.converter.base import Format, BaseConverter
from src.osm_tool.core.converter.gdal_converter import GDALConverter


def test_detect_format():
    """测试格式检测"""
    assert BaseConverter.detect_format("test.geojson") == Format.GEOJSON
    assert BaseConverter.detect_format("test.shp") == Format.SHAPEFILE
    assert BaseConverter.detect_format("test.gpkg") == Format.GEOPACKAGE
    assert BaseConverter.detect_format("test.osm.pbf") == Format.PBF
    assert BaseConverter.detect_format("test.xyz") is None


def test_gdal_convert_geojson_to_shp(tmp_dir):
    """测试 GeoJSON 转 Shapefile"""
    input_path = str(tmp_dir / "input.geojson")
    output_path = str(tmp_dir / "output.shp")

    # 创建输入文件
    Path(input_path).write_text('{"type":"FeatureCollection","features":[]}')

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        # 创建输出文件模拟
        Path(output_path).write_text("fake")

        converter = GDALConverter()
        result = converter.convert(
            input_path, output_path, Format.GEOJSON, Format.SHAPEFILE
        )

    assert result.success
    assert result.output_format == Format.SHAPEFILE


def test_gdal_convert_failure(tmp_dir):
    """测试转换失败"""
    input_path = str(tmp_dir / "input.geojson")
    output_path = str(tmp_dir / "output.shp")
    Path(input_path).write_text("{}")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="ERROR: bad input")

        converter = GDALConverter()
        result = converter.convert(
            input_path, output_path, Format.GEOJSON, Format.SHAPEFILE
        )

    assert not result.success
    assert "bad input" in result.error_message
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_converter.py -v
```

- [ ] **Step 3: 写实现**

```python
# src/osm_tool/core/converter/gdal_converter.py
"""GDAL ogr2ogr 转换器"""
import subprocess
import time
from pathlib import Path

from .base import BaseConverter, ConversionResult, Format


class GDALConverter(BaseConverter):
    """使用 ogr2ogr 进行格式转换

    支持: GeoJSON ↔ Shapefile ↔ GeoPackage 互转
    """

    def convert(
        self,
        input_path: str,
        output_path: str,
        input_format: Format,
        output_format: Format,
        options: dict | None = None,
    ) -> ConversionResult:
        opts = options or {}
        start_time = time.time()

        try:
            cmd = self._build_command(input_path, output_path, input_format, output_format, opts)
            self._report_progress(10)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
            )
            self._report_progress(90)

            if result.returncode != 0:
                error_msg = result.stderr.strip() or f"ogr2ogr 返回错误码 {result.returncode}"
                self._report_error(error_msg)
                return ConversionResult(
                    input_path=input_path,
                    output_path=output_path,
                    input_format=input_format,
                    output_format=output_format,
                    success=False,
                    error_message=error_msg,
                    duration_seconds=time.time() - start_time,
                )

            # 验证输出文件
            if not Path(output_path).exists():
                return ConversionResult(
                    input_path=input_path,
                    output_path=output_path,
                    input_format=input_format,
                    output_format=output_format,
                    success=False,
                    error_message="输出文件未生成",
                    duration_seconds=time.time() - start_time,
                )

            self._report_progress(100)
            return ConversionResult(
                input_path=input_path,
                output_path=output_path,
                input_format=input_format,
                output_format=output_format,
                success=True,
                duration_seconds=time.time() - start_time,
            )

        except subprocess.TimeoutExpired:
            msg = "转换超时（超过 1 小时）"
            self._report_error(msg)
            return ConversionResult(
                input_path=input_path,
                output_path=output_path,
                input_format=input_format,
                output_format=output_format,
                success=False,
                error_message=msg,
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            self._report_error(str(e))
            return ConversionResult(
                input_path=input_path,
                output_path=output_path,
                input_format=input_format,
                output_format=output_format,
                success=False,
                error_message=str(e),
                duration_seconds=time.time() - start_time,
            )

    def _build_command(
        self,
        input_path: str,
        output_path: str,
        input_format: Format,
        output_format: Format,
        options: dict,
    ) -> list[str]:
        """构建 ogr2ogr 命令"""
        cmd = ["ogr2ogr"]

        # 输出格式
        fmt_map = {
            Format.GEOJSON: "GeoJSON",
            Format.SHAPEFILE: "ESRI Shapefile",
            Format.GEOPACKAGE: "GPKG",
        }
        if output_format in fmt_map:
            cmd.extend(["-f", fmt_map[output_format]])

        # 编码（Shapefile 默认 UTF-8）
        encoding = options.get("encoding", "UTF-8")
        if output_format == Format.SHAPEFILE:
            cmd.extend(["-lco", f"ENCODING={encoding}"])

        # 坐标参考系
        if "srs" in options:
            cmd.extend(["-a_srs", options["srs"]])

        # 覆盖已有文件
        cmd.append("-overwrite")

        # 输出路径和输入路径
        cmd.extend([output_path, input_path])

        return cmd
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_converter.py -v
```

- [ ] **Step 5: 提交**

```bash
git add src/osm_tool/core/converter/gdal_converter.py tests/test_converter.py
git commit -m "feat: add GDAL ogr2ogr converter"
```

---

### Task 3: Osmium 转换器

**Files:**
- Create: `src/osm_tool/core/converter/osmium_converter.py`

- [ ] **Step 1: 写实现**

```python
# src/osm_tool/core/converter/osmium_converter.py
"""Osmium-tool 转换器"""
import subprocess
import time

from .base import BaseConverter, ConversionResult, Format


class OsmiumConverter(BaseConverter):
    """使用 osmium-tool 进行 PBF 格式转换

    主要处理 PBF → GeoJSON/其他格式的转换
    """

    def convert(
        self,
        input_path: str,
        output_path: str,
        input_format: Format,
        output_format: Format,
        options: dict | None = None,
    ) -> ConversionResult:
        start_time = time.time()

        try:
            # PBF → GeoJSON: 使用 osmium export
            if input_format == Format.PBF and output_format == Format.GEOJSON:
                return self._pbf_to_geojson(input_path, output_path, start_time)

            # 其他情况通过 osmium getid +ogr2ogr 中转
            return ConversionResult(
                input_path=input_path,
                output_path=output_path,
                input_format=input_format,
                output_format=output_format,
                success=False,
                error_message=f"不支持的转换: {input_format.value} → {output_format.value}",
                duration_seconds=time.time() - start_time,
            )

        except Exception as e:
            return ConversionResult(
                input_path=input_path,
                output_path=output_path,
                input_format=input_format,
                output_format=output_format,
                success=False,
                error_message=str(e),
                duration_seconds=time.time() - start_time,
            )

    def _pbf_to_geojson(self, input_path: str, output_path: str, start_time: float) -> ConversionResult:
        """PBF 转 GeoJSON"""
        cmd = ["osmium", "export", input_path, "-o", output_path, "--overwrite"]
        self._report_progress(10)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        self._report_progress(90)

        if result.returncode != 0:
            return ConversionResult(
                input_path=input_path,
                output_path=output_path,
                input_format=Format.PBF,
                output_format=Format.GEOJSON,
                success=False,
                error_message=result.stderr.strip(),
                duration_seconds=time.time() - start_time,
            )

        self._report_progress(100)
        return ConversionResult(
            input_path=input_path,
            output_path=output_path,
            input_format=Format.PBF,
            output_format=Format.GEOJSON,
            success=True,
            duration_seconds=time.time() - start_time,
        )
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/core/converter/osmium_converter.py
git commit -m "feat: add osmium-tool converter for PBF exports"
```

---

### Task 4: 转换管理器

**Files:**
- Create: `src/osm_tool/core/converter/manager.py`
- Test: `tests/test_convert_manager.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_convert_manager.py
"""转换管理器测试"""
from src.osm_tool.core.converter.base import Format
from src.osm_tool.core.converter.manager import ConversionManager


def test_get_converter_geojson_to_shp():
    """测试 GeoJSON→SHP 路由到 GDAL"""
    mgr = ConversionManager()
    converter = mgr.get_converter(Format.GEOJSON, Format.SHAPEFILE)
    assert converter is not None


def test_get_converter_pbf_to_geojson():
    """测试 PBF→GeoJSON 路由到 Osmium"""
    mgr = ConversionManager()
    converter = mgr.get_converter(Format.PBF, Format.GEOJSON)
    assert converter is not None


def test_get_converter_same_format():
    """测试相同格式返回 None"""
    mgr = ConversionManager()
    converter = mgr.get_converter(Format.GEOJSON, Format.GEOJSON)
    assert converter is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_convert_manager.py -v
```

- [ ] **Step 3: 写实现**

```python
# src/osm_tool/core/converter/manager.py
"""转换管理器 - 自动路由到合适的转换器"""
from .base import BaseConverter, Format
from .gdal_converter import GDALConverter
from .osmium_converter import OsmiumConverter


class ConversionManager:
    """格式转换管理器

    根据输入/输出格式自动选择最佳转换器。
    """

    def __init__(self):
        self._gdal = GDALConverter()
        self._osmium = OsmiumConverter()

    def get_converter(self, input_fmt: Format, output_fmt: Format) -> BaseConverter | None:
        """根据格式组合获取合适的转换器

        Args:
            input_fmt: 输入格式
            output_fmt: 输出格式

        Returns:
            转换器实例，相同格式返回 None
        """
        if input_fmt == output_fmt:
            return None

        # PBF 相关转换使用 osmium
        if input_fmt == Format.PBF:
            return self._osmium

        # 其他转换使用 GDAL
        return self._gdal

    def convert(
        self,
        input_path: str,
        output_path: str,
        output_format: Format | None = None,
        options: dict | None = None,
    ):
        """便捷转换方法"""
        from .base import BaseConverter as bc

        input_format = bc.detect_format(input_path)
        if input_format is None:
            raise ValueError(f"无法识别输入文件格式: {input_path}")

        fmt = output_format or bc.detect_format(output_path)
        if fmt is None:
            raise ValueError(f"无法识别输出文件格式: {output_path}")

        converter = self.get_converter(input_format, fmt)
        if converter is None:
            raise ValueError("相同格式无需转换")

        return converter.convert(input_path, output_path, input_format, fmt, options)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_convert_manager.py -v
```

- [ ] **Step 5: 提交**

```bash
git add src/osm_tool/core/converter/manager.py tests/test_convert_manager.py
git commit -m "feat: add conversion manager with auto-routing"
```

---

### Task 5: 转换 Worker

**Files:**
- Create: `src/osm_tool/workers/convert_worker.py`

- [ ] **Step 1: 写实现**

```python
# src/osm_tool/workers/convert_worker.py
"""格式转换工作线程"""
from PySide6.QtCore import QThread, Signal

from src.osm_tool.core.converter.base import ConversionResult
from src.osm_tool.core.converter.manager import ConversionManager


class ConvertWorker(QThread):
    """异步执行格式转换"""

    progress = Signal(int)
    finished_ok = Signal(object)  # ConversionResult
    error = Signal(str)

    def __init__(
        self,
        input_path: str,
        output_path: str,
        output_format=None,
        options: dict | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._input_path = input_path
        self._output_path = output_path
        self._output_format = output_format
        self._options = options

    def run(self) -> None:
        try:
            mgr = ConversionManager()
            result = mgr.convert(
                self._input_path,
                self._output_path,
                self._output_format,
                self._options,
            )
            if result.success:
                self.finished_ok.emit(result)
            else:
                self.error.emit(result.error_message or "转换失败")
        except Exception as e:
            self.error.emit(str(e))
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/workers/convert_worker.py
git commit -m "feat: add convert worker thread"
```

---

### Task 6: 转换面板 UI

**Files:**
- Modify: `src/osm_tool/ui/panels/convert_panel.py`（替换占位面板）

- [ ] **Step 1: 重写转换面板**

```python
# src/osm_tool/ui/panels/convert_panel.py
"""格式转换面板"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox,
    QFileDialog, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox,
)
from PySide6.QtCore import Qt

from src.osm_tool.core.converter.base import Format, BaseConverter


class ConvertPanel(QWidget):
    """格式转换面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("格式转换")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 单文件转换
        single_group = QGroupBox("单文件转换")
        form = QFormLayout(single_group)

        # 输入文件
        input_layout = QHBoxLayout()
        self._input_path = QLineEdit()
        input_btn = QPushButton("浏览...")
        input_btn.clicked.connect(self._browse_input)
        input_layout.addWidget(self._input_path)
        input_layout.addWidget(input_btn)
        form.addRow("输入文件:", input_layout)

        # 输入格式（自动检测）
        self._input_format_label = QLabel("-")
        form.addRow("输入格式:", self._input_format_label)

        # 输出格式选择
        self._output_format = QComboBox()
        for fmt in Format:
            self._output_format.addItem(fmt.value, fmt)
        form.addRow("输出格式:", self._output_format)

        # 输出文件
        output_layout = QHBoxLayout()
        self._output_path = QLineEdit()
        output_btn = QPushButton("浏览...")
        output_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(self._output_path)
        output_layout.addWidget(output_btn)
        form.addRow("输出文件:", output_layout)

        # 选项
        self._encoding_combo = QComboBox()
        self._encoding_combo.addItems(["UTF-8", "GBK", "Latin-1"])
        form.addRow("编码 (SHP):", self._encoding_combo)

        # 转换按钮 + 进度
        btn_layout = QHBoxLayout()
        self._convert_btn = QPushButton("开始转换")
        self._convert_btn.clicked.connect(self._on_convert)
        btn_layout.addWidget(self._convert_btn)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        btn_layout.addWidget(self._progress)
        form.addRow(btn_layout)

        layout.addWidget(single_group)

        # 转换历史
        history_group = QGroupBox("转换历史")
        history_layout = QVBoxLayout(history_group)
        self._history_table = QTableWidget(0, 4)
        self._history_table.setHorizontalHeaderLabels(["输入", "输出格式", "状态", "耗时"])
        self._history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        history_layout.addWidget(self._history_table)
        layout.addWidget(history_group)

    def _browse_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择输入文件", "",
            "支持格式 (*.pbf *.osm *.geojson *.json *.shp *.gpkg);;所有文件 (*)"
        )
        if path:
            self._input_path.setText(path)
            fmt = BaseConverter.detect_format(path)
            self._input_format_label.setText(fmt.value if fmt else "未知")

    def _browse_output(self) -> None:
        fmt = self._output_format.currentData()
        ext_map = {Format.PBF: "pbf", Format.GEOJSON: "geojson", Format.SHAPEFILE: "shp", Format.GEOPACKAGE: "gpkg"}
        ext = ext_map.get(fmt, "*")
        path, _ = QFileDialog.getSaveFileName(self, "选择输出路径", "", f"文件 (*.{ext})")
        if path:
            self._output_path.setText(path)

    def _on_convert(self) -> None:
        if not self._input_path.text() or not self._output_path.text():
            QMessageBox.warning(self, "提示", "请选择输入和输出文件")
            return
        # 实际转换由 MainWindow 通过信号连接 ConvertWorker 执行
        self._convert_btn.setEnabled(False)
        self._progress.setValue(0)
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/ui/panels/convert_panel.py
git commit -m "feat: replace placeholder with full convert panel UI"
```

---

### Task 7: 最终验证

- [ ] **运行全部测试**

```bash
uv run pytest tests/ -v
```

- [ ] **最终提交**

```bash
git add -A
git commit -m "chore: finalize Phase 2 - format conversion module"
```
