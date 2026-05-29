"""字段删除处理器"""
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from osm_tool.core.processor.base import ProcessingStep

OSM_METADATA_FIELDS = ["source", "created_by", "note", "fixme", "source_ref", "source:url"]


@dataclass
class FieldInfo:
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
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
        features = data.get("features", [])
        if not features:
            return []

        all_keys: set[str] = set()
        for feat in features:
            all_keys.update(feat.get("properties", {}).keys())

        result = []
        for key in sorted(all_keys):
            values = []
            for feat in features:
                v = feat.get("properties", {}).get(key)
                if v is not None:
                    values.append(v)
            counter = Counter(values)
            result.append(FieldInfo(
                name=key, non_null_count=len(values),
                unique_count=len(counter), sample_values=values[:5],
            ))
        return result
