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
