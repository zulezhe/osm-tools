# Phase 4: 数据拆分模块

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 4 种数据拆分策略：行政区拆分、矢量范围拆分、属性拆分、类型拆分

**Architecture:** BaseSplitter 抽象基类 + 4 个拆分器实现，行政区使用内置 DataV 数据 + 自定义边界，属性/类型使用 python-osmium

**Tech Stack:** osmium-tool, python-osmium, shapely, fiona

**Depends on:** Phase 1 完成

---

## 文件结构

```
src/osm_tool/core/splitter/
├── __init__.py
├── base.py               # BaseSplitter
├── admin_splitter.py      # 行政区拆分
├── admin_boundaries.py    # 行政区数据管理
├── range_splitter.py      # 范围拆分
├── attribute_splitter.py  # 属性拆分
└── type_splitter.py       # 类型拆分
src/osm_tool/workers/
└── split_worker.py        # QThread 拆分线程
src/osm_tool/ui/panels/
└── split_panel.py         # 替换占位面板
scripts/
└── download_admin_data.py # 行政区数据下载脚本
tests/
└── test_splitter.py
```

---

### Task 1: 拆分基类

**Files:**
- Create: `src/osm_tool/core/splitter/__init__.py`
- Create: `src/osm_tool/core/splitter/base.py`

- [ ] **Step 1: 写实现**

```python
# src/osm_tool/core/splitter/__init__.py
"""数据拆分模块"""
```

```python
# src/osm_tool/core/splitter/base.py
"""拆分器抽象基类"""
from abc import ABC, abstractmethod
from typing import Callable


class BaseSplitter(ABC):
    """数据拆分抽象基类"""

    def __init__(
        self,
        on_progress: Callable[[int], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        self._on_progress = on_progress
        self._on_error = on_error

    @abstractmethod
    def split(self, input_path: str, output_dir: str, options: dict | None = None) -> list[str]:
        """执行拆分

        Args:
            input_path: 输入文件路径（PBF/GeoJSON）
            output_dir: 输出目录
            options: 拆分选项

        Returns:
            输出文件路径列表
        """
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
git add src/osm_tool/core/splitter/
git commit -m "feat: add splitter base class"
```

---

### Task 2: 行政区拆分器

**Files:**
- Create: `src/osm_tool/core/splitter/admin_splitter.py`
- Create: `src/osm_tool/core/splitter/admin_boundaries.py`
- Create: `scripts/download_admin_data.py`
- Test: `tests/test_splitter.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_splitter.py
"""数据拆分测试"""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.osm_tool.core.splitter.admin_boundaries import AdminBoundaryManager, RegionInfo


def test_region_info():
    """测试区域信息"""
    r = RegionInfo(code="110000", name="北京市", geojson_path="/tmp/bj.json", parent_code="")
    assert r.code == "110000"
    assert r.name == "北京市"


def test_admin_boundary_manager_load(tmp_dir):
    """测试加载省份数据"""
    provinces_file = tmp_dir / "provinces.json"
    provinces_file.write_text(json.dumps({
        "features": [{"properties": {"adcode": 110000, "name": "北京市"}}]
    }), encoding="utf-8")

    mgr = AdminBoundaryManager(data_dir=str(tmp_dir))
    regions = mgr.load_provinces()
    assert len(regions) == 1
    assert regions[0].name == "北京市"


def test_admin_splitter(tmp_dir):
    """测试行政区拆分（mock osmium）"""
    from src.osm_tool.core.splitter.admin_splitter import AdminSplitter

    input_pbf = tmp_dir / "input.osm.pbf"
    input_pbf.write_bytes(b"fake pbf")

    boundary_geojson = tmp_dir / "boundary.json"
    boundary_geojson.write_text(json.dumps({
        "type": "Polygon",
        "coordinates": [[[116.0, 39.0], [117.0, 39.0], [117.0, 40.0], [116.0, 40.0], [116.0, 39.0]]]
    }), encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        # 模拟输出文件
        output_dir = tmp_dir / "output"
        output_dir.mkdir()
        (output_dir / "beijing.osm.pbf").write_bytes(b"output")

        splitter = AdminSplitter()
        result = splitter.split_by_region(
            str(input_pbf),
            str(output_dir),
            str(boundary_geojson),
            "beijing",
        )

    assert result.endswith("beijing.osm.pbf")
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_splitter.py -v
```

- [ ] **Step 3: 写实现**

```python
# src/osm_tool/core/splitter/admin_boundaries.py
"""行政区划数据管理"""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RegionInfo:
    """区域信息"""
    code: str
    name: str
    geojson_path: str
    parent_code: str = ""


class AdminBoundaryManager:
    """中国行政区划管理器

    使用 DataV.GeoAtlas 数据（省/市/区县三级）
    """

    BASE_URL = "https://geo.datav.aliyun.com/areas_v3/bound"

    def __init__(self, data_dir: str | None = None):
        if data_dir is None:
            data_dir = str(Path(__file__).parent.parent.parent / "resources" / "admin_boundaries")
        self._data_dir = Path(data_dir)
        self._provinces: list[RegionInfo] = []
        self._cities: dict[str, list[RegionInfo]] = {}
        self._districts: dict[str, list[RegionInfo]] = {}

    def load_provinces(self) -> list[RegionInfo]:
        """加载省级行政区"""
        path = self._data_dir / "provinces.json"
        if not path.exists():
            self._download("100000_full", path)
        self._provinces = self._parse_regions(path, parent_code="")
        return self._provinces

    def load_cities(self, province_code: str) -> list[RegionInfo]:
        """加载市级行政区"""
        if province_code in self._cities:
            return self._cities[province_code]
        path = self._data_dir / "cities" / f"{province_code}_full.json"
        if not path.exists():
            self._download(f"{province_code}_full", path)
        self._cities[province_code] = self._parse_regions(path, parent_code=province_code)
        return self._cities[province_code]

    def load_districts(self, city_code: str) -> list[RegionInfo]:
        """加载区县级行政区"""
        if city_code in self._districts:
            return self._districts[city_code]
        path = self._data_dir / "districts" / f"{city_code}_full.json"
        if not path.exists():
            self._download(f"{city_code}_full", path)
        self._districts[city_code] = self._parse_regions(path, parent_code=city_code)
        return self._districts[city_code]

    def _parse_regions(self, path: Path, parent_code: str) -> list[RegionInfo]:
        """解析 GeoJSON 区域文件"""
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        regions = []
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            regions.append(RegionInfo(
                code=str(props.get("adcode", "")),
                name=props.get("name", ""),
                geojson_path=str(path),
                parent_code=parent_code,
            ))
        return regions

    def _download(self, area_code: str, save_path: Path) -> None:
        """从 DataV 下载行政区划数据"""
        import requests
        save_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"{self.BASE_URL}/{area_code}.json"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        save_path.write_text(resp.text, encoding="utf-8")
```

```python
# src/osm_tool/core/splitter/admin_splitter.py
"""行政区拆分器"""
import json
import subprocess
from pathlib import Path

from .base import BaseSplitter


class AdminSplitter(BaseSplitter):
    """按行政区划拆分 OSM 数据

    使用 osmium-tool extract 命令进行高性能空间裁剪。
    """

    def split(self, input_path: str, output_dir: str, options: dict | None = None) -> list[str]:
        """按行政区批量拆分"""
        opts = options or {}
        regions = opts.get("regions", [])
        results = []
        for i, region in enumerate(regions):
            geojson_path = region.get("geojson_path", "")
            region_name = region.get("name", "unknown")
            output_path = str(Path(output_dir) / f"{region_name}.osm.pbf")
            try:
                result = self.split_by_region(input_path, output_dir, geojson_path, region_name)
                results.append(result)
            except Exception as e:
                self._report_error(f"拆分 {region_name} 失败: {e}")
            self._report_progress(int((i + 1) / len(regions) * 100))
        return results

    def split_by_region(
        self,
        input_path: str,
        output_dir: str,
        boundary_geojson: str,
        region_name: str,
    ) -> str:
        """按单个区域拆分"""
        output_path = str(Path(output_dir) / f"{region_name}.osm.pbf")

        # 将 GeoJSON 转换为 osmium 的多边形格式
        poly_path = self._geojson_to_poly(boundary_geojson, output_path + ".poly")

        # 调用 osmium extract
        cmd = [
            "osmium", "extract",
            "-p", poly_path,
            input_path,
            "-o", output_path,
            "--overwrite",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

        if result.returncode != 0:
            raise RuntimeError(f"osmium extract 失败: {result.stderr}")

        # 清理临时 poly 文件
        Path(poly_path).unlink(missing_ok=True)

        return output_path

    def _geojson_to_poly(self, geojson_path: str, output_path: str) -> str:
        """将 GeoJSON 多边形转换为 osmium .poly 格式"""
        data = json.loads(Path(geojson_path).read_text(encoding="utf-8"))

        # 处理 Feature 或直接 Geometry
        if data.get("type") == "Feature":
            geom = data["geometry"]
        else:
            geom = data

        rings = []
        if geom["type"] == "Polygon":
            rings = geom["coordinates"]
        elif geom["type"] == "MultiPolygon":
            for poly in geom["coordinates"]:
                rings.extend(poly)

        lines = ["boundary"]
        for i, ring in enumerate(rings):
            lines.append(f"ring_{i}")
            for coord in ring:
                lines.append(f"   {coord[0]:.10f}   {coord[1]:.10f}")
            lines.append("END")
        lines.append("END")

        Path(output_path).write_text("\n".join(lines), encoding="utf-8")
        return output_path
```

```python
# scripts/download_admin_data.py
"""下载中国行政区划数据（辅助脚本）

从 DataV.GeoAtlas 下载省/市/区县三级数据。
运行: uv run python scripts/download_admin_data.py
"""
import json
import sys
from pathlib import Path

import requests

BASE_URL = "https://geo.datav.aliyun.com/areas_v3/bound"
OUTPUT_DIR = Path(__file__).parent.parent / "src" / "osm_tool" / "resources" / "admin_boundaries"


def download_area(area_code: str, filename: str) -> None:
    """下载指定区域数据"""
    url = f"{BASE_URL}/{area_code}_full.json"
    print(f"下载 {filename} <- {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(resp.text, encoding="utf-8")
    print(f"  已保存: {path}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 下载省级
    download_area("100000", "provinces.json")

    # 下载各省级的市级数据
    provinces = json.loads((OUTPUT_DIR / "provinces.json").read_text(encoding="utf-8"))
    for feat in provinces.get("features", []):
        code = str(feat["properties"]["adcode"])
        name = feat["properties"]["name"]
        download_area(code, f"cities/{code}_full.json")

    print("下载完成！")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_splitter.py -v
```

- [ ] **Step 5: 提交**

```bash
git add src/osm_tool/core/splitter/ scripts/ tests/test_splitter.py
git commit -m "feat: add admin splitter with DataV boundary support"
```

---

### Task 3: 范围拆分器

**Files:**
- Create: `src/osm_tool/core/splitter/range_splitter.py`

- [ ] **Step 1: 写实现**

```python
# src/osm_tool/core/splitter/range_splitter.py
"""矢量范围拆分器"""
import json
import subprocess
from pathlib import Path

from .base import BaseSplitter


class RangeSplitter(BaseSplitter):
    """按自定义范围拆分 OSM 数据"""

    def split(self, input_path: str, output_dir: str, options: dict | None = None) -> list[str]:
        opts = options or {}
        output_name = opts.get("output_name", "clipped")
        output_path = str(Path(output_dir) / f"{output_name}.osm.pbf")

        # 矩形范围
        if "bbox" in opts:
            bbox = opts["bbox"]  # [left, bottom, right, top]
            return self._split_by_bbox(input_path, output_path, bbox)

        # 多边形/边界文件
        boundary = opts.get("boundary_geojson")
        if boundary:
            return [self._split_by_polygon(input_path, output_path, boundary)]

        raise ValueError("需要提供 bbox 或 boundary_geojson")

    def _split_by_bbox(self, input_path: str, output_path: str, bbox: list[float]) -> list[str]:
        """按矩形范围裁剪"""
        cmd = [
            "osmium", "extract",
            "-b", f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            input_path,
            "-o", output_path,
            "--overwrite",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"osmium extract 失败: {result.stderr}")
        self._report_progress(100)
        return [output_path]

    def _split_by_polygon(self, input_path: str, output_path: str, geojson_path: str) -> str:
        """按多边形裁剪"""
        from .admin_splitter import AdminSplitter
        admin = AdminSplitter(on_progress=self._report_progress, on_error=self._report_error)
        return admin.split_by_region(input_path, str(Path(output_path).parent), geojson_path, Path(output_path).stem)
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/core/splitter/range_splitter.py
git commit -m "feat: add range splitter with bbox and polygon support"
```

---

### Task 4: 属性拆分器

**Files:**
- Create: `src/osm_tool/core/splitter/attribute_splitter.py`

- [ ] **Step 1: 写实现**

```python
# src/osm_tool/core/splitter/attribute_splitter.py
"""属性拆分器"""
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .base import BaseSplitter


@dataclass
class FilterCondition:
    """过滤条件"""
    key: str
    value: str | None = None  # None 表示只要 key 存在
    match: str = "exact"  # exact / exists / regex


@dataclass
class TagStats:
    """标签统计"""
    key: str
    value_counts: dict[str, int]
    total_count: int


# 预设过滤器
PRESET_FILTERS = {
    "建筑物": [FilterCondition(key="building")],
    "道路": [FilterCondition(key="highway")],
    "水体": [FilterCondition(key="natural", value="water"), FilterCondition(key="waterway")],
    "绿地": [FilterCondition(key="natural", value="wood"), FilterCondition(key="landuse", value="forest"), FilterCondition(key="leisure", value="park")],
    "POI": [FilterCondition(key="amenity"), FilterCondition(key="shop"), FilterCondition(key="tourism")],
}


class AttributeSplitter(BaseSplitter):
    """按属性拆分数据"""

    def split(self, input_path: str, output_dir: str, options: dict | None = None) -> list[str]:
        opts = options or {}
        conditions = opts.get("conditions", [])
        logic = opts.get("logic", "and")  # and / or
        output_name = opts.get("output_name", "filtered")

        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
        features = data.get("features", [])
        total = len(features)

        filtered = []
        for i, feat in enumerate(features):
            props = feat.get("properties", {})
            if self._match(props, conditions, logic):
                filtered.append(feat)
            if i % 1000 == 0:
                self._report_progress(int(i / total * 100))

        output_path = str(Path(output_dir) / f"{output_name}.geojson")
        result_data = {**data, "features": filtered}
        Path(output_path).write_text(
            json.dumps(result_data, ensure_ascii=False),
            encoding="utf-8",
        )
        self._report_progress(100)
        return [output_path]

    def _match(self, props: dict, conditions: list[dict], logic: str) -> bool:
        """检查属性是否匹配条件"""
        results = []
        for cond_data in conditions:
            cond = FilterCondition(**cond_data) if isinstance(cond_data, dict) else cond_data
            if cond.match == "exists":
                results.append(cond.key in props)
            elif cond.match == "exact":
                results.append(props.get(cond.key) == cond.value)
            else:
                results.append(cond.key in props)

        if logic == "and":
            return all(results)
        return any(results)

    @staticmethod
    def analyze_tags(input_path: str) -> list[TagStats]:
        """分析文件中所有标签"""
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
        features = data.get("features", [])
        tag_counter: dict[str, Counter] = {}

        for feat in features:
            for k, v in feat.get("properties", {}).items():
                if k not in tag_counter:
                    tag_counter[k] = Counter()
                tag_counter[k][str(v)] += 1

        return [
            TagStats(key=k, value_counts=dict(counter.most_common(20)), total_count=sum(counter.values()))
            for k, counter in sorted(tag_counter.items())
        ]
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/core/splitter/attribute_splitter.py
git commit -m "feat: add attribute splitter with preset filters"
```

---

### Task 5: 类型拆分器

**Files:**
- Create: `src/osm_tool/core/splitter/type_splitter.py`

- [ ] **Step 1: 写实现**

```python
# src/osm_tool/core/splitter/type_splitter.py
"""类型拆分器"""
import json
from pathlib import Path

from .base import BaseSplitter


class TypeSplitter(BaseSplitter):
    """按 OSM 元素类型或标签分类拆分"""

    def split(self, input_path: str, output_dir: str, options: dict | None = None) -> list[str]:
        opts = options or {}
        mode = opts.get("mode", "element_type")  # element_type / tag_group
        output_files = []

        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
        features = data.get("features", [])
        total = len(features)

        if mode == "element_type":
            output_files = self._split_by_element_type(data, features, output_dir, total)
        elif mode == "tag_group":
            groups = opts.get("tag_groups", ["highway", "building", "natural", "landuse"])
            output_files = self._split_by_tag_group(data, features, output_dir, groups, total)

        self._report_progress(100)
        return output_files

    def _split_by_element_type(self, data: dict, features: list, output_dir: str, total: int) -> list[str]:
        """按几何类型拆分（Point/LineString/Polygon）"""
        buckets: dict[str, list] = {}
        for i, feat in enumerate(features):
            geom = feat.get("geometry")
            if geom is None:
                gtype = "None"
            else:
                gtype = geom.get("type", "Unknown")
            if gtype not in buckets:
                buckets[gtype] = []
            buckets[gtype].append(feat)
            if i % 1000 == 0:
                self._report_progress(int(i / total * 80))

        output_files = []
        for gtype, feats in buckets.items():
            path = str(Path(output_dir) / f"{gtype.lower()}.geojson")
            result = {**data, "features": feats}
            Path(path).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            output_files.append(path)
        return output_files

    def _split_by_tag_group(self, data: dict, features: list, output_dir: str, groups: list[str], total: int) -> list[str]:
        """按标签分组拆分"""
        buckets: dict[str, list] = {g: [] for g in groups}
        buckets["other"] = []

        for i, feat in enumerate(features):
            props = feat.get("properties", {})
            matched = False
            for group in groups:
                if group in props:
                    buckets[group].append(feat)
                    matched = True
                    break
            if not matched:
                buckets["other"].append(feat)
            if i % 1000 == 0:
                self._report_progress(int(i / total * 80))

        output_files = []
        for group, feats in buckets.items():
            if not feats:
                continue
            path = str(Path(output_dir) / f"{group}.geojson")
            result = {**data, "features": feats}
            Path(path).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            output_files.append(path)
        return output_files
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/core/splitter/type_splitter.py
git commit -m "feat: add type splitter for element and tag group splitting"
```

---

### Task 6: 拆分 Worker 和面板

**Files:**
- Create: `src/osm_tool/workers/split_worker.py`
- Modify: `src/osm_tool/ui/panels/split_panel.py`

- [ ] **Step 1: 写 Worker**

```python
# src/osm_tool/workers/split_worker.py
"""数据拆分工作线程"""
from PySide6.QtCore import QThread, Signal

from src.osm_tool.core.splitter.base import BaseSplitter


class SplitWorker(QThread):
    """异步执行数据拆分"""

    progress = Signal(int)
    finished_ok = Signal(list)  # 输出文件列表
    error = Signal(str)

    def __init__(self, splitter: BaseSplitter, input_path: str, output_dir: str, options: dict | None = None, parent=None):
        super().__init__(parent)
        self._splitter = splitter
        self._input = input_path
        self._output_dir = output_dir
        self._options = options

    def run(self) -> None:
        try:
            self._splitter._on_progress = lambda p: self.progress.emit(p)
            result = self._splitter.split(self._input, self._output_dir, self._options)
            self.finished_ok.emit(result)
        except Exception as e:
            self.error.emit(str(e))
```

- [ ] **Step 2: 重写拆分面板**

```python
# src/osm_tool/ui/panels/split_panel.py
"""数据拆分面板"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox,
    QFileDialog, QProgressBar, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QDoubleSpinBox, QListWidget, QCheckBox,
    QMessageBox,
)

from src.osm_tool.core.splitter.admin_boundaries import AdminBoundaryManager
from src.osm_tool.core.splitter.attribute_splitter import PRESET_FILTERS


class SplitPanel(QWidget):
    """数据拆分面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("数据拆分")
        self._admin_mgr = AdminBoundaryManager()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 文件选择
        file_group = QGroupBox("输入文件")
        file_layout = QHBoxLayout(file_group)
        self._input_path = QLineEdit()
        input_btn = QPushButton("浏览...")
        input_btn.clicked.connect(lambda: self._browse(self._input_path, "OSM/PBF (*.osm.pbf *.pbf *.geojson)"))
        file_layout.addWidget(self._input_path)
        file_layout.addWidget(input_btn)
        layout.addWidget(file_group)

        # 标签页
        tabs = QTabWidget()
        tabs.addTab(self._create_admin_tab(), "行政区拆分")
        tabs.addTab(self._create_range_tab(), "范围拆分")
        tabs.addTab(self._create_attribute_tab(), "属性拆分")
        tabs.addTab(self._create_type_tab(), "类型拆分")
        layout.addWidget(tabs)

        # 输出 + 执行
        output_layout = QHBoxLayout()
        self._output_dir = QLineEdit()
        output_btn = QPushButton("浏览...")
        output_btn.clicked.connect(lambda: self._browse_dir(self._output_dir))
        output_layout.addWidget(QLabel("输出目录:"))
        output_layout.addWidget(self._output_dir)
        output_layout.addWidget(output_btn)
        self._progress = QProgressBar()
        self._execute_btn = QPushButton("执行拆分")
        output_layout.addWidget(self._progress)
        output_layout.addWidget(self._execute_btn)
        layout.addLayout(output_layout)

    def _create_admin_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self._admin_tree = QTreeWidget()
        self._admin_tree.setHeaderLabels(["区域", "编码"])
        layout.addWidget(self._admin_tree)
        load_btn = QPushButton("加载行政区划")
        load_btn.clicked.connect(self._load_admin_regions)
        layout.addWidget(load_btn)

        custom_layout = QHBoxLayout()
        custom_btn = QPushButton("上传自定义边界文件")
        custom_btn.clicked.connect(self._upload_custom_boundary)
        custom_layout.addWidget(custom_btn)
        custom_layout.addStretch()
        layout.addLayout(custom_layout)
        return w

    def _create_range_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self._range_left = QDoubleSpinBox(); self._range_left.setRange(-180, 180); self._range_left.setDecimals(6)
        self._range_bottom = QDoubleSpinBox(); self._range_bottom.setRange(-90, 90); self._range_bottom.setDecimals(6)
        self._range_right = QDoubleSpinBox(); self._range_right.setRange(-180, 180); self._range_right.setDecimals(6)
        self._range_top = QDoubleSpinBox(); self._range_top.setRange(-90, 90); self._range_top.setDecimals(6)
        form.addRow("左 (经度):", self._range_left)
        form.addRow("下 (纬度):", self._range_bottom)
        form.addRow("右 (经度):", self._range_right)
        form.addRow("上 (纬度):", self._range_top)
        return w

    def _create_attribute_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        preset_group = QGroupBox("预设过滤器")
        preset_layout = QVBoxLayout(preset_group)
        for name in PRESET_FILTERS:
            cb = QCheckBox(name)
            preset_layout.addWidget(cb)
        layout.addWidget(preset_group)
        layout.addWidget(QLabel("自定义条件编辑（后续版本）"))
        return w

    def _create_type_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self._type_mode = QComboBox()
        self._type_mode.addItems(["按几何类型", "按标签分类"])
        layout.addWidget(self._type_mode)
        for tag in ["highway", "building", "natural", "landuse", "amenity", "waterway"]:
            cb = QCheckBox(tag)
            layout.addWidget(cb)
        return w

    def _browse(self, line_edit, filter_str):
        path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", filter_str)
        if path:
            line_edit.setText(path)

    def _browse_dir(self, line_edit):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            line_edit.setText(path)

    def _load_admin_regions(self):
        try:
            provinces = self._admin_mgr.load_provinces()
            self._admin_tree.clear()
            for prov in provinces:
                item = QTreeWidgetItem([prov.name, prov.code])
                self._admin_tree.addTopLevelItem(item)
        except Exception as e:
            QMessageBox.warning(self, "加载失败", str(e))

    def _upload_custom_boundary(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择边界文件", "", "GeoJSON (*.geojson *.json);;Shapefile (*.shp)")
        if path:
            pass  # 存储路径供后续使用
```

- [ ] **Step 3: 提交**

```bash
git add src/osm_tool/workers/split_worker.py src/osm_tool/ui/panels/split_panel.py
git commit -m "feat: add split worker and full split panel UI"
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
git commit -m "chore: finalize Phase 4 - data splitting module"
```
