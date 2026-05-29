"""任务管理器 - 管理所有后台任务"""
import uuid
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from osm_tool.api.events import event_bus
from osm_tool.models.task_state import TaskState


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    task_type: str  # download / convert / split / process / publish
    status: str = TaskState.PENDING.value
    progress: float = 0.0
    result: Any = None
    error: str | None = None
    params: dict = field(default_factory=dict)
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed: float = 0.0
    _cancel_fn: Callable | None = field(default=None, repr=False)


class TaskManager:
    """管理所有后台任务"""

    def __init__(self):
        self._tasks: dict[str, TaskInfo] = {}
        self._lock = threading.Lock()

    def create_task(self, task_type: str, params: dict | None = None) -> TaskInfo:
        task_id = uuid.uuid4().hex[:12]
        info = TaskInfo(task_id=task_id, task_type=task_type, params=params or {})
        with self._lock:
            self._tasks[task_id] = info
        self._emit_event(info)
        return info

    def get_task(self, task_id: str) -> TaskInfo | None:
        return self._tasks.get(task_id)

    def list_tasks(self, task_type: str | None = None) -> list[dict]:
        with self._lock:
            tasks = list(self._tasks.values())
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        return [self._task_to_dict(t) for t in tasks]

    def update_progress(self, task_id: str, progress: float, **kwargs) -> None:
        info = self._tasks.get(task_id)
        if not info:
            return
        info.progress = progress
        for k, v in kwargs.items():
            if hasattr(info, k):
                setattr(info, k, v)
        self._emit_event(info)

    def complete_task(self, task_id: str, result: Any = None) -> None:
        info = self._tasks.get(task_id)
        if not info:
            return
        info.status = TaskState.COMPLETED.value
        info.progress = 100
        info.result = result
        self._emit_event(info)

    def fail_task(self, task_id: str, error: str) -> None:
        info = self._tasks.get(task_id)
        if not info:
            return
        info.status = TaskState.FAILED.value
        info.error = error
        self._emit_event(info)

    def cancel_task(self, task_id: str) -> bool:
        info = self._tasks.get(task_id)
        if not info:
            return False
        if info._cancel_fn:
            info._cancel_fn()
        info.status = TaskState.CANCELLED.value
        self._emit_event(info)
        return True

    def delete_task(self, task_id: str) -> bool:
        """删除任务（仅限已完成/失败/已取消）"""
        with self._lock:
            info = self._tasks.get(task_id)
            if not info:
                return False
            if info.status in (TaskState.PENDING.value, TaskState.DOWNLOADING.value):
                return False
            del self._tasks[task_id]
        return True

    def _emit_event(self, info: TaskInfo) -> None:
        event_bus.emit("task_progress", self._task_to_dict(info))

    @staticmethod
    def _task_to_dict(info: TaskInfo) -> dict:
        return {
            "task_id": info.task_id,
            "task_type": info.task_type,
            "status": info.status,
            "progress": info.progress,
            "error": info.error,
            "params": info.params,
            "result": str(info.result) if info.result is not None else None,
            "downloaded_bytes": info.downloaded_bytes,
            "total_bytes": info.total_bytes,
            "speed": info.speed,
        }


# 全局单例
task_manager = TaskManager()
