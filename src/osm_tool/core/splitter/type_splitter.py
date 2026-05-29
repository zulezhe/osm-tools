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
