"""Planetiler 发布器"""
import subprocess
import time
from pathlib import Path

from .base import BasePublisher, TileConfig, PublishResult


class PlanetilerPublisher(BasePublisher):
    """使用 Planetiler 生成矢量切片

    Planetiler 是 Java 工具，速度极快，适合大规模数据。
    需要安装 JRE 和下载 Planetiler JAR 文件。
    """

    def __init__(self, jar_path: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self._jar_path = jar_path or "planetiler.jar"

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
                return PublishResult(
                    output_path=output_path,
                    success=False,
                    error_message=result.stderr.strip(),
                    duration_seconds=time.time() - start_time,
                )

            total_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
            self._report_progress(100)
            return PublishResult(
                output_path=output_path,
                total_size_bytes=total_size,
                duration_seconds=time.time() - start_time,
                success=True,
            )

        except Exception as e:
            return PublishResult(output_path=output_path, success=False, error_message=str(e), duration_seconds=time.time() - start_time)

    def _build_command(self, input_path: str, output_path: str, config: TileConfig) -> list[str]:
        cmd = ["java", "-jar", self._jar_path]

        cmd.extend(["--input", input_path])
        cmd.extend(["--output", output_path])

        # 缩放范围
        cmd.append(f"--mbtiles={config.minzoom},{config.maxzoom}")

        # 切片大小
        if config.tile_size != 256:
            cmd.extend(["--tile-size", str(config.tile_size)])

        return cmd
