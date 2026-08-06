import asyncio
import json
import logging
from typing import Dict, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.core.auth import decode_access_token

_log = logging.getLogger("nms.core.events")


class ConnectionManager:
    """Менеджер WebSocket соединений для рассылки событий в реальном времени."""

    def __init__(self):
        self.active_connections: Dict[WebSocket, Optional[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None):
        await websocket.accept()
        self.active_connections[websocket] = str(user_id) if user_id else None
        _log.info(
            "WebSocket client connected (user_id=%s, %d total)",
            user_id,
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket):
        self.active_connections.pop(websocket, None)
        _log.info("WebSocket client disconnected (%d total)", len(self.active_connections))

    async def broadcast_json(self, data: dict, target_user_id: Optional[str] = None):
        """Рассылка JSON объекта WebSocket клиентам (всему пулу или адресно по user_id)."""
        if not self.active_connections:
            return
        message = json.dumps(data)
        target_str = str(target_user_id) if target_user_id is not None else None
        disconnected = set()

        for connection, conn_user_id in list(self.active_connections.items()):
            # Если целевой user_id указан, отправляем только соответствующему пользователю
            if target_str is not None and conn_user_id != target_str:
                continue
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.add(connection)

        for conn in disconnected:
            self.disconnect(conn)


ws_manager = ConnectionManager()


class EventBroadcaster:
    """Броадкастер событий для WebSockets."""

    def broadcast(self, message: str = "", data_dict: dict = None, target_user_id: Optional[str] = None):
        """Отправка сообщения WebSocket подписчикам."""
        if not data_dict and message:
            try:
                data_dict = json.loads(message)
            except Exception:
                data_dict = {"type": "raw_event", "payload": message}

        if data_dict:
            # Если target_user_id явным образом не передан, пытаемся взять его из объекта уведомления
            if target_user_id is None and isinstance(data_dict, dict):
                notif = data_dict.get("notification")
                if isinstance(notif, dict) and notif.get("user_id"):
                    target_user_id = notif.get("user_id")

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(ws_manager.broadcast_json(data_dict, target_user_id=target_user_id))
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            ws_manager.broadcast_json(data_dict, target_user_id=target_user_id), loop
                        )
                except Exception as exc:
                    _log.warning("Could not broadcast WS event: %s", exc)


broadcaster = EventBroadcaster()

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("")
@router.get("/")
async def get_events_info():
    """Информационный эндпоинт реального времени (SSE заменен на WebSockets)."""
    return {
        "status": "online",
        "transport": "websocket",
        "ws_url": "/api/events/ws",
        "message": "Real-time stream has been migrated to WebSockets at /api/events/ws",
    }


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    """Эндпоинт для подключения WebSocket клиентов с опциональной аутентификацией."""
    user_id = None
    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            user_id = str(payload["sub"])

    await ws_manager.connect(websocket, user_id=user_id)
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
