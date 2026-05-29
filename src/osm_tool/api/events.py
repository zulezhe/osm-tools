"""SSE 事件推送"""
import asyncio
import json
from typing import Any

from sse_starlette.sse import EventSourceResponse
from starlette.requests import Request


class EventBus:
    """全局事件总线，管理 SSE 订阅和事件分发"""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        payload = json.dumps({"type": event_type, **data}, ensure_ascii=False)
        for q in self._subscribers:
            q.put_nowait(payload)


# 全局单例
event_bus = EventBus()


async def sse_endpoint(request: Request) -> EventSourceResponse:
    """SSE 端点：/api/v1/events"""

    async def event_generator():
        q = event_bus.subscribe()
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(q.get(), timeout=30)
                    yield {"event": "message", "data": data}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        finally:
            event_bus.unsubscribe(q)

    return EventSourceResponse(event_generator())
