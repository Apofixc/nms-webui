import asyncio
import json
import logging
from typing import AsyncGenerator, List, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

_log = logging.getLogger("nms.core.events")


class ConnectionManager:
    """Менеджер WebSocket соединений для рассылки событий в реальном времени."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        _log.info("WebSocket client connected (%d total)", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        _log.info("WebSocket client disconnected (%d total)", len(self.active_connections))

    async def broadcast_json(self, data: dict):
        """Рассылка JSON объекта всем подключенным вебсокет клиентам."""
        if not self.active_connections:
            return
        message = json.dumps(data)
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.add(connection)
        for conn in disconnected:
            self.active_connections.remove(conn)


ws_manager = ConnectionManager()


class EventBroadcaster:
    """Броадкастер событий для SSE и WebSockets."""

    def __init__(self):
        self.listeners: set[asyncio.Queue] = set()

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """Подписка SSE клиента."""
        queue = asyncio.Queue()
        self.listeners.add(queue)
        try:
            while True:
                msg = await queue.get()
                yield f"data: {msg}\n\n"
        finally:
            self.listeners.remove(queue)

    def broadcast(self, message: str, data_dict: dict = None):
        """Отправка сообщения всем SSE и WebSocket подписчикам."""
        for queue in self.listeners:
            queue.put_nowait(message)

        if data_dict:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(ws_manager.broadcast_json(data_dict))
            except RuntimeError:
                pass


broadcaster = EventBroadcaster()

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("")
async def sse_endpoint():
    """Эндпоинт для подключения SSE клиентов."""
    return StreamingResponse(
        broadcaster.subscribe(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Эндпоинт для подключения WebSocket клиентов."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Прием любых пинг/пакетов от клиента
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        _log.warning("WebSocket error: %s", exc)
        ws_manager.disconnect(websocket)


def notify_settings_changed(module_id: str):
    """Уведомить всех клиентов об изменении настроек модуля."""
    _log.debug("Settings changed for module: %s", module_id)
    payload = {"type": "module_settings_changed", "module_id": module_id}
    broadcaster.broadcast(json.dumps(payload), payload)
    try:
        from backend.core.notifications_api import create_notification
        create_notification(
            title="Изменение настроек",
            message=f"Обновлены настройки модуля {module_id}",
            notification_type="info",
            category="module",
        )
    except Exception:
        pass
