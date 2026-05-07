"""Osmium-tool 转换器"""
import subprocess
import time

from .base import BaseConverter, ConversionResult, Format


class OsmiumConverter(BaseConverter):
    """使用 osmium-tool 进行 PBF 格式转换"""

    def convert(
        self,
        input_path: str,
        output_path: str,
        input_format: Format,
        output_format: Format,
        options: dict | None = None,
    ) -> ConversionResult:
        start_time = time.time()

        try:
            if input_format == Format.PBF and output_format == Format.GEOJSON:
                return self._pbf_to_geojson(input_path, output_path, start_time)

            return ConversionResult(
                input_path=input_path, output_path=output_path,
                input_format=input_format, output_format=output_format,
                success=False,
                error_message=f"不支持的转换: {input_format.value} → {output_format.value}",
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            return ConversionResult(
                input_path=input_path, output_path=output_path,
                input_format=input_format, output_format=output_format,
                success=False, error_message=str(e),
                duration_seconds=time.time() - start_time,
            )

    def _pbf_to_geojson(self, input_path: str, output_path: str, start_time: float) -> ConversionResult:
        cmd = ["osmium", "export", input_path, "-o", output_path, "--overwrite"]
        self._report_progress(10)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        self._report_progress(90)

        if result.returncode != 0:
            return ConversionResult(
                input_path=input_path, output_path=output_path,
                input_format=Format.PBF, output_format=Format.GEOJSON,
                success=False, error_message=result.stderr.strip(),
                duration_seconds=time.time() - start_time,
            )

        self._report_progress(100)
        return ConversionResult(
            input_path=input_path, output_path=output_path,
            input_format=Format.PBF, output_format=Format.GEOJSON,
            success=True, duration_seconds=time.time() - start_time,
        )
