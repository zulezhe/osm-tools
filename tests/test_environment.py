"""环境检测测试"""
from src.osm_tool.utils.environment import check_tool_available, ToolCheckResult


def test_check_tool_available_python():
    result = check_tool_available("python")
    assert isinstance(result, ToolCheckResult)
    assert result.name == "python"
    assert result.available is True
    assert result.path is not None


def test_check_tool_available_nonexistent():
    result = check_tool_available("nonexistent_tool_xyz_12345")
    assert result.available is False
