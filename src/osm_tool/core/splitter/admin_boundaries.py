"""行政区划数据管理"""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RegionInfo:
    """区域信息"""
    code: str
    name: str
    geojson_path: str
    parent_code: str = ""


class AdminBoundaryManager:
    """中国行政区划管理器

    使用 DataV.GeoAtlas 数据（省/市/区县三级）
    """

    BASE_URL = "https://geo.datav.aliyun.com/areas_v3/bound"

    def __init__(self, data_dir: str | None = None):
        if data_dir is None:
            data_dir = str(Path(__file__).parent.parent.parent / "resources" / "admin_boundaries")
        self._data_dir = Path(data_dir)
        self._provinces: list[RegionInfo] = []
        self._cities: dict[str, list[RegionInfo]] = {}
        self._districts: dict[str, list[RegionInfo]] = {}

    def load_provinces(self) -> list[RegionInfo]:
        """加载省级行政区"""
        path = self._data_dir / "provinces.json"
        if not path.exists():
            self._download("100000_full", path)
        self._provinces = self._parse_regions(path, parent_code="")
        return self._provinces

    def load_cities(self, province_code: str) -> list[RegionInfo]:
        """加载市级行政区"""
        if province_code in self._cities:
            return self._cities[province_code]
        path = self._data_dir / "cities" / f"{province_code}_full.json"
        if not path.exists():
            self._download(f"{province_code}_full", path)
        self._cities[province_code] = self._parse_regions(path, parent_code=province_code)
        return self._cities[province_code]

    def load_districts(self, city_code: str) -> list[RegionInfo]:
        """加载区县级行政区"""
        if city_code in self._districts:
            return self._districts[city_code]
        path = self._data_dir / "districts" / f"{city_code}_full.json"
        if not path.exists():
            self._download(f"{city_code}_full", path)
        self._districts[city_code] = self._parse_regions(path, parent_code=city_code)
        return self._districts[city_code]

    def _parse_regions(self, path: Path, parent_code: str) -> list[RegionInfo]:
        """解析 GeoJSON 区域文件"""
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        regions = []
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            regions.append(RegionInfo(
                code=str(props.get("adcode", "")),
                name=props.get("name", ""),
                geojson_path=str(path),
                parent_code=parent_code,
            ))
        return regions

    def _download(self, area_code: str, save_path: Path) -> None:
        """从 DataV 下载行政区划数据"""
        import requests
        save_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"{self.BASE_URL}/{area_code}.json"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        save_path.write_text(resp.text, encoding="utf-8")
