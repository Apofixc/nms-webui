import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

from backend.core.database import get_db_connection

_log = logging.getLogger("nms.core.events")

MAX_CONNECTIONS_PER_USER = 10
SEND_TIMEOUT_SECONDS = 2.0
HEARTBEAT_INTERVAL = 30.0
HEARTBEAT_TIMEOUT = 60.0
BATCH_INTERVAL = 0.1  # 100ms


def record_event_in_db(event_type: str, payload_json: str, target_user_id: Optional[str] = None) -> int:
    """Запись события в персистентный журнал SQLite. Возвращает seq_id."""
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO system_events_journal (event_type, payload, target_user_id)
                VALUES (?, ?, ?)
                """,
                (event_type, payload_json, str(target_user_id) if target_user_id is not None else None),
            )
            return cursor.lastrowid
    except Exception as exc:
        _log.error("Failed to record WS event in SQLite journal: %s", exc)
        return 0
    finally:
        conn.close()


def prune_system_events_journal(max_age_days: int = 7, max_rows: int = 50000) -> int:
    """Прунинг (очистка) старых и избыточных записей журнала system_events_journal."""
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute(
                "DELETE FROM system_events_journal WHERE created_at < datetime('now', ?)",
                (f"-{max_age_days} days",),
            )
            deleted = cursor.rowcount or 0

            conn.execute(
                """
                DELETE FROM system_events_journal
                WHERE seq_id NOT IN (
                    SELECT seq_id FROM system_events_journal ORDER BY seq_id DESC LIMIT ?
                )
                """,
                (max_rows,),
            )
            return deleted
    except Exception as exc:
        _log.error("Failed to prune system_events_journal: %s", exc)
        return 0
    finally:
        conn.close()


def get_missed_events_from_db(last_event_id: int, target_user_id: Optional[str] = None, limit: int = 200) -> List[dict]:
    """Получение списка пропущенных событий из SQLite базы по last_event_id."""
    conn = get_db_connection()
    try:
        target_str = str(target_user_id) if target_user_id is not None else None
        if target_str:
            rows = conn.execute(
                """
                SELECT seq_id, event_type, payload, created_at
                FROM system_events_journal
                WHERE seq_id > ? AND (target_user_id IS NULL OR target_user_id = ?)
                ORDER BY seq_id ASC LIMIT ?
                """,
                (last_event_id, target_str, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT seq_id, event_type, payload, created_at
                FROM system_events_journal
                WHERE seq_id > ? AND target_user_id IS NULL
                ORDER BY seq_id ASC LIMIT ?
                """,
                (last_event_id, limit),
            ).fetchall()

        result = []
        for r in rows:
            try:
                payload_dict = json.loads(r["payload"])
            except Exception:
                payload_dict = {"payload": r["payload"]}
            payload_dict["seq_id"] = r["seq_id"]
            payload_dict["created_at"] = r["created_at"]
            result.append(payload_dict)
        return result
    except Exception as exc:
        _log.error("Failed to fetch missed events from SQLite: %s", exc)
        return []
    finally:
        conn.close()


class ConnectionManager:
    """Менеджер WebSocket соединений с поддержкой рассылки, Heartbeat и Replay."""

    def __init__(self):
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}
        self._batch_queue: List[dict] = []
        self._batch_lock = asyncio.Lock()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._batch_task: Optional[asyncio.Task] = None
        self._prune_task: Optional[asyncio.Task] = None

        # Метрики
        self.total_sent: int = 0
        self.total_received: int = 0
        self.total_dropped: int = 0

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        jti: Optional[str] = None,
        exp: Optional[float] = None,
        subprotocol: Optional[str] = None,
    ) -> bool:
        """Подключение сокета с поддержкой RFC 6455 subprotocol и лимитом соединений."""
        user_str = str(user_id) if user_id else None

        if user_str:
            user_conns = sum(1 for info in self.active_connections.values() if info.get("user_id") == user_str)
            if user_conns >= MAX_CONNECTIONS_PER_USER:
                _log.warning("Connection limit reached for user %s (%d max)", user_str, MAX_CONNECTIONS_PER_USER)
                await websocket.close(code=4008, reason="Too many active connections")
                self.total_dropped += 1
                return False

        if subprotocol:
            await websocket.accept(subprotocol=subprotocol)
        else:
            await websocket.accept()

        now = time.time()
        self.active_connections[websocket] = {
            "user_id": user_str,
            "jti": jti,
            "exp": exp,
            "connected_at": now,
            "last_pong_time": now,
            "topics": set(),
        }
        _log.info("WebSocket client connected (user_id=%s, total=%d)", user_str, len(self.active_connections))

        self._ensure_background_tasks()
        return True

    async def close_all(self, code: int = 1001, reason: str = "Server shutting down"):
        """Закрыть все открытые сокеты с кодом 1001 при остановке сервера."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()
        if self._prune_task and not self._prune_task.done():
            self._prune_task.cancel()

        connections = list(self.active_connections.keys())
        self.active_connections.clear()
        for ws in connections:
            try:
                await ws.close(code=code, reason=reason)
            except Exception:
                pass

    def disconnect(self, websocket: WebSocket):
        """Отключение сокета и очистка метаданных."""
        info = self.active_connections.pop(websocket, None)
        if info:
            _log.info("WebSocket client disconnected (user_id=%s, total=%d)", info.get("user_id"), len(self.active_connections))

    def update_pong(self, websocket: WebSocket):
        """Обновить timestamp последнего PONG / активности сокета."""
        if websocket in self.active_connections:
            self.active_connections[websocket]["last_pong_time"] = time.time()
            self.total_received += 1

    def subscribe_topic(self, websocket: WebSocket, topic: str):
        """Подписать подключение на топик."""
        if websocket in self.active_connections and topic:
            self.active_connections[websocket]["topics"].add(topic)

    def unsubscribe_topic(self, websocket: WebSocket, topic: str):
        """Отписать подключение от топика."""
        if websocket in self.active_connections and topic:
            self.active_connections[websocket]["topics"].discard(topic)

    def get_metrics(self) -> dict:
        """Получить текущие метрики WebSocket соединений."""
        return {
            "active_connections": len(self.active_connections),
            "total_sent": self.total_sent,
            "total_received": self.total_received,
            "total_dropped": self.total_dropped,
        }

    def _ensure_background_tasks(self):
        """Запуск фоновых задач Heartbeat, Batch Flush и Prune, если они еще не запущены."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = loop.create_task(self._heartbeat_loop())
        if self._batch_task is None or self._batch_task.done():
            self._batch_task = loop.create_task(self._batch_flush_loop())
        if self._prune_task is None or self._prune_task.done():
            self._prune_task = loop.create_task(self._prune_loop())

    async def _heartbeat_loop(self):
        """Фоновый цикл Heartbeat: периодический ping, проверка exp и закрытие зависших/отозванных сокетов."""
        from backend.core.auth import is_session_revoked
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            if not self.active_connections:
                continue

            now = time.time()
            stale_sockets: Set[WebSocket] = set()
            revoked_sockets: Set[WebSocket] = set()
            expired_sockets: Set[WebSocket] = set()

            for ws, info in list(self.active_connections.items()):
                exp = info.get("exp")
                if exp and now > exp:
                    _log.warning("WebSocket token expired for user_id=%s", info.get("user_id"))
                    expired_sockets.add(ws)
                elif info.get("jti") and is_session_revoked(info["jti"]):
                    _log.warning("WebSocket session revoked for user_id=%s (jti=%s)", info.get("user_id"), info.get("jti"))
                    revoked_sockets.add(ws)
                elif now - info["last_pong_time"] > HEARTBEAT_TIMEOUT:
                    _log.warning("WebSocket connection timeout for user_id=%s (stale)", info.get("user_id"))
                    stale_sockets.add(ws)
                else:
                    try:
                        await self._safe_send(ws, json.dumps({"type": "ping"}))
                    except Exception:
                        stale_sockets.add(ws)

            for ws in expired_sockets:
                self.disconnect(ws)
                try:
                    await ws.close(code=1008, reason="Token expired")
                except Exception:
                    pass

            for ws in revoked_sockets:
                self.disconnect(ws)
                try:
                    await ws.close(code=1008, reason="Session revoked")
                except Exception:
                    pass

            for ws in stale_sockets:
                self.disconnect(ws)
                try:
                    await ws.close(code=1001, reason="Heartbeat timeout")
                except Exception:
                    pass

    async def _safe_send(self, websocket: WebSocket, message: str):
        """Безопасная отправка кадра с таймаутом и подсчетом статистики."""
        try:
            await asyncio.wait_for(websocket.send_text(message), timeout=SEND_TIMEOUT_SECONDS)
            self.total_sent += 1
        except Exception as exc:
            _log.debug("Error sending WS message to client: %s", exc)
            self.total_dropped += 1
            self.disconnect(websocket)

    async def broadcast_immediate(self, data: dict, target_user_id: Optional[str] = None, topic: Optional[str] = None):
        """Мгновенная рассылка срочных/критических событий всем подходящим клиентам."""
        if not self.active_connections:
            return

        event_type = data.get("type", "event")
        payload_str = json.dumps(data)
        seq_id = await asyncio.to_thread(record_event_in_db, event_type, payload_str, target_user_id)
        data["seq_id"] = seq_id

        message = json.dumps(data)
        target_str = str(target_user_id) if target_user_id is not None else None

        tasks = []
        for ws, info in list(self.active_connections.items()):
            if target_str is not None and info.get("user_id") != target_str:
                continue
            if topic is not None and topic not in info.get("topics", set()):
                continue
            tasks.append(self._safe_send(ws, message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_batched(self, data: dict, target_user_id: Optional[str] = None, topic: Optional[str] = None):
        """Добавление события в очередь пакетной рассылки (батчинга)."""
        event_type = data.get("type", "event")
        payload_str = json.dumps(data)
        seq_id = await asyncio.to_thread(record_event_in_db, event_type, payload_str, target_user_id)
        data["seq_id"] = seq_id

        async with self._batch_lock:
            self._batch_queue.append({
                "data": data,
                "target_user_id": str(target_user_id) if target_user_id is not None else None,
                "topic": topic,
            })

    async def _batch_flush_loop(self):
        """Фоновый цикл отправки накопившихся сообщений каждые 100 мс с изоляцией по получателям."""
        while True:
            await asyncio.sleep(BATCH_INTERVAL)
            if not self._batch_queue or not self.active_connections:
                continue

            async with self._batch_lock:
                items_to_send = self._batch_queue[:]
                self._batch_queue.clear()

            if not items_to_send:
                continue

            tasks = []
            for ws, info in list(self.active_connections.items()):
                user_id = info.get("user_id")
                user_topics = info.get("topics", set())

                user_events = []
                seen_telemetry_keys: Set[str] = set()

                for item in reversed(items_to_send):
                    target = item.get("target_user_id")
                    topic = item.get("topic")
                    data = item.get("data", {})

                    if target is not None and target != user_id:
                        continue
                    if topic is not None and topic not in user_topics:
                        continue

                    # Коалесцинг телеметрии по ключу (оставляем только последнее значение)
                    t_key = data.get("telemetry_key") or data.get("key")
                    if t_key:
                        if t_key in seen_telemetry_keys:
                            continue
                        seen_telemetry_keys.add(t_key)

                    user_events.append(data)

                user_events.reverse()

                if user_events:
                    batch_msg = json.dumps({
                        "type": "batch",
                        "events": user_events,
                    })
                    tasks.append(self._safe_send(ws, batch_msg))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _prune_loop(self):
        """Фоновая периодическая очистка журнала событий (каждые 6 часов)."""
        while True:
            await asyncio.sleep(21600)
            await asyncio.to_thread(prune_system_events_journal)

    async def send_replay(self, websocket: WebSocket, last_event_id: int, user_id: Optional[str] = None):
        """Досылка пропущенных сообщений по last_event_id из SQLite."""
        missed = await asyncio.to_thread(get_missed_events_from_db, last_event_id, target_user_id=user_id, limit=200)
        if missed:
            replay_msg = json.dumps({
                "type": "replay",
                "last_event_id": last_event_id,
                "events": missed,
            })
            await self._safe_send(websocket, replay_msg)
        else:
            resync_msg = json.dumps({
                "type": "resync_required",
                "message": "No missed events in journal or gap too large",
            })
            await self._safe_send(websocket, resync_msg)


ws_manager = ConnectionManager()


class EventBroadcaster:
    """Броадкастер событий для WebSockets с поддержкой мгновенной и пакетной отправки."""

    def broadcast(
        self,
        message: str = "",
        data_dict: dict = None,
        target_user_id: Optional[str] = None,
        topic: Optional[str] = None,
        immediate: bool = True,
    ):
        """Отправка сообщения WebSocket подписчикам."""
        if not data_dict and message:
            try:
                data_dict = json.loads(message)
            except Exception:
                data_dict = {"type": "raw_event", "payload": message}

        if not data_dict:
            return

        coro = (
            ws_manager.broadcast_immediate(data_dict, target_user_id=target_user_id, topic=topic)
            if immediate
            else ws_manager.broadcast_batched(data_dict, target_user_id=target_user_id, topic=topic)
        )

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(coro, loop)
            except Exception as exc:
                _log.warning("Could not broadcast WS event: %s", exc)


broadcaster = EventBroadcaster()


def notify_settings_changed(module_id: str):
    """Уведомить всех клиентов об изменении настроек модуля (мгновенно)."""
    _log.debug("Settings changed for module: %s", module_id)
    payload = {"type": "module_settings_changed", "module_id": module_id}
    broadcaster.broadcast(json.dumps(payload), payload, immediate=True)


def __getattr__(name: str):
    if name == "router":
        from backend.api.events import router
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
