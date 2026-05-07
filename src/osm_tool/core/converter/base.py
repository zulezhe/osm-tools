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
        full_name = Path(path).name.lower()
        if full_name.endswith(".osm.pbf"):
            return Format.PBF
        if full_name.endswith(".geojson.gz"):
            return Format.GEOJSON

        p = Path(path).suffix.lower()
        mapping = {
            ".pbf": Format.PBF,
            ".osm": Format.PBF,
            ".geojson": Format.GEOJSON,
            ".json": Format.GEOJSON,
            ".shp": Format.SHAPEFILE,
            ".gpkg": Format.GEOPACKAGE,
        }
        return mapping.get(p)
