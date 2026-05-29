# Phase 1: 项目基础 + GUI 骨架 + 下载模块

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 搭建项目框架和 GUI 骨架，实现三大 OSM 数据源下载功能，支持断点续传

**Architecture:** PySide6 单体架构，QThread 异步下载，core/ui 分层

**Tech Stack:** PySide6, requests, pytest, uv

---

## 文件结构

```
osm-download/
├── pyproject.toml
├── src/osm_tool/
│   ├── __init__.py
│   ├── main.py                          # 应用入口
│   ├── app.py                           # QApplication 配置
│   ├── models/
│   │   ├── __init__.py
│   │   ├── download_task.py             # 下载数据模型
│   │   └── task_state.py                # 任务状态枚举
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── environment.py               # 外部工具检测
│   │   └── logger.py                    # 日志配置
│   ├── core/
│   │   ├── __init__.py
│   │   └── downloader/
│   │       ├── __init__.py
│   │       ├── base.py                  # 下载器基类
│   │       ├── geofabrik.py             # Geofabrik 下载器
│   │       ├── overpass.py              # Overpass 下载器
│   │       └── bbox.py                  # BBox 下载器
│   ├── workers/
│   │   ├── __init__.py
│   │   └── download_worker.py           # QThread 下载工作线程
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py               # 主窗口
│       ├── panels/
│       │   ├── __init__.py
│       │   ├── download_panel.py        # 下载面板
│       │   ├── split_panel.py           # 占位
│       │   ├── process_panel.py         # 占位
│       │   ├── convert_panel.py         # 占位
│       │   └── publish_panel.py         # 占位
│       ├── widgets/
│       │   └── __init__.py
│       └── dialogs/
│           └── __init__.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_models.py
    ├── test_environment.py
    ├── test_geofabrik.py
    ├── test_overpass.py
    └── test_bbox.py
```

---

### Task 1: 项目初始化

**Files:**
- Create: `pyproject.toml`
- Create: `src/osm_tool/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "osm-tool"
version = "0.1.0"
description = "OSM 数据下载、处理、转换、发布桌面工具"
requires-python = ">=3.10"
dependencies = [
    "PySide6>=6.6",
    "requests>=2.31",
    "psutil>=5.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.12",
]

[project.scripts]
osm-tool = "osm_tool.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/osm_tool"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: 创建包结构**

```python
# src/osm_tool/__init__.py
"""OSM Data Toolbox - OSM 数据下载、处理、转换、发布桌面工具"""
__version__ = "0.1.0"
```

```python
# tests/__init__.py
```

```python
# tests/conftest.py
"""测试公共 fixtures"""
import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def tmp_dir():
    """临时目录 fixture"""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_pbf_url():
    """Geofabrik 示例 URL"""
    return "https://download.geofabrik.de/asia/china-latest.osm.pbf"
```

- [ ] **Step 3: 初始化 git 并提交**

```bash
cd E:/oliver/learn/osm-download
git init
uv init --no-workspace
```

然后手动创建上述文件，最后：

```bash
git add pyproject.toml src/ tests/
git commit -m "chore: initialize project structure with uv and PySide6"
```

---

### Task 2: 数据模型

**Files:**
- Create: `src/osm_tool/models/__init__.py`
- Create: `src/osm_tool/models/task_state.py`
- Create: `src/osm_tool/models/download_task.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_models.py
"""数据模型测试"""
from src.osm_tool.models.task_state import TaskState
from src.osm_tool.models.download_task import DownloadTask


def test_task_state_values():
    """测试任务状态枚举值"""
    assert TaskState.PENDING.value == "pending"
    assert TaskState.DOWNLOADING.value == "downloading"
    assert TaskState.PAUSED.value == "paused"
    assert TaskState.COMPLETED.value == "completed"
    assert TaskState.FAILED.value == "failed"
    assert TaskState.CANCELLED.value == "cancelled"


def test_create_download_task():
    """测试创建下载任务"""
    task = DownloadTask(
        url="https://example.com/test.osm.pbf",
        save_path="/tmp/test.osm.pbf",
        source_type="geofabrik",
    )
    assert task.url == "https://example.com/test.osm.pbf"
    assert task.save_path == "/tmp/test.osm.pbf"
    assert task.source_type == "geofabrik"
    assert task.state == TaskState.PENDING
    assert task.total_bytes == 0
    assert task.downloaded_bytes == 0
    assert task.etag is None


def test_download_task_progress():
    """测试下载进度计算"""
    task = DownloadTask(
        url="https://example.com/test.osm.pbf",
        save_path="/tmp/test.osm.pbf",
        source_type="geofabrik",
        total_bytes=1000,
        downloaded_bytes=500,
    )
    assert task.progress == 50.0


def test_download_task_progress_zero_total():
    """测试总大小为 0 时进度为 0"""
    task = DownloadTask(
        url="https://example.com/test.osm.pbf",
        save_path="/tmp/test.osm.pbf",
        source_type="geofabrik",
    )
    assert task.progress == 0.0


def test_download_task_to_meta(tmp_dir):
    """测试序列化为 meta 文件"""
    task = DownloadTask(
        url="https://example.com/test.osm.pbf",
        save_path=str(tmp_dir / "test.osm.pbf"),
        source_type="geofabrik",
        total_bytes=1000,
        downloaded_bytes=500,
        etag="abc123",
    )
    meta_path = task.to_meta_file()
    assert meta_path.exists()

    loaded = DownloadTask.from_meta_file(meta_path)
    assert loaded.url == task.url
    assert loaded.total_bytes == task.total_bytes
    assert loaded.downloaded_bytes == task.downloaded_bytes
    assert loaded.etag == task.etag
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_models.py -v
```

Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: 写实现**

```python
# src/osm_tool/models/__init__.py
"""数据模型"""
from .task_state import TaskState
from .download_task import DownloadTask

__all__ = ["TaskState", "DownloadTask"]
```

```python
# src/osm_tool/models/task_state.py
"""任务状态枚举"""
from enum import Enum


class TaskState(Enum):
    """下载任务状态"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

```python
# src/osm_tool/models/download_task.py
"""下载数据模型"""
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from .task_state import TaskState


@dataclass
class DownloadTask:
    """下载任务数据模型"""
    url: str
    save_path: str
    source_type: str  # geofabrik / overpass / bbox
    state: TaskState = TaskState.PENDING
    total_bytes: int = 0
    downloaded_bytes: int = 0
    etag: str | None = None
    last_modified: str | None = None
    error_message: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def progress(self) -> float:
        """下载进度百分比"""
        if self.total_bytes <= 0:
            return 0.0
        return round(self.downloaded_bytes / self.total_bytes * 100, 2)

    @property
    def meta_path(self) -> Path:
        """meta 文件路径（与下载文件同目录，后缀 .download_meta）"""
        p = Path(self.save_path)
        return p.with_suffix(p.suffix + ".download_meta")

    def to_meta_file(self) -> Path:
        """将任务信息保存为 meta 文件"""
        data = {
            "url": self.url,
            "save_path": self.save_path,
            "source_type": self.source_type,
            "total_bytes": self.total_bytes,
            "downloaded_bytes": self.downloaded_bytes,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "created_at": self.created_at,
            "updated_at": datetime.now().isoformat(),
        }
        meta = self.meta_path
        meta.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return meta

    @classmethod
    def from_meta_file(cls, meta_path: Path) -> "DownloadTask":
        """从 meta 文件加载任务"""
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return cls(
            url=data["url"],
            save_path=data["save_path"],
            source_type=data["source_type"],
            total_bytes=data.get("total_bytes", 0),
            downloaded_bytes=data.get("downloaded_bytes", 0),
            etag=data.get("etag"),
            last_modified=data.get("last_modified"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_models.py -v
```

Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add src/osm_tool/models/ tests/test_models.py
git commit -m "feat: add download task data model and task state enum"
```

---

### Task 3: 环境检测与日志工具

**Files:**
- Create: `src/osm_tool/utils/__init__.py`
- Create: `src/osm_tool/utils/environment.py`
- Create: `src/osm_tool/utils/logger.py`
- Test: `tests/test_environment.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_environment.py
"""环境检测测试"""
from src.osm_tool.utils.environment import check_tool_available, ToolCheckResult


def test_check_tool_available_python():
    """测试检测 python（一定存在）"""
    result = check_tool_available("python")
    assert isinstance(result, ToolCheckResult)
    assert result.name == "python"
    assert result.available is True
    assert result.path is not None


def test_check_tool_available_nonexistent():
    """测试检测不存在的工具"""
    result = check_tool_available("nonexistent_tool_xyz_12345")
    assert result.available is False
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_environment.py -v
```

- [ ] **Step 3: 写实现**

```python
# src/osm_tool/utils/__init__.py
"""工具函数"""
```

```python
# src/osm_tool/utils/environment.py
"""外部工具环境检测"""
import shutil
from dataclasses import dataclass


@dataclass
class ToolCheckResult:
    """工具检测结果"""
    name: str
    available: bool
    path: str | None = None
    version: str | None = None


def check_tool_available(tool_name: str) -> ToolCheckResult:
    """检测外部工具是否可用

    Args:
        tool_name: 工具名称，如 ogr2ogr, osmium, tippecanoe

    Returns:
        ToolCheckResult 检测结果
    """
    path = shutil.which(tool_name)
    if path is not None:
        return ToolCheckResult(name=tool_name, available=True, path=path)
    return ToolCheckResult(name=tool_name, available=False)


def check_all_tools() -> dict[str, ToolCheckResult]:
    """检测所有外部工具"""
    tools = ["ogr2ogr", "osmium", "tippecanoe", "java"]
    return {name: check_tool_available(name) for name in tools}
```

```python
# src/osm_tool/utils/logger.py
"""日志配置"""
import logging
import sys
from pathlib import Path


def setup_logger(
    name: str = "osm_tool",
    level: int = logging.INFO,
    log_file: Path | None = None,
) -> logging.Logger:
    """配置日志

    Args:
        name: logger 名称
        level: 日志级别
        log_file: 日志文件路径（可选）

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_fmt = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%H:%M:%S")
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # 文件输出
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)

    return logger
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_environment.py -v
```

Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add src/osm_tool/utils/ tests/test_environment.py
git commit -m "feat: add environment check and logger utilities"
```

---

### Task 4: 下载器基类

**Files:**
- Create: `src/osm_tool/core/__init__.py`
- Create: `src/osm_tool/core/downloader/__init__.py`
- Create: `src/osm_tool/core/downloader/base.py`

- [ ] **Step 1: 写基类**

```python
# src/osm_tool/core/__init__.py
"""核心业务逻辑"""
```

```python
# src/osm_tool/core/downloader/__init__.py
"""下载模块"""
```

```python
# src/osm_tool/core/downloader/base.py
"""下载器抽象基类"""
from abc import ABC, abstractmethod
from typing import Callable

from src.osm_tool.models.download_task import DownloadTask
from src_osm_tool.models.task_state import TaskState


class BaseDownloader(ABC):
    """下载器抽象基类

    所有下载器必须继承此类并实现 download 方法。
    通过回调函数汇报进度和状态。
    """

    def __init__(
        self,
        task: DownloadTask,
        on_progress: Callable[[int, int, float] | None] = None,
        on_state_change: Callable[[TaskState], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        """
        Args:
            task: 下载任务
            on_progress: 进度回调 (downloaded_bytes, total_bytes, speed_bytes_per_sec)
            on_state_change: 状态变更回调
            on_error: 错误回调
        """
        self._task = task
        self._on_progress = on_progress
        self._on_state_change = on_state_change
        self._on_error = on_error
        self._is_cancelled = False
        self._is_paused = False

    @property
    def task(self) -> DownloadTask:
        return self._task

    @abstractmethod
    def download(self) -> None:
        """执行下载（阻塞），由 QThread 调用"""
        ...

    def cancel(self) -> None:
        """取消下载"""
        self._is_cancelled = True
        self._set_state(TaskState.CANCELLED)

    def pause(self) -> None:
        """暂停下载"""
        self._is_paused = True
        self._set_state(TaskState.PAUSED)

    def resume(self) -> None:
        """恢复下载"""
        self._is_paused = False
        self._set_state(TaskState.DOWNLOADING)

    def _set_state(self, state: TaskState) -> None:
        """设置状态并触发回调"""
        self._task.state = state
        if self._on_state_change:
            self._on_state_change(state)

    def _report_progress(self, downloaded: int, total: int, speed: float) -> None:
        """汇报进度"""
        self._task.downloaded_bytes = downloaded
        self._task.total_bytes = total
        if self._on_progress:
            self._on_progress(downloaded, total, speed)

    def _report_error(self, msg: str) -> None:
        """汇报错误"""
        self._task.error_message = msg
        self._set_state(TaskState.FAILED)
        if self._on_error:
            self._on_error(msg)
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/core/
git commit -m "feat: add base downloader abstract class"
```

---

### Task 5: Geofabrik 下载器

**Files:**
- Create: `src/osm_tool/core/downloader/geofabrik.py`
- Test: `tests/test_geofabrik.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_geofabrik.py
"""Geofabrik 下载器测试"""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.osm_tool.core.downloader.geofabrik import (
    GeofabrikDownloader,
    GeofabrikIndex,
    RegionInfo,
)
from src_osm_tool.models.download_task import DownloadTask
from src_osm_tool.models.task_state import TaskState


def test_region_info_creation():
    """测试区域信息创建"""
    region = RegionInfo(
        id="china",
        name="China",
        parent_id="asia",
        url="https://download.geofabrik.de/asia/china-latest.osm.pbf",
        size_bytes=1000000,
    )
    assert region.id == "china"
    assert region.name == "China"
    assert region.size_bytes == 1000000


def test_geofabrik_index_parse():
    """测试 Geofabrik 索引解析"""
    mock_data = {
        "features": [
            {
                "properties": {
                    "id": "asia",
                    "name": "Asia",
                    "parent": None,
                    "urls": {
                        "pbf": "https://download.geofabrik.de/asia-latest.osm.pbf"
                    },
                    "size": 5000000000,
                }
            },
            {
                "properties": {
                    "id": "china",
                    "name": "China",
                    "parent": "asia",
                    "urls": {
                        "pbf": "https://download.geofabrik.de/asia/china-latest.osm.pbf"
                    },
                    "size": 1000000000,
                }
            },
        ]
    }

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        index = GeofabrikIndex()
        regions = index.fetch_index()

    assert len(regions) == 2
    assert regions[0].id == "asia"
    assert regions[0].name == "Asia"
    assert regions[1].id == "china"
    assert regions[1].parent_id == "asia"


def test_geofabrik_download_new(tmp_dir):
    """测试全新下载"""
    save_path = str(tmp_dir / "test.osm.pbf")
    task = DownloadTask(
        url="https://example.com/test.osm.pbf",
        save_path=save_path,
        source_type="geofabrik",
    )
    # mock HTTP 响应
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"x" * 100]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        states = []
        downloader = GeofabrikDownloader(
            task=task,
            on_state_change=lambda s: states.append(s),
        )
        downloader.download()

    assert task.state == TaskState.COMPLETED
    assert Path(save_path).exists()
    assert task.downloaded_bytes == 100


def test_geofabrik_resume(tmp_dir):
    """测试断点续传"""
    save_path = str(tmp_dir / "test.osm.pbf")
    # 写入已有文件
    Path(save_path).write_bytes(b"x" * 50)

    task = DownloadTask(
        url="https://example.com/test.osm.pbf",
        save_path=save_path,
        source_type="geofabrik",
        total_bytes=100,
        downloaded_bytes=50,
    )

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "50"}
        mock_resp.iter_content.return_value = [b"y" * 50]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        downloader = GeofabrikDownloader(task=task)
        downloader.download()

    assert task.state == TaskState.COMPLETED
    content = Path(save_path).read_bytes()
    assert len(content) == 100  # 50 原有 + 50 新增
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_geofabrik.py -v
```

- [ ] **Step 3: 写实现**

```python
# src/osm_tool/core/downloader/geofabrik.py
"""Geofabrik 下载器"""
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from src.osm_tool.core.downloader.base import BaseDownloader
from src_osm_tool.models.download_task import DownloadTask
from src_osm_tool.models.task_state import TaskState

GEOFABRIK_INDEX_URL = "https://download.geofabrik.de/index.json"


@dataclass
class RegionInfo:
    """Geofabrik 区域信息"""
    id: str
    name: str
    parent_id: str | None
    url: str
    size_bytes: int
    updated: str | None = None


class GeofabrikIndex:
    """Geofabrik 区域索引"""

    def __init__(self):
        self._regions: list[RegionInfo] = []

    def fetch_index(self) -> list[RegionInfo]:
        """获取并解析 Geofabrik 索引"""
        resp = requests.get(GEOFABRIK_INDEX_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        self._regions = self._parse_index(data)
        return self._regions

    def _parse_index(self, data: dict) -> list[RegionInfo]:
        """解析索引 JSON"""
        regions = []
        features = data.get("features", [])
        for feat in features:
            props = feat.get("properties", {})
            urls = props.get("urls", {})
            regions.append(RegionInfo(
                id=props.get("id", ""),
                name=props.get("name", ""),
                parent_id=props.get("parent"),
                url=urls.get("pbf", ""),
                size_bytes=props.get("size", 0),
            ))
        return regions

    def get_children(self, parent_id: str | None) -> list[RegionInfo]:
        """获取子区域"""
        return [r for r in self._regions if r.parent_id == parent_id]

    def get_region(self, region_id: str) -> RegionInfo | None:
        """按 ID 查找区域"""
        for r in self._regions:
            if r.id == region_id:
                return r
        return None


class GeofabrikDownloader(BaseDownloader):
    """Geofabrik 下载器，支持断点续传"""

    CHUNK_SIZE = 1024 * 64  # 64KB

    def download(self) -> None:
        """执行下载"""
        self._set_state(TaskState.DOWNLOADING)
        save_path = Path(self._task.save_path)

        # 检查是否需要续传
        existing_size = save_path.stat().st_size if save_path.exists() else 0
        headers = {}
        if existing_size > 0:
            headers["Range"] = f"bytes={existing_size}-"

        try:
            resp = requests.get(
                self._task.url,
                headers=headers,
                stream=True,
                timeout=60,
            )
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            if existing_size > 0 and total > 0:
                total += existing_size  # Range 返回剩余大小
            self._task.total_bytes = max(total, existing_size)

            # 写入文件（追加模式）
            mode = "ab" if existing_size > 0 else "wb"
            downloaded = existing_size
            start_time = time.time()

            with open(save_path, mode) as f:
                for chunk in resp.iter_content(chunk_size=self.CHUNK_SIZE):
                    if self._is_cancelled:
                        return
                    f.write(chunk)
                    downloaded += len(chunk)

                    # 计算速度
                    elapsed = time.time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0
                    self._report_progress(downloaded, self._task.total_bytes, speed)

            # 保存 meta 文件
            self._task.downloaded_bytes = downloaded
            self._task.to_meta_file()
            self._set_state(TaskState.COMPLETED)

        except Exception as e:
            # 保存进度以便续传
            if save_path.exists():
                self._task.to_meta_file()
            self._report_error(str(e))
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_geofabrik.py -v
```

Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add src/osm_tool/core/downloader/geofabrik.py tests/test_geofabrik.py
git commit -m "feat: add Geofabrik downloader with resume support"
```

---

### Task 6: Overpass 下载器

**Files:**
- Create: `src/osm_tool/core/downloader/overpass.py`
- Test: `tests/test_overpass.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_overpass.py
"""Overpass 下载器测试"""
from unittest.mock import patch, MagicMock

from src.osm_tool.core.downloader.overpass import OverpassDownloader
from src_osm_tool.models.download_task import DownloadTask
from src_osm_tool.models.task_state import TaskState


def test_overpass_download(tmp_dir):
    """测试 Overpass 下载"""
    save_path = str(tmp_dir / "overpass.json")
    task = DownloadTask(
        url="https://overpass-api.de/api/interpreter",
        save_path=save_path,
        source_type="overpass",
    )

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [b'{"elements":[]}']
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        states = []
        downloader = OverpassDownloader(
            task=task,
            query="[out:json];way(around:100,39.9,116.4);out;",
            output_format="json",
            on_state_change=lambda s: states.append(s),
        )
        downloader.download()

    assert task.state == TaskState.COMPLETED
    assert states[-1] == TaskState.COMPLETED


def test_overpass_cancel(tmp_dir):
    """测试 Overpass 取消"""
    save_path = str(tmp_dir / "overpass.json")
    task = DownloadTask(
        url="https://overpass-api.de/api/interpreter",
        save_path=save_path,
        source_type="overpass",
    )
    downloader = OverpassDownloader(
        task=task,
        query="[out:json];way(around:100,39.9,116.4);out;",
    )
    downloader.cancel()
    assert task.state == TaskState.CANCELLED
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_overpass.py -v
```

- [ ] **Step 3: 写实现**

```python
# src/osm_tool/core/downloader/overpass.py
"""Overpass API 下载器"""
from pathlib import Path

import requests

from src.osm_tool.core.downloader.base import BaseDownloader
from src_osm_tool.models.task_state import TaskState


class OverpassDownloader(BaseDownloader):
    """Overpass API 下载器

    发送 Overpass QL 查询并保存结果。
    """

    CHUNK_SIZE = 1024 * 64

    def __init__(self, task, query: str, output_format: str = "json", **kwargs):
        """
        Args:
            task: 下载任务
            query: Overpass QL 查询字符串
            output_format: 输出格式 json 或 xml
        """
        super().__init__(task, **kwargs)
        self._query = query
        self._output_format = output_format

    def download(self) -> None:
        """执行 Overpass 查询并下载结果"""
        self._set_state(TaskState.DOWNLOADING)
        save_path = Path(self._task.save_path)

        try:
            # Overpass 使用 POST 请求
            data_param = "data"
            resp = requests.post(
                self._task.url,
                data={data_param: self._query},
                stream=True,
                timeout=600,  # Overpass 查询可能很慢
            )
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            self._task.total_bytes = total
            downloaded = 0

            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=self.CHUNK_SIZE):
                    if self._is_cancelled:
                        return
                    f.write(chunk)
                    downloaded += len(chunk)
                    self._report_progress(downloaded, total, 0)

            self._task.downloaded_bytes = downloaded
            self._set_state(TaskState.COMPLETED)

        except requests.exceptions.Timeout:
            self._report_error("Overpass 查询超时，请缩小查询范围或稍后重试")
        except Exception as e:
            self._report_error(str(e))
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_overpass.py -v
```

- [ ] **Step 5: 提交**

```bash
git add src/osm_tool/core/downloader/overpass.py tests/test_overpass.py
git commit -m "feat: add Overpass API downloader"
```

---

### Task 7: BBox 下载器

**Files:**
- Create: `src/osm_tool/core/downloader/bbox.py`
- Test: `tests/test_bbox.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_bbox.py
"""BBox 下载器测试"""
from unittest.mock import patch, MagicMock

from src.osm_tool.core.downloader.bbox import BBoxDownloader
from src_osm_tool.models.download_task import DownloadTask
from src_osm_tool.models.task_state import TaskState


def test_bbox_download(tmp_dir):
    """测试 BBox 下载"""
    save_path = str(tmp_dir / "bbox.osm")
    task = DownloadTask(
        url="https://api.openstreetmap.org/api/0.6/map",
        save_path=save_path,
        source_type="bbox",
    )

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "200"}
        mock_resp.iter_content.return_value = [b"<osm>" + b"x" * 195 + b"</osm>"]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        downloader = BBoxDownloader(
            task=task,
            left=116.3,
            bottom=39.8,
            right=116.5,
            top=40.0,
        )
        downloader.download()

    assert task.state == TaskState.COMPLETED
    assert task.downloaded_bytes == 200


def test_bbox_area_too_large(tmp_dir):
    """测试 BBox 面积过大时报错"""
    save_path = str(tmp_dir / "bbox.osm")
    task = DownloadTask(
        url="https://api.openstreetmap.org/api/0.6/map",
        save_path=save_path,
        source_type="bbox",
    )
    downloader = BBoxDownloader(
        task=task,
        left=116.0,
        bottom=39.0,
        right=117.0,
        top=40.0,
    )
    # 1° × 1° ≈ 0.25° 超过 OSM API 限制
    # OSM API 限制约 0.25 度²
    downloader.download()
    assert task.state == TaskState.FAILED
    assert "过大" in task.error_message
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_bbox.py -v
```

- [ ] **Step 3: 写实现**

```python
# src/osm_tool/core/downloader/bbox.py
"""BBox 下载器"""
from pathlib import Path

import requests

from src.osm_tool.core.downloader.base import BaseDownloader
from src_osm_tool.models.task_state import TaskState

# OSM API 面积限制（约 0.25 度²）
MAX_BBOX_AREA = 0.25


class BBoxDownloader(BaseDownloader):
    """按经纬度范围（BBox）下载 OSM 数据"""

    CHUNK_SIZE = 1024 * 64

    def __init__(self, task, left: float, bottom: float, right: float, top: float, **kwargs):
        """
        Args:
            task: 下载任务
            left: 左边界经度
            bottom: 下边界纬度
            right: 右边界经度
            top: 上边界纬度
        """
        super().__init__(task, **kwargs)
        self._left = left
        self._bottom = bottom
        self._right = right
        self._top = top

    def download(self) -> None:
        """执行 BBox 下载"""
        # 检查面积
        area = (self._right - self._left) * (self._top - self._bottom)
        if area > MAX_BBOX_AREA:
            self._report_error(
                f"请求区域面积 ({area:.2f}°²) 过大，OSM API 限制为 {MAX_BBOX_AREA}°²。"
                f"请缩小范围或使用 Geofabrik 下载。"
            )
            return

        self._set_state(TaskState.DOWNLOADING)
        save_path = Path(self._task.save_path)

        bbox = f"{self._left},{self._bottom},{self._right},{self._top}"
        url = f"{self._task.url}?bbox={bbox}"

        try:
            resp = requests.get(url, stream=True, timeout=120)
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            self._task.total_bytes = total
            downloaded = 0

            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=self.CHUNK_SIZE):
                    if self._is_cancelled:
                        return
                    f.write(chunk)
                    downloaded += len(chunk)
                    self._report_progress(downloaded, total, 0)

            self._task.downloaded_bytes = downloaded
            self._set_state(TaskState.COMPLETED)

        except Exception as e:
            self._report_error(str(e))
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_bbox.py -v
```

- [ ] **Step 5: 提交**

```bash
git add src/osm_tool/core/downloader/bbox.py tests/test_bbox.py
git commit -m "feat: add BBox downloader with area limit check"
```

---

### Task 8: QThread 下载工作线程

**Files:**
- Create: `src/osm_tool/workers/__init__.py`
- Create: `src/osm_tool/workers/download_worker.py`

- [ ] **Step 1: 写实现**

```python
# src/osm_tool/workers/__init__.py
"""工作线程"""
```

```python
# src/osm_tool/workers/download_worker.py
"""下载工作线程"""
from PySide6.QtCore import QThread, Signal

from src.osm_tool.core.downloader.base import BaseDownloader
from src_osm_tool.models.task_state import TaskState


class DownloadWorker(QThread):
    """异步下载工作线程

    在 QThread 中执行下载器，通过信号汇报进度。
    """

    # 信号: (进度百分比, 速度 bytes/s, 剩余秒数)
    progress = Signal(int, float, int)
    # 信号: 下载完成 (输出文件路径)
    finished_ok = Signal(str)
    # 信号: 下载错误 (错误信息)
    error = Signal(str)
    # 信号: 状态变更
    state_changed = Signal(object)

    def __init__(self, downloader: BaseDownloader, parent=None):
        super().__init__(parent)
        self._downloader = downloader

    def run(self) -> None:
        """线程入口"""
        try:
            self._downloader.download()
            state = self._downloader.task.state
            if state == TaskState.COMPLETED:
                self.finished_ok.emit(self._downloader.task.save_path)
            elif state == TaskState.FAILED:
                self.error.emit(self._downloader.task.error_message or "下载失败")
        except Exception as e:
            self.error.emit(str(e))

    def cancel(self) -> None:
        """取消下载"""
        self._downloader.cancel()

    def pause(self) -> None:
        """暂停下载"""
        self._downloader.pause()

    def resume(self) -> None:
        """恢复下载"""
        self._downloader.resume()
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/workers/
git commit -m "feat: add QThread download worker"
```

---

### Task 9: 主窗口框架

**Files:**
- Create: `src/osm_tool/ui/__init__.py`
- Create: `src/osm_tool/ui/widgets/__init__.py`
- Create: `src/osm_tool/ui/dialogs/__init__.py`
- Create: `src/osm_tool/ui/panels/__init__.py`
- Create: `src/osm_tool/ui/panels/split_panel.py`
- Create: `src/osm_tool/ui/panels/process_panel.py`
- Create: `src/osm_tool/ui/panels/convert_panel.py`
- Create: `src/osm_tool/ui/panels/publish_panel.py`
- Create: `src/osm_tool/ui/main_window.py`

- [ ] **Step 1: 创建包结构**

```python
# src/osm_tool/ui/__init__.py
"""用户界面"""
```

```python
# src/osm_tool/ui/widgets/__init__.py
"""自定义组件"""
```

```python
# src/osm_tool/ui/dialogs/__init__.py
"""对话框"""
```

```python
# src/osm_tool/ui/panels/__init__.py
"""功能面板"""
```

- [ ] **Step 2: 创建占位面板**

```python
# src/osm_tool/ui/panels/split_panel.py
"""数据拆分面板（占位）"""
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SplitPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("数据拆分 - 开发中")
        label.setStyleSheet("font-size: 24px; color: #888;")
        layout.addWidget(label)
```

```python
# src/osm_tool/ui/panels/process_panel.py
"""数据处理面板（占位）"""
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ProcessPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("数据处理 - 开发中")
        label.setStyleSheet("font-size: 24px; color: #888;")
        layout.addWidget(label)
```

```python
# src/osm_tool/ui/panels/convert_panel.py
"""格式转换面板（占位）"""
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ConvertPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("格式转换 - 开发中")
        label.setStyleSheet("font-size: 24px; color: #888;")
        layout.addWidget(label)
```

```python
# src/osm_tool/ui/panels/publish_panel.py
"""矢量切片发布面板（占位）"""
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PublishPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("矢量切片发布 - 开发中")
        label.setStyleSheet("font-size: 24px; color: #888;")
        layout.addWidget(label)
```

- [ ] **Step 3: 创建主窗口**

```python
# src/osm_tool/ui/main_window.py
"""主窗口"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QTextEdit, QLabel, QToolBar,
    QStatusBar, QSplitter, QMessageBox,
)

from src.osm_tool.ui.panels.download_panel import DownloadPanel
from src.osm_tool.ui.panels.split_panel import SplitPanel
from src.osm_tool.ui.panels.process_panel import ProcessPanel
from src.osm_tool.ui.panels.convert_panel import ConvertPanel
from src.osm_tool.ui.panels.publish_panel import PublishPanel
from src.osm_tool.utils.logger import setup_logger

logger = setup_logger("osm_tool.ui")


class MainWindow(QMainWindow):
    """应用主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OSM Data Toolbox")
        self.setMinimumSize(1200, 800)
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()

    def _setup_ui(self) -> None:
        """搭建 UI 布局"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # 工作区：左侧面板选择 + 右侧内容
        splitter = QSplitter(Qt.Horizontal)

        # 面板堆栈
        self._stack = QStackedWidget()
        self._panels = {
            "download": DownloadPanel(),
            "split": SplitPanel(),
            "process": ProcessPanel(),
            "convert": ConvertPanel(),
            "publish": PublishPanel(),
        }
        for panel in self._panels.values():
            self._stack.addWidget(panel)

        # 日志面板
        self._log_panel = QTextEdit()
        self._log_panel.setReadOnly(True)
        self._log_panel.setMaximumHeight(150)

        # 右侧垂直分割：工作区 + 日志
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.addWidget(self._stack)
        right_splitter.addWidget(self._log_panel)
        right_splitter.setStretchFactor(0, 4)
        right_splitter.setStretchFactor(1, 1)

        splitter.addWidget(right_splitter)
        main_layout.addWidget(splitter)

        # 默认显示下载面板
        self.switch_panel("download")

    def _setup_menu(self) -> None:
        """搭建菜单栏"""
        menu_bar = self.menuBar()

        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self) -> None:
        """搭建工具栏"""
        toolbar = QToolBar("功能切换")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        buttons = [
            ("下载数据", "download"),
            ("数据拆分", "split"),
            ("数据处理", "process"),
            ("格式转换", "convert"),
            ("矢量切片", "publish"),
        ]
        self._toolbar_buttons = {}
        for label, key in buttons:
            btn = toolbar.addAction(label)
            btn.triggered.connect(lambda checked, k=key: self.switch_panel(k))
            self._toolbar_buttons[key] = btn

    def _setup_statusbar(self) -> None:
        """搭建状态栏"""
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("就绪")

    def switch_panel(self, name: str) -> None:
        """切换功能面板"""
        if name in self._panels:
            self._stack.setCurrentWidget(self._panels[name])
            self._statusbar.showMessage(f"当前: {self._panels[name].objectName() or name}")
            logger.info(f"切换到面板: {name}")

    def log_message(self, msg: str, level: str = "info") -> None:
        """在日志面板追加消息"""
        color = {"info": "#333", "warning": "#c90", "error": "#c00"}.get(level, "#333")
        self._log_panel.append(f'<span style="color:{color}">{msg}</span>')

    def _show_about(self) -> None:
        QMessageBox.about(self, "关于", "OSM Data Toolbox v0.1.0\nOSM 数据下载、处理、转换、发布工具")
```

- [ ] **Step 4: 提交**

```bash
git add src/osm_tool/ui/
git commit -m "feat: add main window framework with placeholder panels"
```

---

### Task 10: 下载面板

**Files:**
- Create: `src/osm_tool/ui/panels/download_panel.py`

- [ ] **Step 1: 写实现**

```python
# src/osm_tool/ui/panels/download_panel.py
"""下载面板"""
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QLabel, QPushButton,
    QLineEdit, QFileDialog, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QDoubleSpinBox,
    QPlainTextEdit, QComboBox, QGroupBox, QFormLayout,
    QMessageBox,
)

from src.osm_tool.models.download_task import DownloadTask
from src_osm_tool.models.task_state import TaskState


class DownloadPanel(QWidget):
    """下载功能面板"""

    # 信号
    download_requested = Signal(object)  # DownloadTask

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("下载数据")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 标签页切换数据源
        self._tabs = QTabWidget()
        self._tabs.addTab(self._create_geofabrik_tab(), "Geofabrik")
        self._tabs.addTab(self._create_overpass_tab(), "Overpass API")
        self._tabs.addTab(self._create_bbox_tab(), "BBox 下载")
        layout.addWidget(self._tabs)

        # 下载列表
        list_group = QGroupBox("下载队列")
        list_layout = QVBoxLayout(list_group)
        self._download_table = QTableWidget(0, 5)
        self._download_table.setHorizontalHeaderLabels(["文件", "大小", "进度", "状态", "操作"])
        self._download_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        list_layout.addWidget(self._download_table)
        layout.addWidget(list_group)

    def _create_geofabrik_tab(self) -> QWidget:
        """创建 Geofabrik 标签页"""
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # 左侧：区域树
        tree_group = QGroupBox("区域选择")
        tree_layout = QVBoxLayout(tree_group)
        self._region_tree = QTreeWidget()
        self._region_tree.setHeaderLabels(["区域", "大小"])
        self._region_tree.itemClicked.connect(self._on_region_selected)
        tree_layout.addWidget(self._region_tree)

        # 刷新按钮
        refresh_btn = QPushButton("刷新区域列表")
        tree_layout.addWidget(refresh_btn)
        layout.addWidget(tree_group, stretch=1)

        # 右侧：区域信息 + 下载
        info_group = QGroupBox("区域信息")
        info_layout = QFormLayout(info_group)
        self._region_name_label = QLabel("请选择区域")
        self._region_size_label = QLabel("-")
        self._region_url_label = QLabel("-")
        info_layout.addRow("区域:", self._region_name_label)
        info_layout.addRow("大小:", self._region_size_label)
        info_layout.addRow("URL:", self._region_url_label)

        # 输出路径
        path_layout = QHBoxLayout()
        self._geofabrik_path = QLineEdit()
        path_btn = QPushButton("浏览...")
        path_btn.clicked.connect(lambda: self._browse_output(self._geofabrik_path, "pbf"))
        path_layout.addWidget(self._geofabrik_path)
        path_layout.addWidget(path_btn)
        info_layout.addRow("保存到:", path_layout)

        # 下载按钮
        self._geofabrik_download_btn = QPushButton("下载")
        self._geofabrik_download_btn.setEnabled(False)
        self._geofabrik_download_btn.clicked.connect(self._on_geofabrik_download)
        info_layout.addRow(self._geofabrik_download_btn)

        layout.addWidget(info_group, stretch=1)
        return widget

    def _create_overpass_tab(self) -> QWidget:
        """创建 Overpass 标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # QL 编辑器
        query_group = QGroupBox("Overpass QL 查询")
        query_layout = QVBoxLayout(query_group)
        self._overpass_query = QPlainTextEdit()
        self._overpass_query.setPlaceholderText(
            '[out:json];\nway(around:100,39.9,116.4)["highway"];\nout body;\n>;out skel qt;'
        )
        query_layout.addWidget(self._overpass_query)

        # 输出格式
        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel("输出格式:"))
        self._overpass_format = QComboBox()
        self._overpass_format.addItems(["JSON", "XML"])
        fmt_layout.addWidget(self._overpass_format)
        fmt_layout.addStretch()
        query_layout.addLayout(fmt_layout)
        layout.addWidget(query_group)

        # 输出路径 + 下载
        path_layout = QHBoxLayout()
        self._overpass_path = QLineEdit()
        path_btn = QPushButton("浏览...")
        path_btn.clicked.connect(lambda: self._browse_output(self._overpass_path, "json"))
        path_layout.addWidget(self._overpass_path)
        path_layout.addWidget(path_btn)
        layout.addLayout(path_layout)

        download_btn = QPushButton("执行查询并下载")
        download_btn.clicked.connect(self._on_overpass_download)
        layout.addWidget(download_btn)
        return widget

    def _create_bbox_tab(self) -> QWidget:
        """创建 BBox 标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 经纬度输入
        coord_group = QGroupBox("经纬度范围")
        coord_layout = QFormLayout(coord_group)
        self._bbox_left = QDoubleSpinBox()
        self._bbox_left.setRange(-180, 180)
        self._bbox_left.setDecimals(6)
        self._bbox_left.setValue(116.3)
        self._bbox_bottom = QDoubleSpinBox()
        self._bbox_bottom.setRange(-90, 90)
        self._bbox_bottom.setDecimals(6)
        self._bbox_bottom.setValue(39.8)
        self._bbox_right = QDoubleSpinBox()
        self._bbox_right.setRange(-180, 180)
        self._bbox_right.setDecimals(6)
        self._bbox_right.setValue(116.5)
        self._bbox_top = QDoubleSpinBox()
        self._bbox_top.setRange(-90, 90)
        self._bbox_top.setDecimals(6)
        self._bbox_top.setValue(40.0)
        coord_layout.addRow("左 (经度):", self._bbox_left)
        coord_layout.addRow("下 (纬度):", self._bbox_bottom)
        coord_layout.addRow("右 (经度):", self._bbox_right)
        coord_layout.addRow("上 (纬度):", self._bbox_top)

        area_label = QLabel(f"面积: {(116.5-116.3)*(40.0-39.8):.4f}°² (限制 0.25°²)")
        coord_layout.addRow(area_label)
        layout.addWidget(coord_group)

        # 输出路径 + 下载
        path_layout = QHBoxLayout()
        self._bbox_path = QLineEdit()
        path_btn = QPushButton("浏览...")
        path_btn.clicked.connect(lambda: self._browse_output(self._bbox_path, "osm"))
        path_layout.addWidget(self._bbox_path)
        path_layout.addWidget(path_btn)
        layout.addLayout(path_layout)

        download_btn = QPushButton("下载")
        download_btn.clicked.connect(self._on_bbox_download)
        layout.addWidget(download_btn)
        return widget

    def _browse_output(self, line_edit: QLineEdit, ext: str) -> None:
        """浏览输出路径"""
        path, _ = QFileDialog.getSaveFileName(self, "选择保存路径", "", f"文件 (*.{ext})")
        if path:
            line_edit.setText(path)

    def _on_region_selected(self, item: QTreeWidgetItem, column: int) -> None:
        """区域选中"""
        self._region_name_label.setText(item.text(0))
        self._region_size_label.setText(item.text(1))
        self._geofabrik_download_btn.setEnabled(True)

    def _on_geofabrik_download(self) -> None:
        """Geofabrik 下载"""
        if not self._geofabrik_path.text():
            QMessageBox.warning(self, "提示", "请选择保存路径")
            return
        # 后续由 MainWindow 连接信号处理
        self._add_download_entry("Geofabrik 下载", "等待中")

    def _on_overpass_download(self) -> None:
        """Overpass 下载"""
        if not self._overpass_query.toPlainText().strip():
            QMessageBox.warning(self, "提示", "请输入 Overpass QL 查询")
            return
        if not self._overpass_path.text():
            QMessageBox.warning(self, "提示", "请选择保存路径")
            return
        self._add_download_entry("Overpass 查询", "等待中")

    def _on_bbox_download(self) -> None:
        """BBox 下载"""
        if not self._bbox_path.text():
            QMessageBox.warning(self, "提示", "请选择保存路径")
            return
        area = (self._bbox_right.value() - self._bbox_left.value()) * (self._bbox_top.value() - self._bbox_bottom.value())
        if area > 0.25:
            QMessageBox.warning(self, "提示", f"面积 ({area:.2f}°²) 超过 OSM API 限制 (0.25°²)")
            return
        self._add_download_entry("BBox 下载", "等待中")

    def _add_download_entry(self, name: str, status: str) -> None:
        """添加下载条目到列表"""
        row = self._download_table.rowCount()
        self._download_table.insertRow(row)
        self._download_table.setItem(row, 0, QTableWidgetItem(name))
        self._download_table.setItem(row, 1, QTableWidgetItem("-"))
        self._download_table.setItem(row, 2, QTableWidgetItem("0%"))
        self._download_table.setItem(row, 3, QTableWidgetItem(status))
        self._download_table.setItem(row, 4, QTableWidgetItem("取消"))

    def update_download_progress(self, row: int, percent: int, speed: float) -> None:
        """更新下载进度"""
        if 0 <= row < self._download_table.rowCount():
            self._download_table.item(row, 2).setText(f"{percent}%")
            self._download_table.item(row, 3).setText(f"{speed / 1024 / 1024:.1f} MB/s")
```

- [ ] **Step 2: 提交**

```bash
git add src/osm_tool/ui/panels/download_panel.py
git commit -m "feat: add download panel with Geofabrik/Overpass/BBox tabs"
```

---

### Task 11: 应用入口

**Files:**
- Create: `src/osm_tool/app.py`
- Create: `src/osm_tool/main.py`

- [ ] **Step 1: 写实现**

```python
# src/osm_tool/app.py
"""应用配置"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.osm_tool.ui.main_window import MainWindow
from src.osm_tool.utils.logger import setup_logger


class OSMToolApp(QApplication):
    """OSM Data Toolbox 应用"""

    def __init__(self, argv=None):
        super().__init__(argv or [])
        self.setApplicationName("OSM Data Toolbox")
        self.setApplicationVersion("0.1.0")

        # 日志
        log_path = Path.home() / ".osm_tool" / "app.log"
        self._logger = setup_logger("osm_tool", log_file=log_path)
        self._logger.info("应用启动")

        # 主窗口
        self._main_window = MainWindow()
        self._main_window.show()

    @property
    def main_window(self) -> MainWindow:
        return self._main_window
```

```python
# src/osm_tool/main.py
"""应用入口"""
import sys

from src.osm_tool.app import OSMToolApp


def main():
    """启动应用"""
    app = OSMToolApp(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证应用可启动**

```bash
uv run python -c "from src.osm_tool.main import main; print('导入成功')"
```

Expected: `导入成功`

- [ ] **Step 3: 提交**

```bash
git add src/osm_tool/app.py src/osm_tool/main.py
git commit -m "feat: add application entry point"
```

---

### Task 12: 最终验证

- [ ] **运行全部测试**

```bash
uv run pytest tests/ -v
```

Expected: 全部通过

- [ ] **安装项目依赖**

```bash
uv sync
```

- [ ] **最终提交**

```bash
git add -A
git commit -m "chore: finalize Phase 1 - foundation and download module"
```
