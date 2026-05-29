"""Tippecanoe 发布器"""
import subprocess
import time
from pathlib import Path

from .base import BasePublisher, TileConfig, OutputFormat, PublishResult


class TippecanoePublisher(BasePublisher):
    """使用 tippecanoe 生成矢量切片

    支持 MVT 目录、MBTiles、GeoJSON 切片三种输出。
    注意: tippecanoe 在 Windows 上需要 WSL。
    """

    def publish(self, input_path: str, output_path: str, config: TileConfig) -> PublishResult:
        start_time = time.time()

        try:
            cmd = self._build_command(input_path, output_path, config)
            self._report_progress(10)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=7200,
            )
            self._report_progress(90)

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                self._report_error(error_msg)
                return PublishResult(
                    output_path=output_path,
                    success=False,
                    error_message=error_msg,
                    duration_seconds=time.time() - start_time,
                )

            # 统计输出
            tile_count = self._parse_tile_count(result.stderr)
            total_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0

            self._report_progress(100)
            return PublishResult(
                output_path=output_path,
                tile_count=tile_count,
                total_size_bytes=total_size,
                duration_seconds=time.time() - start_time,
                success=True,
            )

        except subprocess.TimeoutExpired:
            msg = "切片生成超时"
            self._report_error(msg)
            return PublishResult(output_path=output_path, success=False, error_message=msg, duration_seconds=time.time() - start_time)
        except Exception as e:
            self._report_error(str(e))
            return PublishResult(output_path=output_path, success=False, error_message=str(e), duration_seconds=time.time() - start_time)

    def _build_command(self, input_path: str, output_path: str, config: TileConfig) -> list[str]:
        """构建 tippecanoe 命令行"""
        cmd = ["tippecanoe"]

        # 缩放级别
        cmd.extend(["-z", str(config.maxzoom)])
        cmd.extend(["-Z", str(config.minzoom)])

        # 切片大小
        if config.tile_size != 256:
            cmd.extend(["--tile-size", str(config.tile_size)])

        # 输出格式
        if config.output_format == OutputFormat.MVT_DIRECTORY:
            cmd.extend(["-e", output_path])
        elif config.output_format == OutputFormat.MBTILES:
            cmd.extend(["-o", output_path])
        elif config.output_format == OutputFormat.GEOJSON_TILES:
            cmd.extend(["-e", output_path, "--no-tile-compression"])

        # 图层
        for layer in config.layers:
            cmd.extend(["-l", layer.name])

        # 简化
        if not config.simplify:
            cmd.append("--no-simplification")

        # 删除标签
        for tag in config.drop_tags:
            cmd.extend(["--exclude", tag])

        # 覆盖已有
        cmd.append("--force")

        # 输入文件
        cmd.append(input_path)

        return cmd

    @staticmethod
    def _parse_tile_count(stderr: str) -> int:
        """从 tippecanoe 输出解析切片数"""
        for line in stderr.split("\n"):
            if "tiles" in line.lower():
                parts = line.split()
                for part in parts:
                    if part.isdigit():
                        return int(part)
        return 0
