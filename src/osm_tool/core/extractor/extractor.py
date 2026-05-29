"""OSM 数据字段提取器

从 OSM 数据文件 (GeoJSON/JSON/XML) 中扫描和提取数据:
- scan_fields: 扫描文件，统计所有 tag 字段的出现次数和示例值
- extract: 根据指定字段过滤提取数据
"""
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from osm_tool.core.extractor.tag_dictionary import get_tag_info, TAG_DICTIONARY
from osm_tool.utils.logger import setup_logger

logger = setup_logger("osm_tool.extractor")


def scan_fields(file_path: str) -> list[dict]:
    """扫描 OSM 数据文件，返回所有 tag 字段统计

    Returns:
        [{key, count, label, desc, sample_values, element_types}]
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    ext = path.suffix.lower()

    if ext in (".json", ".geojson"):
        return _scan_geojson(path)
    elif ext in (".osm",):
        return _scan_osm_xml(path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}，支持: .json, .geojson, .osm")


def extract(file_path: str, filters: list[dict], output_path: str) -> dict:
    """按字段条件提取数据

    Args:
        file_path: 输入文件路径
        filters: 过滤条件列表 [{key: "highway", values: ["primary", "secondary"]}]
                 values 为空则提取包含该 key 的所有要素
        output_path: 输出文件路径
    Returns:
        {total: int, extracted: int, output: str}
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext in (".json", ".geojson"):
        return _extract_geojson(path, filters, output_path)
    elif ext in (".osm",):
        return _extract_osm_xml(path, filters, output_path)
    else:
        raise ValueError(f"不支持的格式: {ext}")


# ── GeoJSON ──

def _scan_geojson(path: Path) -> list[dict]:
    """扫描 GeoJSON 文件中的所有 properties 字段"""
    data = json.loads(path.read_text(encoding="utf-8"))

    tag_counter: Counter = Counter()
    value_counter: dict[str, Counter] = {}
    type_counter: dict[str, set] = {}  # key → 出现的 geometry 类型

    features = data.get("features", [])
    # 也处理 Overpass JSON 格式: {elements: [...]}
    if not features and "elements" in data:
        features = _overpass_elements_to_features(data["elements"])

    for feat in features:
        props = feat.get("properties", {}) or {}
        tags = feat.get("tags", {})  # 有时 tags 在顶层
        merged = {**props, **tags}

        geom_type = ""
        geom = feat.get("geometry")
        if isinstance(geom, dict):
            geom_type = geom.get("type", "")

        for key, val in merged.items():
            if key.startswith("@") or key in ("id", "type", "nodes", "members", "geometry"):
                continue
            tag_counter[key] += 1
            if key not in value_counter:
                value_counter[key] = Counter()
            val_str = str(val) if val is not None else ""
            value_counter[key][val_str] += 1
            if key not in type_counter:
                type_counter[key] = set()
            if geom_type:
                type_counter[key].add(geom_type)

    # 组装结果
    results = []
    for key, count in tag_counter.most_common():
        info = get_tag_info(key)
        top_values = value_counter[key].most_common(20)
        results.append({
            "key": key,
            "count": count,
            "label": info["label"],
            "desc": info["desc"],
            "sample_values": [{"value": v, "count": c} for v, c in top_values],
            "element_types": sorted(type_counter.get(key, set())),
        })

    return results


def _extract_geojson(path: Path, filters: list[dict], output_path: str) -> dict:
    """从 GeoJSON 提取符合条件的要素"""
    data = json.loads(path.read_text(encoding="utf-8"))

    # 构建 filter map: key → set(values)
    filter_map: dict[str, set] = {}
    for f in filters:
        key = f.get("key", "")
        vals = f.get("values", [])
        filter_map[key] = set(vals) if vals else None  # None = 接受任何值

    features = data.get("features", [])
    if not features and "elements" in data:
        features = _overpass_elements_to_features(data["elements"])

    total = len(features)
    extracted = []

    for feat in features:
        props = feat.get("properties", {}) or {}
        tags = feat.get("tags", {})
        merged = {**props, **tags}

        match = True
        for key, allowed_values in filter_map.items():
            if key not in merged:
                match = False
                break
            if allowed_values is not None and str(merged[key]) not in allowed_values:
                match = False
                break

        if match:
            extracted.append(feat)

    # 输出为 GeoJSON
    output = {
        "type": "FeatureCollection",
        "features": extracted,
        "metadata": {
            "source": str(path),
            "filters": filters,
            "total": total,
            "extracted": len(extracted),
        },
    }

    Path(output_path).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"total": total, "extracted": len(extracted), "output": output_path}


# ── OSM XML ──

def _scan_osm_xml(path: Path) -> list[dict]:
    """扫描 OSM XML 文件中的所有 tag 字段"""
    tag_counter: Counter = Counter()
    value_counter: dict[str, Counter] = {}
    type_counter: dict[str, set] = {}

    context = ET.iterparse(str(path), events=("end",))
    for event, elem in context:
        if elem.tag in ("node", "way", "relation"):
            elem_type = elem.tag
            for tag_elem in elem.findall("tag"):
                k = tag_elem.get("k", "")
                v = tag_elem.get("v", "")
                if not k:
                    continue
                tag_counter[k] += 1
                if k not in value_counter:
                    value_counter[k] = Counter()
                value_counter[k][v] += 1
                if k not in type_counter:
                    type_counter[k] = set()
                type_counter[k].add(elem_type)
            elem.clear()

    results = []
    for key, count in tag_counter.most_common():
        info = get_tag_info(key)
        top_values = value_counter[key].most_common(20)
        results.append({
            "key": key,
            "count": count,
            "label": info["label"],
            "desc": info["desc"],
            "sample_values": [{"value": v, "count": c} for v, c in top_values],
            "element_types": sorted(type_counter.get(key, set())),
        })

    return results


def _extract_osm_xml(path: Path, filters: list[dict], output_path: str) -> dict:
    """从 OSM XML 提取符合条件的要素并转为 GeoJSON"""
    filter_map: dict[str, set] = {}
    for f in filters:
        key = f.get("key", "")
        vals = f.get("values", [])
        filter_map[key] = set(vals) if vals else None

    features = []
    total = 0

    context = ET.iterparse(str(path), events=("end",))
    for event, elem in context:
        if elem.tag in ("node", "way", "relation"):
            total += 1
            tags = {t.get("k"): t.get("v") for t in elem.findall("tag")}

            match = True
            for key, allowed_values in filter_map.items():
                if key not in tags:
                    match = False
                    break
                if allowed_values is not None and tags[key] not in allowed_values:
                    match = False
                    break

            if match and elem.tag == "node":
                lat = elem.get("lat")
                lon = elem.get("lon")
                if lat and lon:
                    features.append({
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                        "properties": tags,
                    })

            elem.clear()

    output = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "source": str(path),
            "filters": filters,
            "total": total,
            "extracted": len(features),
        },
    }

    Path(output_path).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"total": total, "extracted": len(features), "output": output_path}


# ── Overpass JSON → GeoJSON 转换 ──

def _overpass_elements_to_features(elements: list) -> list[dict]:
    """将 Overpass JSON elements 转为 GeoJSON features"""
    features = []
    for elem in elements:
        etype = elem.get("type", "")
        props = {k: v for k, v in elem.items() if k not in ("type", "id", "lat", "lon", "tags", "bounds", "nodes", "geometry", "members")}
        if "tags" in elem:
            props.update(elem["tags"])
        props["id"] = elem.get("id", "")
        props["element_type"] = etype

        geom = None
        if etype == "node" and "lat" in elem and "lon" in elem:
            geom = {"type": "Point", "coordinates": [elem["lon"], elem["lat"]]}
        elif etype == "way" and "geometry" in elem:
            coords = [[p["lon"], p["lat"]] for p in elem["geometry"]]
            if coords and coords[0] == coords[-1] and len(coords) >= 4:
                geom = {"type": "Polygon", "coordinates": [coords]}
            elif coords:
                geom = {"type": "LineString", "coordinates": coords}

        if geom:
            features.append({"type": "Feature", "geometry": geom, "properties": props})

    return features
