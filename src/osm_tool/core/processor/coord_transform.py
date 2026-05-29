"""坐标转换处理器"""
import math

from osm_tool.core.processor.base import ProcessingStep

_X_PI = math.pi * 3000.0 / 180.0
_PI = math.pi
_A = 6378245.0
_EE = 0.00669342162296594323


def _out_of_china(lng: float, lat: float) -> bool:
    return not (72.004 <= lng <= 137.8347 and 0.8293 <= lat <= 55.8271)


def _transform_lat(lng: float, lat: float) -> float:
    ret = (-100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat +
           0.1 * lng * lat + 0.2 * math.sqrt(abs(lng)))
    ret += (20.0 * math.sin(6.0 * lng * _PI) + 20.0 * math.sin(2.0 * lng * _PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * _PI) + 40.0 * math.sin(lat / 3.0 * _PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * _PI) + 320 * math.sin(lat * _PI / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(lng: float, lat: float) -> float:
    ret = (300.0 + lng + 2.0 * lat + 0.1 * lng * lng +
           0.1 * lng * lat + 0.1 * math.sqrt(abs(lng)))
    ret += (20.0 * math.sin(6.0 * lng * _PI) + 20.0 * math.sin(2.0 * lng * _PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * _PI) + 40.0 * math.sin(lng / 3.0 * _PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * _PI) + 300.0 * math.sin(lng / 30.0 * _PI)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lng: float, lat: float) -> tuple[float, float]:
    if _out_of_china(lng, lat):
        return lng, lat
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * _PI
    magic = math.sin(radlat)
    magic = 1 - _EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrtmagic) * _PI)
    dlng = (dlng * 180.0) / (_A / sqrtmagic * math.cos(radlat) * _PI)
    return lng + dlng, lat + dlat


def gcj02_to_bd09(lng: float, lat: float) -> tuple[float, float]:
    z = math.sqrt(lng * lng + lat * lat) + 0.00002 * math.sin(lat * _X_PI)
    theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * _X_PI)
    return z * math.cos(theta) + 0.0065, z * math.sin(theta) + 0.006


def wgs84_to_bd09(lng: float, lat: float) -> tuple[float, float]:
    gcj_lng, gcj_lat = wgs84_to_gcj02(lng, lat)
    return gcj02_to_bd09(gcj_lng, gcj_lat)


class CoordTransform(ProcessingStep):
    """坐标转换处理步骤"""
    name = "coord_transform"

    def __init__(self, target_crs: str = "gcj02"):
        self._target_crs = target_crs

    def _transform_coord(self, lng: float, lat: float) -> tuple[float, float]:
        if self._target_crs == "gcj02":
            return wgs84_to_gcj02(lng, lat)
        elif self._target_crs == "bd09":
            return wgs84_to_bd09(lng, lat)
        else:
            from pyproj import Transformer
            transformer = Transformer.from_crs("EPSG:4326", self._target_crs, always_xy=True)
            return transformer.transform(lng, lat)

    def process_feature(self, feature: dict) -> dict:
        geom = feature.get("geometry")
        if geom is None:
            return feature
        feature["geometry"] = self._transform_geometry(geom)
        return feature

    def _transform_geometry(self, geom: dict) -> dict:
        gtype = geom.get("type", "")
        coords = geom.get("coordinates", [])

        if gtype == "Point":
            geom["coordinates"] = list(self._transform_coord(coords[0], coords[1]))
        elif gtype in ("LineString", "MultiPoint"):
            geom["coordinates"] = [list(self._transform_coord(c[0], c[1])) for c in coords]
        elif gtype in ("Polygon", "MultiLineString"):
            geom["coordinates"] = [[list(self._transform_coord(c[0], c[1])) for c in ring] for ring in coords]
        elif gtype == "MultiPolygon":
            geom["coordinates"] = [[[list(self._transform_coord(c[0], c[1])) for c in ring] for ring in poly] for poly in coords]
        return geom
