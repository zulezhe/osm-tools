"""格式转换测试"""
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.osm_tool.core.converter.base import Format, BaseConverter
from src.osm_tool.core.converter.gdal_converter import GDALConverter
from src.osm_tool.core.converter.manager import ConversionManager


def test_detect_format():
    assert BaseConverter.detect_format("test.geojson") == Format.GEOJSON
    assert BaseConverter.detect_format("test.shp") == Format.SHAPEFILE
    assert BaseConverter.detect_format("test.gpkg") == Format.GEOPACKAGE
    assert BaseConverter.detect_format("test.osm.pbf") == Format.PBF
    assert BaseConverter.detect_format("test.xyz") is None


def test_gdal_convert_geojson_to_shp(tmp_dir):
    input_path = str(tmp_dir / "input.geojson")
    output_path = str(tmp_dir / "output.shp")
    Path(input_path).write_text('{"type":"FeatureCollection","features":[]}')

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        Path(output_path).write_text("fake")

        converter = GDALConverter()
        result = converter.convert(input_path, output_path, Format.GEOJSON, Format.SHAPEFILE)

    assert result.success
    assert result.output_format == Format.SHAPEFILE


def test_gdal_convert_failure(tmp_dir):
    input_path = str(tmp_dir / "input.geojson")
    output_path = str(tmp_dir / "output.shp")
    Path(input_path).write_text("{}")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="ERROR: bad input")

        converter = GDALConverter()
        result = converter.convert(input_path, output_path, Format.GEOJSON, Format.SHAPEFILE)

    assert not result.success
    assert "bad input" in result.error_message


def test_manager_get_converter_geojson_to_shp():
    mgr = ConversionManager()
    converter = mgr.get_converter(Format.GEOJSON, Format.SHAPEFILE)
    assert converter is not None


def test_manager_get_converter_pbf_to_geojson():
    mgr = ConversionManager()
    converter = mgr.get_converter(Format.PBF, Format.GEOJSON)
    assert converter is not None


def test_manager_get_converter_same_format():
    mgr = ConversionManager()
    converter = mgr.get_converter(Format.GEOJSON, Format.GEOJSON)
    assert converter is None
