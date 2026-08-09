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
    """Информационный эндпоинт реального времени."""
    return {
        "status": "online",
        "transport": "websocket",
        "ws_url": "/api/events/ws",
        "message": "Real-time system events channel via WebSockets",
    }


def _extract_token(websocket: WebSocket, token_query: Optional[str]) -> Optional[str]:
    """Извлечение JWT-токена из заголовка Sec-WebSocket-Protocol или query параметра."""
    if token_query:
        return token_query

    subprotocol_header = websocket.headers.get("sec-websocket-protocol")
    if subprotocol_header:
        parts = [p.strip() for p in subprotocol_header.split(",")]
        for i, part in enumerate(parts):
            if part.lower() == "bearer" and i + 1 < len(parts):
                return parts[i + 1]
            elif part.startswith("bearer."):
                return part.split(".", 1)[1]

    return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    """Безопасный WebSocket-эндпоинт с обязательной аутентификацией и поддержкой Replay."""
    raw_token = _extract_token(websocket, token)
    if not raw_token:
        _log.warning("Rejecting unauthenticated WS connection request")
        await websocket.close(code=1008, reason="Unauthorized: Missing authentication token")
        return

    payload = decode_access_token(raw_token)
    if not payload or "sub" not in payload:
        _log.warning("Rejecting WS connection with invalid token")
        await websocket.close(code=1008, reason="Unauthorized: Invalid token")
        return

    user_id = str(payload["sub"])
    subprotocol = "bearer" if "sec-websocket-protocol" in websocket.headers else None

    # Если токен передавался в субпротоколе, запрашиваем согласие со стороны сервера
    connected = await ws_manager.connect(websocket, user_id=user_id)
    if not connected:
        return

    try:
        while True:
            raw_data = await websocket.receive_text()
            ws_manager.update_pong(websocket)

            if raw_data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue
            elif raw_data == "pong":
                continue

            # Попытка парсинга JSON управляющего сообщения от клиента
            try:
                msg = json.loads(raw_data)
                msg_type = msg.get("type")
                if msg_type == "resume":
                    last_event_id = int(msg.get("last_event_id", 0))
                    await ws_manager.send_replay(websocket, last_event_id, user_id=user_id)
                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        _log.warning("WebSocket connection error for user %s: %s", user_id, exc)
        ws_manager.disconnect(websocket)
