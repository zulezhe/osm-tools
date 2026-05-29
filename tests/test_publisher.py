"""矢量切片发布测试"""
from unittest.mock import patch, MagicMock
from pathlib import Path

from osm_tool.core.publisher.base import TileConfig, OutputFormat
from osm_tool.core.publisher.tippecanoe_publisher import TippecanoePublisher


def test_tippecanoe_build_command_mbtiles():
    """测试 MBTiles 命令构建"""
    publisher = TippecanoePublisher()
    config = TileConfig(minzoom=5, maxzoom=12, output_format=OutputFormat.MBTILES)
    cmd = publisher._build_command("input.geojson", "output.mbtiles", config)
    assert "-z" in cmd
    assert "12" in cmd
    assert "-o" in cmd
    assert "output.mbtiles" in cmd


def test_tippecanoe_build_command_mvt_dir():
    """测试 MVT 目录命令构建"""
    publisher = TippecanoePublisher()
    config = TileConfig(minzoom=0, maxzoom=14, output_format=OutputFormat.MVT_DIRECTORY)
    cmd = publisher._build_command("input.geojson", "output_dir", config)
    assert "-e" in cmd
    assert "output_dir" in cmd


def test_tippecanoe_publish_success(tmp_dir):
    """测试发布成功"""
    publisher = TippecanoePublisher()
    config = TileConfig(output_format=OutputFormat.MBTILES)
    output_path = str(tmp_dir / "output.mbtiles")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="1000 tiles")
        Path(output_path).write_bytes(b"fake mbtiles")

        result = publisher.publish(str(tmp_dir / "input.geojson"), output_path, config)

    assert result.success


def test_tippecanoe_publish_failure(tmp_dir):
    """测试发布失败"""
    publisher = TippecanoePublisher()
    config = TileConfig(output_format=OutputFormat.MBTILES)
    output_path = str(tmp_dir / "output.mbtiles")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="error: bad input")

        result = publisher.publish(str(tmp_dir / "input.geojson"), output_path, config)

    assert not result.success
    assert "error" in result.error_message


def test_planetiler_build_command():
    """测试 Planetiler 命令构建"""
    from osm_tool.core.publisher.planetiler_publisher import PlanetilerPublisher
    publisher = PlanetilerPublisher(jar_path="/opt/planetiler.jar")
    config = TileConfig(minzoom=0, maxzoom=10)
    cmd = publisher._build_command("input.pbf", "output.mbtiles", config)
    assert "java" in cmd
    assert "/opt/planetiler.jar" in cmd
    assert "--mbtiles=0,10" in cmd


def test_publish_manager_no_tool(tmp_dir):
    """测试无可用工具时抛出异常"""
    from osm_tool.core.publisher.manager import PublishManager
    mgr = PublishManager()

    with patch("shutil.which", return_value=None):
        try:
            mgr.get_publisher()
            assert False, "应该抛出异常"
        except RuntimeError as e:
            assert "未找到" in str(e)
