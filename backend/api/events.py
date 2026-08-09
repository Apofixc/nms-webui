import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.core.auth import consume_ws_ticket, decode_access_token, is_origin_allowed, is_session_revoked
from backend.core.events import ws_manager
from backend.core.plugin.registry import get_security_settings

_log = logging.getLogger("nms.api.events")

router = APIRouter(prefix="/api/events", tags=["events"])

MAX_FRAME_SIZE = 65536  # 64 KB
MAX_MESSAGES_PER_SECOND = 50
MAX_JSON_ERRORS = 5


def can_subscribe_to_topic(user_id: Optional[str], topic: str) -> bool:
    """Динамическая проверка прав доступа пользователя к топику WebSocket через систему разрешений (RBAC)."""
    if not topic:
        return False

    sec_settings = get_security_settings()
    if not sec_settings.get("auth_enabled", True):
        return True

    if not user_id:
        return False

    from backend.core.auth import user_has_permission

    # 1. Суперадминистратор имеет глобальный доступ ко всем топикам
    if user_has_permission(user_id, "system.admin") or user_has_permission(user_id, "system.all"):
        return True

    topic_str = topic.strip()
    base_name = topic_str.split(".")[0].split("_")[0]

    # 2. Прямая проверка наличия разрешения в БД (по названию топика или <resource>.view)
    if user_has_permission(user_id, topic_str) or user_has_permission(user_id, f"{base_name}.view"):
        return True

    # 3. Если топик относится к привилегированному ресурсу, но разрешения нет — отклонить
    protected_resources = {"audit", "logs", "users", "roles", "system", "admin", "security", "core"}
    if base_name in protected_resources or topic_str in protected_resources or topic_str.startswith("core."):
        return False

    # 4. Для остальных публичных/доменных топиков подписка разрешена
    return True


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


def _extract_token_and_subprotocol(websocket: WebSocket, token_query: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Извлечение токена/билета и согласованного subprotocol из заголовков или query."""
    subprotocol_header = websocket.headers.get("sec-websocket-protocol")
    accepted_subprotocol = None

    if subprotocol_header:
        parts = [p.strip() for p in subprotocol_header.split(",")]
        for i, part in enumerate(parts):
            if part.lower() == "bearer":
                accepted_subprotocol = "bearer"
                if i + 1 < len(parts):
                    return parts[i + 1], accepted_subprotocol
            elif part.startswith("bearer."):
                accepted_subprotocol = "bearer"
                return part.split(".", 1)[1], accepted_subprotocol

    if token_query:
        return token_query, accepted_subprotocol

    return None, accepted_subprotocol


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    protocol: Optional[str] = Query("json"),
):
    """Безопасный WebSocket-эндпоинт с RFC 6455 subprotocol, support msgpack/json, ticket-auth, лимитами и Replay."""
    # 1. Защита от CSWSH (Cross-Site WebSocket Hijacking)
    origin = websocket.headers.get("origin")
    if not is_origin_allowed(origin):
        _log.warning("Rejecting WS connection with untrusted origin: %s", origin)
        await websocket.close(code=1008, reason="Forbidden Origin (CSWSH Protection)")
        return

    # 2. Извлечение токена / билета и subprotocol
    raw_token, accepted_subprotocol = _extract_token_and_subprotocol(websocket, token)

    sec_settings = get_security_settings()
    auth_enabled = sec_settings.get("auth_enabled", True)

    user_id: Optional[str] = None
    jti: Optional[str] = None
    exp: Optional[float] = None

    if auth_enabled:
        if not raw_token:
            _log.warning("Rejecting unauthenticated WS connection request")
            await websocket.close(code=1008, reason="Unauthorized: Missing authentication token")
            return

        # Проверка одноразового билета
        if raw_token.startswith("wst_"):
            ticket_data = consume_ws_ticket(raw_token)
            if not ticket_data:
                _log.warning("Rejecting WS connection with invalid or expired ticket")
                await websocket.close(code=1008, reason="Unauthorized: Invalid ticket")
                return
            user_id = str(ticket_data["user_id"])
            jti = ticket_data.get("jti")
        else:
            payload = decode_access_token(raw_token)
            if not payload or "sub" not in payload:
                _log.warning("Rejecting WS connection with invalid token")
                await websocket.close(code=1008, reason="Unauthorized: Invalid token")
                return

            jti = payload.get("jti")
            if jti and is_session_revoked(jti):
                _log.warning("Rejecting WS connection with revoked session (jti=%s)", jti)
                await websocket.close(code=1008, reason="Unauthorized: Session revoked")
                return

            user_id = str(payload["sub"])
            exp = float(payload["exp"]) if "exp" in payload else None
    else:
        # Аутентификация отключена системно (auth_enabled = False)
        if raw_token and raw_token.startswith("wst_"):
            ticket_data = consume_ws_ticket(raw_token)
            if ticket_data:
                user_id = str(ticket_data["user_id"])
        elif raw_token and raw_token != "system_disabled_auth":
            payload = decode_access_token(raw_token)
            if payload and "sub" in payload:
                user_id = str(payload["sub"])

    # Регистрация подключения в ws_manager с подтверждением subprotocol и выбором формата кодирования
    connected = await ws_manager.connect(
        websocket,
        user_id=user_id,
        jti=jti,
        exp=exp,
        subprotocol=accepted_subprotocol,
        protocol_format=protocol or "json",
    )
    if not connected:
        return

    # Метрики rate limit и нарушений
    rate_window_start = time.time()
    msg_count = 0
    json_error_count = 0

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                ws_manager.disconnect(websocket)
                return

            raw_bytes = message.get("bytes")
            raw_text = message.get("text")
            frame_len = len(raw_bytes) if raw_bytes is not None else (len(raw_text) if raw_text is not None else 0)

            ws_manager.update_pong(websocket)

            # 1. Проверка размера кадра
            if frame_len > MAX_FRAME_SIZE:
                _log.warning("Closing WS connection for user %s: frame size exceeds %d bytes", user_id, MAX_FRAME_SIZE)
                await websocket.close(code=1009, reason="Message too large (max 64KB)")
                ws_manager.disconnect(websocket)
                return

            raw_data = raw_text if raw_text is not None else (raw_bytes.decode("utf-8", errors="replace") if raw_bytes else "")


            # 2. Rate Limiting
            now = time.time()
            if now - rate_window_start > 1.0:
                rate_window_start = now
                msg_count = 0

            msg_count += 1
            if msg_count > MAX_MESSAGES_PER_SECOND:
                _log.warning("Rate limit exceeded for WS user %s (%d msgs/sec)", user_id, msg_count)
                await websocket.close(code=4029, reason="Rate limit exceeded")
                ws_manager.disconnect(websocket)
                return

            # 3. Базовая обработка служебных строк / бинарных сообщений
            if raw_data in ("ping", "pong"):
                if raw_data == "ping":
                    await ws_manager._safe_send(websocket, {"type": "pong"})
                continue

            # 4. Парсинг управляющего объекта (msgpack или JSON)
            try:
                if raw_bytes and protocol == "msgpack":
                    import msgpack
                    try:
                        msg = msgpack.unpackb(raw_bytes, raw=False)
                    except Exception:
                        msg = json.loads(raw_bytes.decode("utf-8", errors="replace"))
                else:
                    msg = json.loads(raw_data) if isinstance(raw_data, str) else json.loads(raw_bytes.decode("utf-8", errors="replace"))

                json_error_count = 0  # Сброс ошибок при успешном парсинге
                msg_type = msg.get("type") if isinstance(msg, dict) else None

                # Поддержка ACK-протокола для любых клиентских управляющих команд
                ack_id = msg.get("ack_id")
                if ack_id:
                    await ws_manager._safe_send(
                        websocket,
                        {
                            "type": "ack",
                            "ack_id": str(ack_id),
                            "status": "received",
                            "timestamp": time.time(),
                        },
                    )

                if msg_type == "resume":

                    last_event_id = int(msg.get("last_event_id", 0))
                    await ws_manager.send_replay(websocket, last_event_id, user_id=user_id)
                elif msg_type == "subscribe":
                    topic = msg.get("topic")
                    if topic:
                        can_sub = await asyncio.to_thread(can_subscribe_to_topic, user_id, str(topic))
                        if can_sub:
                            ws_manager.subscribe_topic(websocket, str(topic))
                        else:
                            _log.warning("User %s denied subscription to sensitive topic %s", user_id, topic)
                            await ws_manager._safe_send(
                                websocket,
                                {
                                    "type": "error",
                                    "code": 403,
                                    "message": f"Permission denied for topic '{topic}'",
                                },
                            )
                elif msg_type == "unsubscribe":
                    topic = msg.get("topic")
                    if topic:
                        ws_manager.unsubscribe_topic(websocket, str(topic))
                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif msg_type == "pong":
                    pass
            except (json.JSONDecodeError, ValueError, TypeError):
                json_error_count += 1
                if json_error_count >= MAX_JSON_ERRORS:
                    _log.warning("Closing WS connection for user %s: too many malformed JSON frames", user_id)
                    await websocket.close(code=4000, reason="Too many malformed frames")
                    ws_manager.disconnect(websocket)
                    return
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        _log.warning("WebSocket connection error for user %s: %s", user_id, exc)
        ws_manager.disconnect(websocket)
