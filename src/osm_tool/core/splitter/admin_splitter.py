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
