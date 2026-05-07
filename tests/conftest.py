"""测试公共 fixtures"""
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir():
    """临时目录 fixture"""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_pbf_url():
    """Geofabrik 示例 URL"""
    return "https://download.geofabrik.de/asia/china-latest.osm.pbf"
