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
