import asyncio
import logging
from typing import AsyncGenerator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

_log = logging.getLogger("nms.core.events")

class EventBroadcaster:
    """Простой броадкастер событий для SSE."""
    def __init__(self):
        self.listeners: set[asyncio.Queue] = set()

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """Подписка нового клиента."""
        queue = asyncio.Queue()
        self.listeners.add(queue)
        try:
            while True:
                msg = await queue.get()
                yield f"data: {msg}\n\n"
        finally:
            self.listeners.remove(queue)

    def broadcast(self, message: str):
        """Отправка сообщения всем подписчикам."""
        for queue in self.listeners:
            queue.put_nowait(message)

# Глобальный экземпляр для системы
broadcaster = EventBroadcaster()

router = APIRouter(prefix="/api/events", tags=["events"])

@router.get("")
async def sse_endpoint():
    """Эндпоинт для подключения EventSource с фронтенда."""
    return StreamingResponse(
        broadcaster.subscribe(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Для Nginx (отключение буферизации)
        }
    )

def notify_settings_changed(module_id: str):
    """Уведомить всех клиентов об изменении настроек модуля."""
    _log.debug("Settings changed for module: %s", module_id)
    broadcaster.broadcast(f'{{"type": "module_settings_changed", "module_id": "{module_id}"}}')
