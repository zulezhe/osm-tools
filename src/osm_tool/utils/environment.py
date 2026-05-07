"""外部工具环境检测"""
import shutil
from dataclasses import dataclass


@dataclass
class ToolCheckResult:
    """工具检测结果"""
    name: str
    available: bool
    path: str | None = None
    version: str | None = None


def check_tool_available(tool_name: str) -> ToolCheckResult:
    """检测外部工具是否可用"""
    path = shutil.which(tool_name)
    if path is not None:
        return ToolCheckResult(name=tool_name, available=True, path=path)
    return ToolCheckResult(name=tool_name, available=False)


def check_all_tools() -> dict[str, ToolCheckResult]:
    """检测所有外部工具"""
    tools = ["ogr2ogr", "osmium", "tippecanoe", "java"]
    return {name: check_tool_available(name) for name in tools}
