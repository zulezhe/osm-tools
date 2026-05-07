"""转换管理器 - 自动路由"""
from .base import BaseConverter, Format
from .gdal_converter import GDALConverter
from .osmium_converter import OsmiumConverter


class ConversionManager:
    """根据输入/输出格式自动选择最佳转换器"""

    def __init__(self):
        self._gdal = GDALConverter()
        self._osmium = OsmiumConverter()

    def get_converter(self, input_fmt: Format, output_fmt: Format) -> BaseConverter | None:
        if input_fmt == output_fmt:
            return None
        if input_fmt == Format.PBF:
            return self._osmium
        return self._gdal

    def convert(
        self,
        input_path: str,
        output_path: str,
        output_format: Format | None = None,
        options: dict | None = None,
    ):
        input_format = BaseConverter.detect_format(input_path)
        if input_format is None:
            raise ValueError(f"无法识别输入文件格式: {input_path}")

        fmt = output_format or BaseConverter.detect_format(output_path)
        if fmt is None:
            raise ValueError(f"无法识别输出文件格式: {output_path}")

        converter = self.get_converter(input_format, fmt)
        if converter is None:
            raise ValueError("相同格式无需转换")

        return converter.convert(input_path, output_path, input_format, fmt, options)
