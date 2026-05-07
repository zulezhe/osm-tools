"""下载数据模型"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .task_state import TaskState


@dataclass
class DownloadTask:
    """下载任务数据模型"""
    url: str
    save_path: str
    source_type: str  # geofabrik / overpass / bbox
    state: TaskState = TaskState.PENDING
    total_bytes: int = 0
    downloaded_bytes: int = 0
    etag: str | None = None
    last_modified: str | None = None
    error_message: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def progress(self) -> float:
        """下载进度百分比"""
        if self.total_bytes <= 0:
            return 0.0
        return round(self.downloaded_bytes / self.total_bytes * 100, 2)

    @property
    def meta_path(self) -> Path:
        """meta 文件路径"""
        p = Path(self.save_path)
        return p.with_suffix(p.suffix + ".download_meta")

    def to_meta_file(self) -> Path:
        """保存为 meta 文件"""
        data = {
            "url": self.url,
            "save_path": self.save_path,
            "source_type": self.source_type,
            "total_bytes": self.total_bytes,
            "downloaded_bytes": self.downloaded_bytes,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "created_at": self.created_at,
            "updated_at": datetime.now().isoformat(),
        }
        meta = self.meta_path
        meta.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return meta

    @classmethod
    def from_meta_file(cls, meta_path: Path) -> "DownloadTask":
        """从 meta 文件加载"""
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return cls(
            url=data["url"],
            save_path=data["save_path"],
            source_type=data["source_type"],
            total_bytes=data.get("total_bytes", 0),
            downloaded_bytes=data.get("downloaded_bytes", 0),
            etag=data.get("etag"),
            last_modified=data.get("last_modified"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )
