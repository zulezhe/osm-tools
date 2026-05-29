"""下载中国行政区划数据（辅助脚本）

从 DataV.GeoAtlas 下载省/市/区县三级数据。
运行: uv run python scripts/download_admin_data.py
"""
import json
import sys
from pathlib import Path

import requests

BASE_URL = "https://geo.datav.aliyun.com/areas_v3/bound"
OUTPUT_DIR = Path(__file__).parent.parent / "src" / "osm_tool" / "resources" / "admin_boundaries"


def download_area(area_code: str, filename: str) -> None:
    """下载指定区域数据"""
    url = f"{BASE_URL}/{area_code}_full.json"
    print(f"下载 {filename} <- {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(resp.text, encoding="utf-8")
    print(f"  已保存: {path}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 下载省级
    download_area("100000", "provinces.json")

    # 下载各省级的市级数据
    provinces = json.loads((OUTPUT_DIR / "provinces.json").read_text(encoding="utf-8"))
    for feat in provinces.get("features", []):
        code = str(feat["properties"]["adcode"])
        name = feat["properties"]["name"]
        download_area(code, f"cities/{code}_full.json")

    print("下载完成！")


if __name__ == "__main__":
    main()
