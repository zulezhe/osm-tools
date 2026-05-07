"""GDAL ogr2ogr 转换器"""
import subprocess
import time
from pathlib import Path

from .base import BaseConverter, ConversionResult, Format


class GDALConverter(BaseConverter):
    """使用 ogr2ogr 进行格式转换"""

    def convert(
        self,
        input_path: str,
        output_path: str,
        input_format: Format,
        output_format: Format,
        options: dict | None = None,
    ) -> ConversionResult:
        opts = options or {}
        start_time = time.time()

        try:
            cmd = self._build_command(input_path, output_path, output_format, opts)
            self._report_progress(10)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            self._report_progress(90)

            if result.returncode != 0:
                error_msg = result.stderr.strip() or f"ogr2ogr 返回错误码 {result.returncode}"
                self._report_error(error_msg)
                return ConversionResult(
                    input_path=input_path, output_path=output_path,
                    input_format=input_format, output_format=output_format,
                    success=False, error_message=error_msg,
                    duration_seconds=time.time() - start_time,
                )

            if not Path(output_path).exists():
                return ConversionResult(
                    input_path=input_path, output_path=output_path,
                    input_format=input_format, output_format=output_format,
                    success=False, error_message="输出文件未生成",
                    duration_seconds=time.time() - start_time,
                )

            self._report_progress(100)
            return ConversionResult(
                input_path=input_path, output_path=output_path,
                input_format=input_format, output_format=output_format,
                success=True, duration_seconds=time.time() - start_time,
            )

        except subprocess.TimeoutExpired:
            msg = "转换超时（超过 1 小时）"
            self._report_error(msg)
            return ConversionResult(
                input_path=input_path, output_path=output_path,
                input_format=input_format, output_format=output_format,
                success=False, error_message=msg,
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            self._report_error(str(e))
            return ConversionResult(
                input_path=input_path, output_path=output_path,
                input_format=input_format, output_format=output_format,
                success=False, error_message=str(e),
                duration_seconds=time.time() - start_time,
            )

    def _build_command(self, input_path: str, output_path: str, output_format: Format, options: dict) -> list[str]:
        cmd = ["ogr2ogr"]

        fmt_map = {
            Format.GEOJSON: "GeoJSON",
            Format.SHAPEFILE: "ESRI Shapefile",
            Format.GEOPACKAGE: "GPKG",
        }
        if output_format in fmt_map:
            cmd.extend(["-f", fmt_map[output_format]])

        encoding = options.get("encoding", "UTF-8")
        if output_format == Format.SHAPEFILE:
            cmd.extend(["-lco", f"ENCODING={encoding}"])

        if "srs" in options:
            cmd.extend(["-a_srs", options["srs"]])

        cmd.append("-overwrite")
        cmd.extend([output_path, input_path])
        return cmd
