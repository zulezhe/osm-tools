"""数据拆分测试"""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from osm_tool.core.splitter.admin_boundaries import AdminBoundaryManager, RegionInfo


def test_region_info():
    """测试区域信息"""
    r = RegionInfo(code="110000", name="北京市", geojson_path="/tmp/bj.json", parent_code="")
    assert r.code == "110000"
    assert r.name == "北京市"


def test_admin_boundary_manager_load(tmp_dir):
    """测试加载省份数据"""
    provinces_file = tmp_dir / "provinces.json"
    provinces_file.write_text(json.dumps({
        "features": [{"properties": {"adcode": 110000, "name": "北京市"}}]
    }), encoding="utf-8")

    mgr = AdminBoundaryManager(data_dir=str(tmp_dir))
    regions = mgr.load_provinces()
    assert len(regions) == 1
    assert regions[0].name == "北京市"


def test_admin_splitter(tmp_dir):
    """测试行政区拆分（mock osmium）"""
    from osm_tool.core.splitter.admin_splitter import AdminSplitter

    input_pbf = tmp_dir / "input.osm.pbf"
    input_pbf.write_bytes(b"fake pbf")

    boundary_geojson = tmp_dir / "boundary.json"
    boundary_geojson.write_text(json.dumps({
        "type": "Polygon",
        "coordinates": [[[116.0, 39.0], [117.0, 39.0], [117.0, 40.0], [116.0, 40.0], [116.0, 39.0]]]
    }), encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        # 模拟输出文件
        output_dir = tmp_dir / "output"
        output_dir.mkdir()
        (output_dir / "beijing.osm.pbf").write_bytes(b"output")

        splitter = AdminSplitter()
        result = splitter.split_by_region(
            str(input_pbf),
            str(output_dir),
            str(boundary_geojson),
            "beijing",
        )

    assert result.endswith("beijing.osm.pbf")


def test_range_splitter_bbox(tmp_dir):
    """测试范围拆分器（bbox 模式，mock osmium）"""
    from osm_tool.core.splitter.range_splitter import RangeSplitter

    input_pbf = tmp_dir / "input.osm.pbf"
    input_pbf.write_bytes(b"fake pbf")

    output_dir = tmp_dir / "output"
    output_dir.mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        (output_dir / "clipped.osm.pbf").write_bytes(b"output")

        splitter = RangeSplitter()
        result = splitter.split(str(input_pbf), str(output_dir), {
            "bbox": [116.0, 39.0, 117.0, 40.0],
        })

    assert len(result) == 1


def test_attribute_splitter(tmp_dir):
    """测试属性拆分器"""
    from osm_tool.core.splitter.attribute_splitter import AttributeSplitter

    input_geojson = tmp_dir / "input.geojson"
    input_geojson.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"highway": "primary", "name": "road1"}, "geometry": None},
            {"type": "Feature", "properties": {"building": "yes", "name": "bldg1"}, "geometry": None},
            {"type": "Feature", "properties": {"highway": "secondary"}, "geometry": None},
        ]
    }), encoding="utf-8")

    output_dir = tmp_dir / "output"
    output_dir.mkdir()

    splitter = AttributeSplitter()
    result = splitter.split(str(input_geojson), str(output_dir), {
        "conditions": [{"key": "highway", "match": "exists"}],
        "logic": "or",
        "output_name": "roads",
    })

    assert len(result) == 1
    data = json.loads(Path(result[0]).read_text(encoding="utf-8"))
    assert len(data["features"]) == 2


def test_type_splitter_element_type(tmp_dir):
    """测试类型拆分器（按几何类型）"""
    from osm_tool.core.splitter.type_splitter import TypeSplitter

    input_geojson = tmp_dir / "input.geojson"
    input_geojson.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [0, 0]}},
            {"type": "Feature", "properties": {}, "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}},
        ]
    }), encoding="utf-8")

    output_dir = tmp_dir / "output"
    output_dir.mkdir()

    splitter = TypeSplitter()
    result = splitter.split(str(input_geojson), str(output_dir), {"mode": "element_type"})

    assert len(result) == 2
    names = [Path(p).stem for p in result]
    assert "point" in names
    assert "linestring" in names


def test_type_splitter_tag_group(tmp_dir):
    """测试类型拆分器（按标签分组）"""
    from osm_tool.core.splitter.type_splitter import TypeSplitter

    input_geojson = tmp_dir / "input.geojson"
    input_geojson.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"highway": "primary"}, "geometry": None},
            {"type": "Feature", "properties": {"building": "yes"}, "geometry": None},
            {"type": "Feature", "properties": {"amenity": "cafe"}, "geometry": None},
        ]
    }), encoding="utf-8")

    output_dir = tmp_dir / "output"
    output_dir.mkdir()

    splitter = TypeSplitter()
    result = splitter.split(str(input_geojson), str(output_dir), {
        "mode": "tag_group",
        "tag_groups": ["highway", "building"],
    })

    assert len(result) == 3  # highway, building, other
    names = [Path(p).stem for p in result]
    assert "highway" in names
    assert "building" in names
    assert "other" in names
