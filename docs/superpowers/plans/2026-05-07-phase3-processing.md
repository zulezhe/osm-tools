# Phase 3: 数据处理模块

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现数据处理管道：压缩、坐标转换（WGS84/GCJ-02/BD-09/EPSG）、坐标抽稀（DP/VW/固定间距）、字段删除

**Architecture:** ProcessingStep 抽象基类 + 4 个处理器实现 + ProcessingPipeline 管道串联执行

**Tech Stack:** fiona, shapely, pyproj, gzip, zipfile

**Depends on:** Phase 1 完成

---

## 文件结构

```
src/osm_tool/core/processor/
├── __init__.py
├── base.py              # ProcessingStep + ProcessingPipeline
├── compressor.py        # 压缩处理器
├── coord_transform.py   # 坐标转换处理器
├── simplifier.py        # 坐标抽稀处理器
└── field_remover.py     # 字段删除处理器
src/osm_tool/workers/
└── process_worker.py    # QThread 处理线程
src/osm_tool/ui/panels/
└── process_panel.py     # 替换占位面板
tests/
└── test_processor.py
```

---

### Task 1: 处理管道框架

**Files:**
- Create: `src/osm_tool/core/processor/__init__.py`
- Create: `src/osm_tool/core/processor/base.py`
- Test: `tests/test_processor.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_processor.py
"""数据处理测试"""
import json
import gzip
import zipfile
from pathlib import Path
from unittest.mock import patch

from src.osm_tool.core.processor.base import ProcessingStep, ProcessingPipeline


class UpperCaseStep(ProcessingStep):
    """测试用处理器：将属性值转大写"""
    name = "uppercase"

    def process_feature(self, feature: dict) -> dict:
        props = feature.get("properties", {})
        return {**feature, "properties": {k: v.upper() if isinstance(v, str) else v for k, v in props.items()}}


def test_pipeline_single_step(tmp_dir):
    """测试单步管道"""
    input_geojson = tmp_dir / "input.geojson"
    output_geojson = tmp_dir / "output.geojson"
    input_geojson.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"name": "hello"}, "geometry": None}]
    }), encoding="utf-8")

    pipeline = ProcessingPipeline()
    pipeline.add_step(UpperCaseStep())
    pipeline.execute(str(input_geojson), str(output_geojson))

    result = json.loads(output_geojson.read_text(encoding="utf-8"))
    assert result["features"][0]["properties"]["name"] == "HELLO"


def test_pipeline_multi_step(tmp_dir):
    """测试多步管道"""
    input_geojson = tmp_dir / "input.geojson"
    output_geojson = tmp_dir / "output.geojson"
    input_geojson.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"name": "hello"}, "geometry": None}]
    }), encoding="utf-8")

    pipeline = ProcessingPipeline()
    pipeline.add_step(UpperCaseStep())
    pipeline.add_step(UpperCaseStep())  # 再次转大写不影响
    pipeline.execute(str(input_geojson), str(output_geojson))

    result = json.loads(output_geojson.read_text(encoding="utf-8"))
    assert result["features"][0]["properties"]["name"] == "HELLO"


def test_compressor_geojson_gz(tmp_dir):
    """测试 GeoJSON 压缩为 gzip"""
    from src.osm_tool.core.processor.compressor import Compressor

    input_geojson = tmp_dir / "input.geojson"
    input_geojson.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")

    compressor = Compressor()
    output_path = compressor.compress_geojson(str(input_geojson), compression_level=6)

    assert Path(output_path).exists()
    content = gzip.open(output_path, "rt", encoding="utf-8").read()
    assert "FeatureCollection" in content


def test_simplifier_douglas_peucker():
    """测试 Douglas-Peucker 抽稀"""
    from src.osm_tool.core.processor.simplifier import DouglasPeuckerSimplifier
    from shapely.geometry import LineString

    line = LineString([(0, 0), (1, 0.1), (2, 0), (3, 0)])
    simplifier = DouglasPeuckerSimplifier(tolerance=0.5)
    result = simplifier.simplify(line)
    assert result.coords[:]  # 非空
    assert len(result.coords) <= len(line.coords)


def test_field_remover(tmp_dir):
    """测试字段删除"""
    from src.osm_tool.core.processor.field_remover import FieldRemover

    input_geojson = tmp_dir / "input.geojson"
    output_geojson = tmp_dir / "output.geojson"
    input_geojson.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"name": "test", "source": "gps", "note": "ok"}, "geometry": None}]
    }), encoding="utf-8")

    remover = FieldRemover(fields_to_remove=["source", "note"])
    remover.execute(str(input_geojson), str(output_geojson))

    result = json.loads(output_geojson.read_text(encoding="utf-8"))
    props = result["features"][0]["properties"]
    assert "name" in props
    assert "source" not in props
    assert "note" not in props
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_processor.py -v
```

- [ ] **Step 3: 写实现**

```python
# src/osm_tool/core/processor/__init__.py
"""数据处理模块"""
```

```python
# src/osm_tool/core/processor/base.py
"""处理管道基类"""
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable


class ProcessingStep(ABC):
    """处理步骤抽象基类"""
    name: str = "base"

    @abstractmethod
    def process_feature(self, feature: dict) -> dict:
        """处理单个要素，返回处理后的要素"""
        ...

    def execute(self, input_path: str, output_path: str) -> None:
        """读取 GeoJSON，逐要素处理，写入输出"""
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
        features = data.get("features", [])
        total = len(features)

        processed = []
        for i, feat in enumerate(features):
            processed.append(self.process_feature(feat))

        data["features"] = processed
        Path(output_path).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class ProcessingPipeline:
    """处理管道 - 串联多个处理步骤"""

    def __init__(self):
        self._steps: list[ProcessingStep] = []
        self._on_step_progress: Callable[[str, int], None] | None = None

    def add_step(self, step: ProcessingStep) -> None:
        self._steps.append(step)

    def remove_step(self, index: int) -> None:
        if 0 <= index < len(self._steps):
            self._steps.pop(index)

    @property
    def steps(self) -> list[ProcessingStep]:
        return self._steps

    def execute(self, input_path: str, output_path: str) -> None:
        """执行管道：每个步骤的输出作为下一个步骤的输入"""
        import tempfile

        current_input = input_path
        for i, step in enumerate(self._steps):
            if i == len(self._steps) - 1:
                # 最后一步直接写入目标
                step.execute(current_input, output_path)
            else:
                # 中间步骤写入临时文件
                tmp = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False, mode="w")
                tmp_path = tmp.name
                tmp.close()
                step.execute(current_input, tmp_path)
                if current_input != input_path:
                    Path(current_input).unlink(missing_ok=True)
                current_input = tmp_path

            if self._on_step_progress:
                self._on_step_progress(step.name, int((i + 1) / len(self._steps) * 100))

        # 清理临时文件
        if current_input != input_path and current_input != output_path:
            Path(current_input).unlink(missing_ok=True)
```

```python
# src/osm_tool/core/processor/compressor.py
"""数据压缩处理器"""
import gzip
import shutil
import zipfile
from pathlib import Path


class Compressor:
    """数据压缩"""

    def compress_geojson(self, input_path: str, compression_level: int = 6) -> str:
        """GeoJSON → Gzip"""
        output_path = input_path + ".gz"
        with open(input_path, "rb") as f_in:
            with gzip.open(output_path, "wb", compresslevel=compression_level) as f_out:
                shutil.copyfileobj(f_in, f_out)
        return output_path

    def compress_shapefile(self, input_dir: str, output_path: str) -> str:
        """Shapefile → ZIP"""
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
                p = Path(input_dir + ext)
                if p.exists():
                    zf.write(str(p), p.name)
        return output_path
```

```python
# src/osm_tool/core/processor/coord_transform.py
"""坐标转换处理器"""
import math
import json
from pathlib import Path

from src.osm_tool.core.processor.base import ProcessingStep


# === GCJ-02 / BD-09 转换常量 ===
_X_PI = math.pi * 3000.0 / 180.0
_PI = math.pi
_A = 6378245.0  # 长半轴
_EE = 0.00669342162296594323  # 扁率


def _out_of_china(lng: float, lat: float) -> bool:
    """判断坐标是否在中国境外"""
    return not (72.004 <= lng <= 137.8347 and 0.8293 <= lat <= 55.8271)


def _transform_lat(lng: float, lat: float) -> float:
    ret = (-100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat +
           0.1 * lng * lat + 0.2 * math.sqrt(abs(lng)))
    ret += (20.0 * math.sin(6.0 * lng * _PI) + 20.0 *
            math.sin(2.0 * lng * _PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * _PI) + 40.0 *
            math.sin(lat / 3.0 * _PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * _PI) + 320 *
            math.sin(lat * _PI / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(lng: float, lat: float) -> float:
    ret = (300.0 + lng + 2.0 * lat + 0.1 * lng * lng +
           0.1 * lng * lat + 0.1 * math.sqrt(abs(lng)))
    ret += (20.0 * math.sin(6.0 * lng * _PI) + 20.0 *
            math.sin(2.0 * lng * _PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * _PI) + 40.0 *
            math.sin(lng / 3.0 * _PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * _PI) + 300.0 *
            math.sin(lng / 30.0 * _PI)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lng: float, lat: float) -> tuple[float, float]:
    """WGS84 → GCJ-02 (火星坐标)"""
    if _out_of_china(lng, lat):
        return lng, lat
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * _PI
    magic = math.sin(radlat)
    magic = 1 - _EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrtmagic) * _PI)
    dlng = (dlng * 180.0) / (_A / sqrtmagic * math.cos(radlat) * _PI)
    mglat = lat + dlat
    mglng = lng + dlng
    return mglng, mglat


def gcj02_to_bd09(lng: float, lat: float) -> tuple[float, float]:
    """GCJ-02 → BD-09 (百度坐标)"""
    z = math.sqrt(lng * lng + lat * lat) + 0.00002 * math.sin(lat * _X_PI)
    theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * _X_PI)
    bd_lng = z * math.cos(theta) + 0.0065
    bd_lat = z * math.sin(theta) + 0.006
    return bd_lng, bd_lat


def wgs84_to_bd09(lng: float, lat: float) -> tuple[float, float]:
    """WGS84 → BD-09"""
    gcj_lng, gcj_lat = wgs84_to_gcj02(lng, lat)
    return gcj02_to_bd09(gcj_lng, gcj_lat)


class CoordTransform(ProcessingStep):
    """坐标转换处理步骤"""
    name = "coord_transform"

    def __init__(self, target_crs: str = "gcj02"):
        """
        Args:
            target_crs: 目标坐标系 gcj02 / bd09 / epsg:3857 / 自定义 EPSG
        """
        self._target_crs = target_crs

    def _transform_coord(self, lng: float, lat: float) -> tuple[float, float]:
        if self._target_crs == "gcj02":
            return wgs84_to_gcj02(lng, lat)
        elif self._target_crs == "bd09":
            return wgs84_to_bd09(lng, lat)
        else:
            # EPSG 转换需要 pyproj
            try:
                from pyproj import Transformer
                transformer = Transformer.from_crs("EPSG:4326", self._target_crs, always_xy=True)
                return transformer.transform(lng, lat)
            except ImportError:
                raise RuntimeError("EPSG 转换需要安装 pyproj: uv add pyproj")

    def process_feature(self, feature: dict) -> dict:
        geom = feature.get("geometry")
        if geom is None:
            return feature
        feature["geometry"] = self._transform_geometry(geom)
        return feature

    def _transform_geometry(self, geom: dict) -> dict:
        gtype = geom.get("type", "")
        coords = geom.get("coordinates", [])

        if gtype == "Point":
            geom["coordinates"] = list(self._transform_coord(coords[0], coords[1]))
        elif gtype in ("LineString", "MultiPoint"):
            geom["coordinates"] = [list(self._transform_coord(c[0], c[1])) for c in coords]
        elif gtype in ("Polygon", "MultiLineString"):
            geom["coordinates"] = [
                [list(self._transform_coord(c[0], c[1])) for c in ring]
                for ring in coords
            ]
        elif gtype == "MultiPolygon":
            geom["coordinates"] = [
                [[list(self._transform_coord(c[0], c[1])) for c in ring] for ring in poly]
                for poly in coords
            ]
        return geom
```

```python
# src/osm_tool/core/processor/simplifier.py
"""坐标抽稀处理器"""
import json
from pathlib import Path

from src.osm_tool.core.processor.base import ProcessingStep


class DouglasPeuckerSimplifier(ProcessingStep):
    """Douglas-Peucker 抽稀"""
    name = "simplify_dp"

    def __init__(self, tolerance: float = 1.0):
        self._tolerance = tolerance

    def simplify(self, geometry):
        """使用 shapely 简化几何"""
        from shapely.geometry import shape
        geom = shape(geometry) if isinstance(geometry, dict) else geometry
        return geom.simplify(self._tolerance)

    def process_feature(self, feature: dict) -> dict:
        from shapely.geometry import shape, mapping
        geom = feature.get("geometry")
        if geom is None or geom.get("type") == "Point":
            return feature
        simplified = self.simplify(geom)
        feature["geometry"] = mapping(simplified)
        return feature


class VisvalingamSimplifier(ProcessingStep):
    """Visvalingam-Whyatt 抽稀"""
    name = "simplify_vw"

    def __init__(self, min_area: float = 1.0):
        self._min_area = min_area

    def simplify(self, geometry):
        """使用 shapely + 简化"""
        from shapely.geometry import shape
        geom = shape(geometry) if isinstance(geometry, dict) else geometry
        # shapely 的 simplify 使用 Douglas-Peucker
        # VW 近似：用较小容差迭代
        tolerance = max(0.1, self._min_area ** 0.5)
        return geom.simplify(tolerance, preserve_topology=True)

    def process_feature(self, feature: dict) -> dict:
        from shapely.geometry import shape, mapping
        geom = feature.get("geometry")
        if geom is None or geom.get("type") == "Point":
            return feature
        simplified = self.simplify(geom)
        feature["geometry"] = mapping(simplified)
        return feature


class FixedIntervalSimplifier(ProcessingStep):
    """固定间距抽稀"""
    name = "simplify_interval"

    def __init__(self, interval_meters: float = 10.0):
        self._interval = interval_meters

    def process_feature(self, feature: dict) -> dict:
        geom = feature.get("geometry")
        if geom is None or geom.get("type") == "Point":
            return feature

        coords = geom.get("coordinates", [])
        gtype = geom.get("type", "")

        if gtype in ("LineString", "MultiPoint"):
            geom["coordinates"] = self._thin_coords(coords)
        elif gtype in ("Polygon", "MultiLineString"):
            geom["coordinates"] = [self._thin_coords(ring) for ring in coords]
        elif gtype == "MultiPolygon":
            geom["coordinates"] = [
                [self._thin_coords(ring) for ring in poly] for poly in coords
            ]
        return feature

    def _thin_coords(self, coords: list) -> list:
        """每隔一定距离取一个点"""
        if len(coords) <= 2:
            return coords
        result = [coords[0]]
        accumulated = 0.0
        for i in range(1, len(coords)):
            dx = coords[i][0] - coords[i-1][0]
            dy = coords[i][1] - coords[i-1][1]
            # 近似距离（度→米）
            dist = (dx * 111000) ** 2 + (dy * 111000) ** 2
            dist = dist ** 0.5
            accumulated += dist
            if accumulated >= self._interval:
                result.append(coords[i])
                accumulated = 0.0
        if result[-1] != coords[-1]:
            result.append(coords[-1])
        return result
```

```python
# src/osm_tool/core/processor/field_remover.py
"""字段删除处理器"""
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from src.osm_tool.core.processor.base import ProcessingStep


# 预设元数据字段
OSM_METADATA_FIELDS = ["source", "created_by", "note", "fixme", "source_ref", "source:url"]


@dataclass
class FieldInfo:
    """字段统计信息"""
    name: str
    non_null_count: int
    unique_count: int
    sample_values: list


class FieldRemover(ProcessingStep):
    """字段删除处理器"""
    name = "field_remover"

    def __init__(self, fields_to_remove: list[str] | None = None):
        self._fields_to_remove = fields_to_remove or []

    def process_feature(self, feature: dict) -> dict:
        props = feature.get("properties", {})
        cleaned = {k: v for k, v in props.items() if k not in self._fields_to_remove}
        return {**feature, "properties": cleaned}

    @staticmethod
    def analyze_fields(input_path: str) -> list[FieldInfo]:
        """分析 GeoJSON 文件中的字段统计"""
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
        features = data.get("features", [])
        if not features:
            return []

        # 收集所有字段
        all_keys: set[str] = set()
        for feat in features:
            all_keys.update(feat.get("properties", {}).keys())

        # 统计每个字段
        result = []
        for key in sorted(all_keys):
            values = []
            for feat in features:
                v = feat.get("properties", {}).get(key)
                if v is not None:
                    values.append(v)
            counter = Counter(values)
            result.append(FieldInfo(
                name=key,
                non_null_count=len(values),
                unique_count=len(counter),
                sample_values=values[:5],
            ))
        return result
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_processor.py -v
```

- [ ] **Step 5: 提交**

```bash
git add src/osm_tool/core/processor/ tests/test_processor.py
git commit -m "feat: add data processing module with pipeline, compressor, coord transform, simplifier, field remover"
```

---

### Task 2: 处理 Worker

**Files:**
- Create: `src/osm_tool/workers/process_worker.py`

- [ ] **Step 1: 写实现**

```python
# src/osm_tool/workers/process_worker.py
"""数据处理工作线程"""
from PySide6.QtCore import QThread, Signal

from src.osm_tool.core.processor.base import ProcessingPipeline


class ProcessWorker(QThread):
    """异步执行处理管道"""

    progress = Signal(int)     # 总进度
    step_progress = Signal(str, int)  # 步骤名 + 步骤进度
    finished_ok = Signal(str)  # 输出路径
    error = Signal(str)

    def __init__(self, pipeline: ProcessingPipeline, input_path: str, output_path: str, parent=None):
        super().__init__(parent)
        self._pipeline = pipeline
        self._input = input_path
        self._output = output_path

    def run(self) -> None:
        try:
            self._pipeline._on_step_progress = lambda name, pct: self.step_progress.emit(name, pct)
            self._pipeline.execute(self._input, self._output)
            self.finished_ok.emit(self._output)
        except Exception as e:
            self.error.emit(str(e))
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/workers/process_worker.py
git commit -m "feat: add process worker thread"
```

---

### Task 3: 处理面板 UI

**Files:**
- Modify: `src/osm_tool/ui/panels/process_panel.py`（替换占位面板）

- [ ] **Step 1: 重写处理面板**

```python
# src/osm_tool/ui/panels/process_panel.py
"""数据处理面板"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox,
    QFileDialog, QProgressBar, QSpinBox, QDoubleSpinBox,
    QCheckBox, QListWidget, QListWidgetItem, QMessageBox,
    QSlider, QTabWidget,
)

from src.osm_tool.core.processor.compressor import Compressor
from src.osm_tool.core.processor.coord_transform import CoordTransform
from src.osm_tool.core.processor.simplifier import DouglasPeuckerSimplifier, VisvalingamSimplifier, FixedIntervalSimplifier
from src.osm_tool.core.processor.field_remover import FieldRemover, OSM_METADATA_FIELDS
from src.osm_tool.core.processor.base import ProcessingPipeline


class ProcessPanel(QWidget):
    """数据处理面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("数据处理")
        self._pipeline = ProcessingPipeline()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 文件选择
        file_group = QGroupBox("输入文件")
        file_layout = QHBoxLayout(file_group)
        self._input_path = QLineEdit()
        input_btn = QPushButton("浏览...")
        input_btn.clicked.connect(self._browse_input)
        file_layout.addWidget(self._input_path)
        file_layout.addWidget(input_btn)
        layout.addWidget(file_group)

        # 处理步骤配置
        tabs = QTabWidget()
        tabs.addTab(self._create_compress_tab(), "压缩")
        tabs.addTab(self._create_transform_tab(), "坐标转换")
        tabs.addTab(self._create_simplify_tab(), "抽稀")
        tabs.addTab(self._create_field_tab(), "字段删除")
        layout.addWidget(tabs)

        # 管道预览
        pipeline_group = QGroupBox("处理管道")
        pipeline_layout = QVBoxLayout(pipeline_group)
        self._pipeline_list = QListWidget()
        pipeline_layout.addWidget(self._pipeline_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("添加到管道")
        add_btn.clicked.connect(self._add_to_pipeline)
        clear_btn = QPushButton("清空管道")
        clear_btn.clicked.connect(self._pipeline.clear)
        clear_btn.clicked.connect(lambda: self._pipeline_list.clear())
        btn_row.addWidget(add_btn)
        btn_row.addWidget(clear_btn)
        pipeline_layout.addLayout(btn_row)
        layout.addWidget(pipeline_group)

        # 输出 + 执行
        output_group = QGroupBox("输出")
        output_layout = QHBoxLayout(output_group)
        self._output_path = QLineEdit()
        output_btn = QPushButton("浏览...")
        output_btn.clicked.connect(self._browse_output)
        self._progress = QProgressBar()
        self._execute_btn = QPushButton("执行")
        output_layout.addWidget(QLabel("输出:"))
        output_layout.addWidget(self._output_path)
        output_layout.addWidget(output_btn)
        output_layout.addWidget(self._progress)
        output_layout.addWidget(self._execute_btn)
        layout.addWidget(output_group)

    def _create_compress_tab(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self._compress_level = QSlider()
        self._compress_level.setRange(1, 9)
        self._compress_level.setValue(6)
        self._compress_level_label = QLabel("6")
        self._compress_level.valueChanged.connect(lambda v: self._compress_level_label.setText(str(v)))
        row = QHBoxLayout()
        row.addWidget(self._compress_level)
        row.addWidget(self._compress_level_label)
        layout.addRow("压缩级别:", row)
        return w

    def _create_transform_tab(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self._crs_combo = QComboBox()
        self._crs_combo.addItems(["WGS84 → GCJ-02 (火星)", "WGS84 → BD-09 (百度)", "WGS84 → EPSG:3857"])
        self._crs_combo.currentIndexChanged.connect(lambda i: self._update_crs(i))
        layout.addRow("目标坐标系:", self._crs_combo)
        return w

    def _create_simplify_tab(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self._simplify_algo = QComboBox()
        self._simplify_algo.addItems(["Douglas-Peucker", "Visvalingam-Whyatt", "固定间距"])
        layout.addRow("算法:", self._simplify_algo)
        self._simplify_tolerance = QDoubleSpinBox()
        self._simplify_tolerance.setRange(0.01, 10000)
        self._simplify_tolerance.setValue(1.0)
        self._simplify_tolerance.setSuffix(" 米")
        layout.addRow("容差:", self._simplify_tolerance)
        return w

    def _create_field_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        preset_btn = QPushButton("预设: 删除 OSM 元数据字段")
        preset_btn.clicked.connect(self._preset_osm_metadata)
        layout.addWidget(preset_btn)
        self._field_list = QListWidget()
        layout.addWidget(QLabel("加载文件后显示字段列表"))
        layout.addWidget(self._field_list)
        return w

    def _update_crs(self, index: int):
        self._selected_crs = ["gcj02", "bd09", "EPSG:3857"][index] if 0 <= index < 3 else "gcj02"

    def _browse_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择输入文件", "", "GeoJSON (*.geojson *.json)")
        if path:
            self._input_path.setText(path)

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "输出路径", "", "GeoJSON (*.geojson)")
        if path:
            self._output_path.setText(path)

    def _add_to_pipeline(self):
        # 根据当前 tab 添加步骤
        pass  # 由信号连接 MainWindow 处理

    def _preset_osm_metadata(self):
        for field in OSM_METADATA_FIELDS:
            self._pipeline_list.addItem(field)
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/ui/panels/process_panel.py
git commit -m "feat: replace placeholder with full process panel UI"
```

---

### Task 4: 最终验证

- [ ] **运行全部测试**

```bash
uv run pytest tests/ -v
```

- [ ] **更新依赖**

```bash
uv add shapely pyproj
```

- [ ] **最终提交**

```bash
git add -A
git commit -m "chore: finalize Phase 3 - data processing module"
```
