"""数据处理测试"""
import gzip
import json
from pathlib import Path

from osm_tool.core.processor.base import ProcessingStep, ProcessingPipeline


class UpperCaseStep(ProcessingStep):
    name = "uppercase"

    def process_feature(self, feature: dict) -> dict:
        props = feature.get("properties", {})
        return {**feature, "properties": {k: v.upper() if isinstance(v, str) else v for k, v in props.items()}}


def test_pipeline_single_step(tmp_dir):
    input_geojson = tmp_dir / "input.geojson"
    output_geojson = tmp_dir / "output.geojson"
    input_geojson.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"name": "hello"}, "geometry": None}]
    }), encoding="utf-8")

    pipeline = ProcessingPipeline()
    pipeline.add_step(UpperCaseStep())
    pipeline.execute(str(input_geojson), str(output_geojson))

    result = json.loads(output_geojson.read_text(encoding="utf-8"))
    assert result["features"][0]["properties"]["name"] == "HELLO"


def test_pipeline_multi_step(tmp_dir):
    input_geojson = tmp_dir / "input.geojson"
    output_geojson = tmp_dir / "output.geojson"
    input_geojson.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"name": "hello"}, "geometry": None}]
    }), encoding="utf-8")

    pipeline = ProcessingPipeline()
    pipeline.add_step(UpperCaseStep())
    pipeline.add_step(UpperCaseStep())
    pipeline.execute(str(input_geojson), str(output_geojson))

    result = json.loads(output_geojson.read_text(encoding="utf-8"))
    assert result["features"][0]["properties"]["name"] == "HELLO"


def test_compressor_geojson_gz(tmp_dir):
    from osm_tool.core.processor.compressor import Compressor

    input_geojson = tmp_dir / "input.geojson"
    input_geojson.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")

    compressor = Compressor()
    output_path = compressor.compress_geojson(str(input_geojson), compression_level=6)

    assert Path(output_path).exists()
    content = gzip.open(output_path, "rt", encoding="utf-8").read()
    assert "FeatureCollection" in content


def test_simplifier_douglas_peucker():
    from osm_tool.core.processor.simplifier import DouglasPeuckerSimplifier
    from shapely.geometry import LineString

    line = LineString([(0, 0), (1, 0.1), (2, 0), (3, 0)])
    simplifier = DouglasPeuckerSimplifier(tolerance=0.5)
    result = simplifier.simplify(line)
    assert len(result.coords) <= len(line.coords)


def test_field_remover(tmp_dir):
    from osm_tool.core.processor.field_remover import FieldRemover

    input_geojson = tmp_dir / "input.geojson"
    output_geojson = tmp_dir / "output.geojson"
    input_geojson.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"name": "test", "source": "gps", "note": "ok"}, "geometry": None}]
    }), encoding="utf-8")

    remover = FieldRemover(fields_to_remove=["source", "note"])
    remover.execute(str(input_geojson), str(output_geojson))

    result = json.loads(output_geojson.read_text(encoding="utf-8"))
    props = result["features"][0]["properties"]
    assert "name" in props
    assert "source" not in props
    assert "note" not in props


def test_coord_transform_gcj02():
    from osm_tool.core.processor.coord_transform import wgs84_to_gcj02

    lng, lat = wgs84_to_gcj02(116.4, 39.9)
    assert lng != 116.4  # 应该有偏移
    assert lat != 39.9


def test_coord_transform_bd09():
    from osm_tool.core.processor.coord_transform import wgs84_to_bd09

    lng, lat = wgs84_to_bd09(116.4, 39.9)
    assert lng != 116.4
    assert lat != 39.9
