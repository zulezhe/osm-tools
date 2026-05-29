"""数据提取功能测试"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def sample_geojson(tmp_dir):
    """创建示例 GeoJSON 文件"""
    data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [116.4, 39.9]},
                "properties": {"highway": "primary", "name": "长安街", "lanes": "4", "maxspeed": "60"},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [116.3, 39.8]},
                "properties": {"highway": "secondary", "name": "复兴路", "lanes": "2"},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [116.5, 40.0]},
                "properties": {"building": "yes", "name": "某建筑", "building:levels": "3"},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [116.6, 40.1]},
                "properties": {"highway": "primary", "name": "建国路", "maxspeed": "80"},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [116.2, 39.7]},
                "properties": {"amenity": "restaurant", "name": "测试餐厅", "cuisine": "chinese"},
            },
        ],
    }
    path = tmp_dir / "test.geojson"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(path)


@pytest.fixture
def sample_osm(tmp_dir):
    """创建示例 OSM XML 文件"""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
  <node id="1" lat="39.9" lon="116.4">
    <tag k="highway" v="primary"/>
    <tag k="name" v="长安街"/>
  </node>
  <node id="2" lat="39.8" lon="116.3">
    <tag k="highway" v="secondary"/>
    <tag k="name" v="复兴路"/>
  </node>
  <node id="3" lat="40.0" lon="116.5">
    <tag k="building" v="yes"/>
  </node>
</osm>"""
    path = tmp_dir / "test.osm"
    path.write_text(xml, encoding="utf-8")
    return str(path)


class TestScanFields:
    """字段扫描测试"""

    def test_scan_geojson(self, sample_geojson):
        from osm_tool.core.extractor.extractor import scan_fields
        fields = scan_fields(sample_geojson)

        assert len(fields) > 0
        # 检查字段结构
        f = next(f for f in fields if f["key"] == "highway")
        assert f["count"] == 3  # primary, secondary, primary
        assert f["label"] == "道路类型"
        assert "desc" in f
        assert len(f["sample_values"]) > 0
        assert f["element_types"]  # 应该有 geometry 类型

    def test_scan_geojson_field_counts(self, sample_geojson):
        from osm_tool.core.extractor.extractor import scan_fields
        fields = scan_fields(sample_geojson)

        field_map = {f["key"]: f for f in fields}
        assert field_map["name"]["count"] == 5
        assert field_map["highway"]["count"] == 3
        assert field_map["building"]["count"] == 1
        assert field_map["amenity"]["count"] == 1

    def test_scan_geojson_sample_values(self, sample_geojson):
        from osm_tool.core.extractor.extractor import scan_fields
        fields = scan_fields(sample_geojson)

        highway = next(f for f in fields if f["key"] == "highway")
        values = {sv["value"] for sv in highway["sample_values"]}
        assert "primary" in values
        assert "secondary" in values

    def test_scan_osm_xml(self, sample_osm):
        from osm_tool.core.extractor.extractor import scan_fields
        fields = scan_fields(sample_osm)

        assert len(fields) > 0
        field_map = {f["key"]: f for f in fields}
        assert "highway" in field_map
        assert field_map["highway"]["count"] == 2
        assert field_map["highway"]["label"] == "道路类型"

    def test_scan_file_not_found(self):
        from osm_tool.core.extractor.extractor import scan_fields
        with pytest.raises(FileNotFoundError):
            scan_fields("/nonexistent/file.geojson")

    def test_scan_unsupported_format(self, tmp_dir):
        from osm_tool.core.extractor.extractor import scan_fields
        path = tmp_dir / "test.csv"
        path.write_text("a,b,c", encoding="utf-8")
        with pytest.raises(ValueError, match="不支持的文件格式"):
            scan_fields(str(path))


class TestExtract:
    """数据提取测试"""

    def test_extract_by_highway(self, sample_geojson, tmp_dir):
        from osm_tool.core.extractor.extractor import extract
        output = str(tmp_dir / "output.geojson")
        result = extract(sample_geojson, [
            {"key": "highway", "values": ["primary"]}
        ], output)

        assert result["total"] == 5
        assert result["extracted"] == 2  # 长安街 + 建国路
        assert Path(output).exists()

        data = json.loads(Path(output).read_text(encoding="utf-8"))
        assert len(data["features"]) == 2
        for feat in data["features"]:
            assert feat["properties"]["highway"] == "primary"

    def test_extract_by_building(self, sample_geojson, tmp_dir):
        from osm_tool.core.extractor.extractor import extract
        output = str(tmp_dir / "output.geojson")
        result = extract(sample_geojson, [
            {"key": "building", "values": []}  # 只要有 building 字段
        ], output)

        assert result["extracted"] == 1
        data = json.loads(Path(output).read_text(encoding="utf-8"))
        assert data["features"][0]["properties"]["building"] == "yes"

    def test_extract_multiple_filters(self, sample_geojson, tmp_dir):
        """多字段 AND 条件过滤"""
        from osm_tool.core.extractor.extractor import extract
        output = str(tmp_dir / "output.geojson")
        result = extract(sample_geojson, [
            {"key": "highway", "values": ["primary"]},
            {"key": "maxspeed", "values": ["60"]},
        ], output)

        assert result["extracted"] == 1  # 只有长安街

    def test_extract_osm_xml(self, sample_osm, tmp_dir):
        from osm_tool.core.extractor.extractor import extract
        output = str(tmp_dir / "output.geojson")
        result = extract(sample_osm, [
            {"key": "highway", "values": ["primary"]}
        ], output)

        assert result["total"] == 3
        assert result["extracted"] == 1
        data = json.loads(Path(output).read_text(encoding="utf-8"))
        assert data["features"][0]["properties"]["name"] == "长安街"

    def test_extract_no_match(self, sample_geojson, tmp_dir):
        from osm_tool.core.extractor.extractor import extract
        output = str(tmp_dir / "output.geojson")
        result = extract(sample_geojson, [
            {"key": "highway", "values": ["motorway"]}
        ], output)

        assert result["extracted"] == 0
        data = json.loads(Path(output).read_text(encoding="utf-8"))
        assert len(data["features"]) == 0

    def test_extract_output_has_metadata(self, sample_geojson, tmp_dir):
        from osm_tool.core.extractor.extractor import extract
        output = str(tmp_dir / "output.geojson")
        result = extract(sample_geojson, [
            {"key": "amenity", "values": []}
        ], output)

        data = json.loads(Path(output).read_text(encoding="utf-8"))
        assert "metadata" in data
        assert data["metadata"]["total"] == 5
        assert data["metadata"]["extracted"] == 1


class TestTagDictionary:
    """标签字典测试"""

    def test_known_tag(self):
        from osm_tool.core.extractor.tag_dictionary import get_tag_info
        info = get_tag_info("highway")
        assert info["label"] == "道路类型"
        assert "primary" in info["values"]

    def test_unknown_tag(self):
        from osm_tool.core.extractor.tag_dictionary import get_tag_info
        info = get_tag_info("custom_unknown_tag")
        assert info["label"] == "custom_unknown_tag"
        assert info["desc"] == "未知标签"

    def test_search_tags(self):
        from osm_tool.core.extractor.tag_dictionary import search_tags
        results = search_tags("道路")
        assert len(results) > 0
        assert any(r["key"] == "highway" for r in results)

    def test_search_english(self):
        from osm_tool.core.extractor.tag_dictionary import search_tags
        results = search_tags("building")
        assert len(results) > 0
        assert any(r["key"] == "building" for r in results)


class TestExtractAPI:
    """API 路由测试"""

    def test_scan_api(self, sample_geojson):
        from osm_tool.app import create_app
        client = TestClient(create_app())
        resp = client.post("/api/v1/extract/scan", json={"file_path": sample_geojson})
        data = resp.json()
        assert data["code"] == 0
        assert len(data["data"]) > 0
        highway = next(f for f in data["data"] if f["key"] == "highway")
        assert highway["count"] == 3

    def test_extract_api(self, sample_geojson, tmp_dir):
        from osm_tool.app import create_app
        from osm_tool.api.task_manager import task_manager
        task_manager._tasks.clear()
        try:
            client = TestClient(create_app())
            output = str(tmp_dir / "api_output.geojson")
            resp = client.post("/api/v1/extract/start", json={
                "file_path": sample_geojson,
                "output_path": output,
                "filters": [{"key": "highway", "values": ["primary"]}],
            })
            data = resp.json()
            assert data["code"] == 0
            assert "task_id" in data["data"]
        finally:
            task_manager._tasks.clear()

    def test_tag_dictionary_api(self):
        from osm_tool.app import create_app
        client = TestClient(create_app())
        resp = client.post("/api/v1/extract/tag-dictionary", json={"query": "道路"})
        data = resp.json()
        assert data["code"] == 0
        assert len(data["data"]) > 0

    def test_scan_missing_path(self):
        from osm_tool.app import create_app
        client = TestClient(create_app())
        resp = client.post("/api/v1/extract/scan", json={})
        assert resp.json()["code"] == 1


class TestOverpassJsonConversion:
    """Overpass JSON 转换测试"""

    def test_overpass_to_geojson(self, tmp_dir):
        from osm_tool.core.extractor.extractor import scan_fields, extract
        overpass_data = {
            "version": 0.6,
            "elements": [
                {"type": "node", "id": 1, "lat": 39.9, "lon": 116.4, "tags": {"highway": "primary", "name": "测试路"}},
                {"type": "node", "id": 2, "lat": 39.8, "lon": 116.3, "tags": {"highway": "secondary"}},
                {"type": "way", "id": 3, "tags": {"building": "yes"}, "geometry": [
                    {"lat": 39.9, "lon": 116.4}, {"lat": 39.91, "lon": 116.41},
                    {"lat": 39.91, "lon": 116.4}, {"lat": 39.9, "lon": 116.4},
                ]},
            ],
        }
        path = tmp_dir / "overpass.json"
        path.write_text(json.dumps(overpass_data), encoding="utf-8")

        # 扫描
        fields = scan_fields(str(path))
        assert len(fields) >= 2
        field_map = {f["key"]: f for f in fields}
        assert "highway" in field_map
        assert "building" in field_map

        # 提取
        output = str(tmp_dir / "out.geojson")
        result = extract(str(path), [{"key": "highway", "values": []}], output)
        assert result["extracted"] == 2
