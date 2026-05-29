"""数据压缩处理器"""
import gzip
import shutil
import zipfile
from pathlib import Path


class Compressor:
    """数据压缩"""

    def compress_geojson(self, input_path: str, compression_level: int = 6) -> str:
        output_path = input_path + ".gz"
        with open(input_path, "rb") as f_in:
            with gzip.open(output_path, "wb", compresslevel=compression_level) as f_out:
                shutil.copyfileobj(f_in, f_out)
        return output_path

    def compress_shapefile(self, input_dir: str, output_path: str) -> str:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
                p = Path(input_dir + ext)
                if p.exists():
                    zf.write(str(p), p.name)
        return output_path
