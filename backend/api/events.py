import json
import logging
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.core.auth import decode_access_token
from backend.core.events import ws_manager

_log = logging.getLogger("nms.api.events")

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
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        _log.warning("WebSocket error: %s", exc)
        ws_manager.disconnect(websocket)
