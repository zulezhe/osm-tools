"""发布管理器"""
import shutil

from .base import BasePublisher, TileConfig
from .tippecanoe_publisher import TippecanoePublisher
from .planetiler_publisher import PlanetilerPublisher


class PublishManager:
    """自动选择可用的发布器"""

    def __init__(self):
        self._tippecanoe = TippecanoePublisher()
        self._planetiler = PlanetilerPublisher()

    def get_publisher(self) -> BasePublisher:
        """获取可用的发布器"""
        if shutil.which("tippecanoe"):
            return self._tippecanoe
        if shutil.which("java"):
            return self._planetiler
        raise RuntimeError("未找到 tippecanoe 或 java，请安装其中之一")

    def publish(self, input_path: str, output_path: str, config: TileConfig):
        """便捷发布方法"""
        publisher = self.get_publisher()
        return publisher.publish(input_path, output_path, config)
