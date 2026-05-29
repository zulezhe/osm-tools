"""坐标抽稀处理器"""
from osm_tool.core.processor.base import ProcessingStep


class DouglasPeuckerSimplifier(ProcessingStep):
    """Douglas-Peucker 抽稀"""
    name = "simplify_dp"

    def __init__(self, tolerance: float = 1.0):
        self._tolerance = tolerance

    def simplify(self, geometry):
        from shapely.geometry import shape
        geom = shape(geometry) if isinstance(geometry, dict) else geometry
        return geom.simplify(self._tolerance)

    def process_feature(self, feature: dict) -> dict:
        from shapely.geometry import shape, mapping
        geom = feature.get("geometry")
        if geom is None or geom.get("type") == "Point":
            return feature
        simplified = self.simplify(geom)
        feature["geometry"] = mapping(simplified)
        return feature


class VisvalingamSimplifier(ProcessingStep):
    """Visvalingam-Whyatt 抽稀"""
    name = "simplify_vw"

    def __init__(self, min_area: float = 1.0):
        self._min_area = min_area

    def simplify(self, geometry):
        from shapely.geometry import shape
        geom = shape(geometry) if isinstance(geometry, dict) else geometry
        tolerance = max(0.1, self._min_area ** 0.5)
        return geom.simplify(tolerance, preserve_topology=True)

    def process_feature(self, feature: dict) -> dict:
        from shapely.geometry import shape, mapping
        geom = feature.get("geometry")
        if geom is None or geom.get("type") == "Point":
            return feature
        simplified = self.simplify(geom)
        feature["geometry"] = mapping(simplified)
        return feature


class FixedIntervalSimplifier(ProcessingStep):
    """固定间距抽稀"""
    name = "simplify_interval"

    def __init__(self, interval_meters: float = 10.0):
        self._interval = interval_meters

    def process_feature(self, feature: dict) -> dict:
        geom = feature.get("geometry")
        if geom is None or geom.get("type") == "Point":
            return feature

        coords = geom.get("coordinates", [])
        gtype = geom.get("type", "")

        if gtype in ("LineString", "MultiPoint"):
            geom["coordinates"] = self._thin_coords(coords)
        elif gtype in ("Polygon", "MultiLineString"):
            geom["coordinates"] = [self._thin_coords(ring) for ring in coords]
        elif gtype == "MultiPolygon":
            geom["coordinates"] = [[[self._thin_coords(ring) for c in ring] for ring in poly] for poly in coords]
        return feature

    def _thin_coords(self, coords: list) -> list:
        if len(coords) <= 2:
            return coords
        result = [coords[0]]
        accumulated = 0.0
        for i in range(1, len(coords)):
            dx = coords[i][0] - coords[i-1][0]
            dy = coords[i][1] - coords[i-1][1]
            dist = ((dx * 111000) ** 2 + (dy * 111000) ** 2) ** 0.5
            accumulated += dist
            if accumulated >= self._interval:
                result.append(coords[i])
                accumulated = 0.0
        if result[-1] != coords[-1]:
            result.append(coords[-1])
        return result
