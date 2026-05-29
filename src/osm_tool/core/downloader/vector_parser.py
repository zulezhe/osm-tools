"""矢量文件解析器，支持 GeoJSON/Shapefile/KML/GeoPackage"""
import json
import tempfile
import os
from dataclasses import dataclass
from pathlib import Path

from osm_tool.utils.logger import setup_logger

logger = setup_logger("osm_tool.vector_parser")


@dataclass
class ParsedVector:
    """解析结果"""
    bbox: dict  # {left, bottom, right, top}
    geojson: dict  # GeoJSON 几何
    area_sqkm: float  # 面积（平方公里，粗略估算）


def parse_vector_file(file_path: str, original_filename: str = "") -> ParsedVector:
    """解析矢量文件，返回边界信息。

    支持 .geojson .json .kml .gpkg .zip(shapefile)
    """
    ext = Path(original_filename or file_path).suffix.lower()

    if ext in ('.geojson', '.json'):
        return _parse_geojson(file_path)
    elif ext == '.kml':
        return _parse_kml(file_path)
    elif ext in ('.gpkg',):
        return _parse_gdal(file_path, ext)
    elif ext == '.zip':
        return _parse_gdal(file_path, ext)
    else:
        # 尝试用 GDAL 打开
        return _parse_gdal(file_path, ext)


def _parse_geojson(file_path: str) -> ParsedVector:
    """解析 GeoJSON 文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    bbox = _extract_bbox_from_geojson(data)
    geojson = _extract_geometry_from_geojson(data)
    area = _estimate_area(bbox)

    return ParsedVector(bbox=bbox, geojson=geojson, area_sqkm=area)


def _parse_kml(file_path: str) -> ParsedVector:
    """解析 KML 文件，使用 GDAL"""
    return _parse_gdal(file_path, '.kml')


def _parse_gdal(file_path: str, ext: str) -> ParsedVector:
    """使用 GDAL/OGR 解析矢量文件"""
    try:
        from osgeo import ogr
    except ImportError:
        raise RuntimeError("GDAL 未安装，无法解析此格式。请安装 GDAL。")

    ds = ogr.Open(file_path)
    if not ds:
        raise ValueError(f"无法打开文件: {file_path}")

    layer = ds.GetLayer(0)
    if not layer:
        raise ValueError("文件中没有找到图层")

    # 获取图层范围
    extent = layer.GetExtent()
    bbox = {
        "left": extent[0],
        "right": extent[1],
        "bottom": extent[2],
        "top": extent[3],
    }

    # 收集所有几何，转为 GeoJSON
    features = []
    for feat in layer:
        geom = feat.GetGeometryRef()
        if geom:
            features.append(json.loads(geom.ExportToJson()))

    if not features:
        raise ValueError("文件中没有找到有效几何")

    # 合并几何为 MultiPolygon 或直接使用第一个
    geojson = _merge_geometries(features)
    area = _estimate_area(bbox)

    ds = None  # 关闭
    return ParsedVector(bbox=bbox, geojson=geojson, area_sqkm=area)


def _extract_bbox_from_geojson(data: dict) -> dict:
    """从 GeoJSON 数据提取 bbox"""
    if "bbox" in data:
        b = data["bbox"]  # [minLng, minLat, maxLng, maxLat]
        return {"left": b[0], "bottom": b[1], "right": b[2], "top": b[3]}

    # 从 features 遍历计算
    coords = _collect_all_coords(data)
    if not coords:
        raise ValueError("GeoJSON 中没有找到坐标")

    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return {"left": min(lngs), "bottom": min(lats), "right": max(lngs), "top": max(lats)}


def _collect_all_coords(data: dict) -> list:
    """递归收集所有坐标"""
    coords = []

    if data.get("type") == "FeatureCollection":
        for feat in data.get("features", []):
            coords.extend(_collect_all_coords(feat))
    elif data.get("type") == "Feature":
        geom = data.get("geometry", {})
        coords.extend(_collect_all_coords(geom))
    elif "coordinates" in data:
        coords.extend(_flatten_coordinates(data["coordinates"]))

    return coords


def _flatten_coordinates(coords) -> list:
    """展平嵌套坐标"""
    if isinstance(coords[0], (int, float)):
        return [coords]
    result = []
    for c in coords:
        result.extend(_flatten_coordinates(c))
    return result


def _extract_geometry_from_geojson(data: dict) -> dict:
    """从 GeoJSON 提取几何"""
    if data.get("type") == "FeatureCollection":
        features = data.get("features", [])
        if len(features) == 1:
            return features[0].get("geometry", {})
        geoms = [f.get("geometry") for f in features if f.get("geometry")]
        return _merge_geometries(geoms)
    elif data.get("type") == "Feature":
        return data.get("geometry", {})
    return data


def _merge_geometries(geoms: list) -> dict:
    """合并多个几何"""
    if len(geoms) == 1:
        return geoms[0]
    return {
        "type": "GeometryCollection",
        "geometries": geoms,
    }


def _estimate_area(bbox: dict) -> float:
    """粗略估算面积（平方公里）"""
    # 1 degree 纬度 ≈ 111 km，1 degree 经度 ≈ 111 * cos(lat) km
    center_lat = (bbox["top"] + bbox["bottom"]) / 2
    lat_km = (bbox["top"] - bbox["bottom"]) * 111
    lng_km = (bbox["right"] - bbox["left"]) * 111 * abs(center_lat / 90)
    return round(lat_km * lng_km, 2)
