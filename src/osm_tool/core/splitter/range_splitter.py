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
        admin = AdminSplitter(on_progress=self._on_progress, on_error=self._on_error)
        return admin.split_by_region(input_path, str(Path(output_path).parent), geojson_path, Path(output_path).stem)
