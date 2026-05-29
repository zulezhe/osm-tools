"""拆分器抽象基类"""
from abc import ABC, abstractmethod
from typing import Callable


class BaseSplitter(ABC):
    """数据拆分抽象基类"""

    def __init__(
        self,
        on_progress: Callable[[int], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        self._on_progress = on_progress
        self._on_error = on_error

    @abstractmethod
    def split(self, input_path: str, output_dir: str, options: dict | None = None) -> list[str]:
        """执行拆分

        Args:
            input_path: 输入文件路径（PBF/GeoJSON）
            output_dir: 输出目录
            options: 拆分选项

        Returns:
            输出文件路径列表
        """
        ...

    def _report_progress(self, percent: int) -> None:
        if self._on_progress:
            self._on_progress(percent)

    def _report_error(self, msg: str) -> None:
        if self._on_error:
            self._on_error(msg)
