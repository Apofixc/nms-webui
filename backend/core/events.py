import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from backend.core.database import get_db_connection

_log = logging.getLogger("nms.core.events")

MAX_CONNECTIONS_PER_USER = 10
SEND_TIMEOUT_SECONDS = 2.0
HEARTBEAT_INTERVAL = 30.0
HEARTBEAT_TIMEOUT = 60.0
BATCH_INTERVAL = 0.1  # 100ms


def record_event_in_db(event_type: str, payload_json: str, target_user_id: Optional[str] = None, topic: Optional[str] = None) -> int:
    """Запись события в персистентный журнал SQLite. Возвращает seq_id."""
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO system_events_journal (event_type, payload, target_user_id, topic)
                VALUES (?, ?, ?, ?)
                """,
                (
                    event_type,
                    payload_json,
                    str(target_user_id) if target_user_id is not None else None,
                    str(topic) if topic is not None else None,
                ),
            )
            return cursor.lastrowid
    except Exception as exc:
        _log.error("Failed to record WS event in SQLite journal: %s", exc)
        return 0
    finally:
        conn.close()


class EventJournalQueue:
    """Асинхронная пакетная очередь для высокопроизводительной записи событий в SQLite без blocking overhead."""

    def __init__(self, flush_interval: float = 0.5, max_batch_size: int = 500):
        self.flush_interval = flush_interval
        self.max_batch_size = max_batch_size
        self._queue: Optional[asyncio.Queue] = None
        self._task: Optional[asyncio.Task] = None
        self._notify_event: Optional[asyncio.Event] = None

    def _ensure_started(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        if self._queue is None:
            self._queue = asyncio.Queue()
        if self._notify_event is None:
            self._notify_event = asyncio.Event()

        if self._task is None or self._task.done():
            self._task = loop.create_task(self._flush_loop())

    async def record_event_async(
        self,
        event_type: str,
        payload_json: str,
        target_user_id: Optional[str] = None,
        topic: Optional[str] = None,
        immediate: bool = False,
    ) -> int:
        """Асинхронно добавить событие в очередь пакетной записи и дождаться seq_id."""
        self._ensure_started()
        if self._queue is None:
            return await asyncio.to_thread(record_event_in_db, event_type, payload_json, target_user_id, topic)

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[int] = loop.create_future()
        await self._queue.put((event_type, payload_json, target_user_id, topic, fut))
        if immediate and self._notify_event:
            self._notify_event.set()
        return await fut

    async def _flush_loop(self):
        """Фоновый цикл пакетной записи раз в flush_interval секунд (или мгновенно при immediate)."""
        while True:
            if self._notify_event:
                try:
                    await asyncio.wait_for(self._notify_event.wait(), timeout=self.flush_interval)
                    self._notify_event.clear()
                except asyncio.TimeoutError:
                    pass
            else:
                await asyncio.sleep(self.flush_interval)

            if self._queue is None or self._queue.empty():
                continue

            batch = []
            while not self._queue.empty() and len(batch) < self.max_batch_size:
                try:
                    item = self._queue.get_nowait()
                    batch.append(item)
                except asyncio.QueueEmpty:
                    break

            if not batch:
                continue

            def _write_batch(items):
                results = []
                conn = get_db_connection()
                try:
                    with conn:
                        for event_type, payload_json, target_user_id, topic, fut in items:
                            try:
                                cursor = conn.execute(
                                    """
                                    INSERT INTO system_events_journal (event_type, payload, target_user_id, topic)
                                    VALUES (?, ?, ?, ?)
                                    """,
                                    (
                                        event_type,
                                        payload_json,
                                        str(target_user_id) if target_user_id is not None else None,
                                        str(topic) if topic is not None else None,
                                    ),
                                )
                                seq_id = cursor.lastrowid
                                results.append((fut, seq_id))
                            except Exception as exc:
                                _log.error("Failed to insert WS event item: %s", exc)
                                results.append((fut, 0))
                except Exception as exc:
                    _log.error("Failed to execute SQLite batch insert: %s", exc)
                    for _, _, _, _, fut in items:
                        results.append((fut, 0))
                finally:
                    conn.close()
                return results

            results = await asyncio.to_thread(_write_batch, batch)
            for fut, seq_id in results:
                if not fut.done():
                    fut.set_result(seq_id)


event_journal_queue = EventJournalQueue()



def prune_system_events_journal(max_age_days: int = 7, max_rows: int = 50000) -> int:
    """Прунинг (очистка) старых и избыточных записей журнала system_events_journal."""
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute(
                """
                DELETE FROM system_events_journal
                WHERE created_at < datetime('now', ?)
                   OR seq_id NOT IN (
                       SELECT seq_id FROM system_events_journal ORDER BY seq_id DESC LIMIT ?
                   )
                """,
                (f"-{max_age_days} days", max_rows),
            )
            return cursor.rowcount or 0
    except Exception as exc:
        _log.error("Failed to prune system_events_journal: %s", exc)
        return 0
    finally:
        conn.close()



def check_replay_status_from_db(
    last_event_id: int,
    target_user_id: Optional[str] = None,
    topics: Optional[Set[str]] = None,
    limit: int = 200,
) -> tuple[str, List[dict]]:
    """Проверка состояния истории событий и получение досланных записей без ложного resync_required."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT MIN(seq_id) as min_seq, MAX(seq_id) as max_seq FROM system_events_journal").fetchone()
        min_seq = row["min_seq"] if row and row["min_seq"] is not None else 0
        max_seq = row["max_seq"] if row and row["max_seq"] is not None else 0

        # Если БД пустая или last_event_id >= max_seq, разрыва нет
        if max_seq == 0 or last_event_id >= max_seq:
            return "replay", []

        # Если last_event_id меньше min_seq - 1 (записи до min_seq вычищены)
        if min_seq > 0 and last_event_id < (min_seq - 1):
            return "resync_required", []

        target_str = str(target_user_id) if target_user_id is not None else None
        
        # Динамическое построение SQL условия с поддержкой топиков и таргетирования
        conditions = ["seq_id > ?"]
        params: List[Any] = [last_event_id]

        if target_str:
            conditions.append("(target_user_id IS NULL OR target_user_id = ?)")
            params.append(target_str)
        else:
            conditions.append("target_user_id IS NULL")

        if topics is not None:
            if topics:
                placeholders = ",".join(["?"] * len(topics))
                conditions.append(f"(topic IS NULL OR topic IN ({placeholders}))")
                params.extend(list(topics))
            else:
                conditions.append("topic IS NULL")

        where_clause = " AND ".join(conditions)

        # 1. Проверяем общее число пропущенных событий с учётом топиков
        count_row = conn.execute(
            f"SELECT COUNT(*) as total_count FROM system_events_journal WHERE {where_clause}",
            params,
        ).fetchone()
        total_missed = count_row["total_count"] if count_row else 0

        # Если количество пропущенных событий превышает limit replay (200) — выдаем resync_required во избежание потери остатка
        if total_missed > limit:
            _log.info("Replay gap too large (%d > %d events) for user=%s, requiring full resync", total_missed, limit, target_str)
            return "resync_required", []

        # 2. Выборка досланных событий
        rows = conn.execute(
            f"""
            SELECT seq_id, event_type, payload, topic, created_at
            FROM system_events_journal
            WHERE {where_clause}
            ORDER BY seq_id ASC LIMIT ?
            """,
            params + [limit],
        ).fetchall()

        result = []
        for r in rows:
            try:
                payload_dict = json.loads(r["payload"])
            except Exception:
                payload_dict = {"payload": r["payload"]}
            payload_dict["seq_id"] = r["seq_id"]
            payload_dict["created_at"] = r["created_at"]
            if "type" not in payload_dict:
                payload_dict["type"] = r["event_type"]
            result.append(payload_dict)
        return "replay", result
    except Exception as exc:
        _log.error("Failed to fetch missed events from SQLite: %s", exc)
        return "replay", []
    finally:
        conn.close()


def get_missed_events_from_db(
    last_event_id: int,
    target_user_id: Optional[str] = None,
    topics: Optional[Set[str]] = None,
    limit: int = 200,
) -> List[dict]:
    """Получение списка пропущенных событий из SQLite базы по last_event_id."""
    _, events = check_replay_status_from_db(last_event_id, target_user_id=target_user_id, topics=topics, limit=limit)
    return events



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
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _prune_dead_connections(self):
        """Очистить соединения из active_connections, если сокет разорван или превысил таймаут."""
        now = time.time()
        dead = []
        for ws, info in list(self.active_connections.items()):
            is_dead = False
            try:
                if getattr(ws, "client_state", None) == WebSocketState.DISCONNECTED or getattr(ws, "application_state", None) == WebSocketState.DISCONNECTED:
                    is_dead = True
                elif now - info.get("last_pong_time", now) > HEARTBEAT_TIMEOUT:
                    is_dead = True
            except Exception:
                is_dead = True

            if is_dead:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        jti: Optional[str] = None,
        exp: Optional[float] = None,
        subprotocol: Optional[str] = None,
        protocol_format: str = "json",
    ) -> bool:
        """Подключение сокета с поддержкой RFC 6455 subprotocol, формата msgpack/json, авто-отбраковкой и LRU вытеснением."""
        user_str = str(user_id) if user_id else None

        # 1. Мгновенная отбраковка разорванных/зависших соединений
        self._prune_dead_connections()

        # 2. LRU вытеснение старейшего сокета пользователя при превышении лимита
        if user_str:
            user_conns = [(ws, info) for ws, info in self.active_connections.items() if info.get("user_id") == user_str]
            if len(user_conns) >= MAX_CONNECTIONS_PER_USER:
                _log.info(
                    "Connection limit (%d) reached for user %s. Evicting oldest stale connection.",
                    MAX_CONNECTIONS_PER_USER,
                    user_str,
                )
                user_conns.sort(key=lambda x: x[1].get("connected_at", 0))
                oldest_ws, _ = user_conns[0]
                self.disconnect(oldest_ws)
                try:
                    await oldest_ws.close(code=4008, reason="Connection replaced by newer session")
                except Exception:
                    pass

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
            "protocol_format": protocol_format,
        }
        _log.info("WebSocket client connected (user_id=%s, format=%s, total=%d)", user_str, protocol_format, len(self.active_connections))

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

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Сохранить ссылку на основной Event Loop приложения."""
        self._loop = loop

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
            self._loop = loop
        except RuntimeError:
            loop = getattr(self, "_loop", None)
            if not loop or not loop.is_running():
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
                elif info.get("jti") and await asyncio.to_thread(is_session_revoked, info["jti"]):
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

    async def _safe_send(self, websocket: WebSocket, payload: Any):
        """Безопасная отправка кадра (JSON или msgpack) с таймаутом и подсчетом статистики."""
        try:
            info = self.active_connections.get(websocket, {})
            fmt = info.get("protocol_format", "json")
            if fmt == "msgpack":
                import msgpack
                if isinstance(payload, str):
                    try:
                        data_obj = json.loads(payload)
                    except Exception:
                        data_obj = {"payload": payload}
                else:
                    data_obj = payload
                raw_bytes = msgpack.packb(data_obj)
                await asyncio.wait_for(websocket.send_bytes(raw_bytes), timeout=SEND_TIMEOUT_SECONDS)
            else:
                msg_str = payload if isinstance(payload, str) else json.dumps(payload)
                await asyncio.wait_for(websocket.send_text(msg_str), timeout=SEND_TIMEOUT_SECONDS)
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
        seq_id = await event_journal_queue.record_event_async(
            event_type, payload_str, target_user_id, topic=topic, immediate=True
        )
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
        seq_id = await event_journal_queue.record_event_async(event_type, payload_str, target_user_id, topic=topic)
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
        """Досылка пропущенных сообщений по last_event_id из SQLite с учетом топиков."""
        user_topics = self.active_connections.get(websocket, {}).get("topics")
        status, missed = await asyncio.to_thread(
            check_replay_status_from_db,
            last_event_id,
            target_user_id=user_id,
            topics=user_topics,
            limit=200,
        )
        if status == "replay":
            replay_msg = json.dumps({
                "type": "replay",
                "last_event_id": last_event_id,
                "events": missed,
            })
            await self._safe_send(websocket, replay_msg)
        else:
            resync_msg = json.dumps({
                "type": "resync_required",
                "message": "Gap detected in event journal due to pruning",
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

        scheduled = False
        try:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro)
                if getattr(ws_manager, "_loop", None) is None:
                    ws_manager._loop = loop
                scheduled = True
            except RuntimeError:
                loop = getattr(ws_manager, "_loop", None)
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(coro, loop)
                    scheduled = True
                else:
                    _log.warning("Could not broadcast WS event from thread context: no running event loop available")
        finally:
            if not scheduled:
                coro.close()


broadcaster = EventBroadcaster()


def notify_settings_changed(module_id: str):
    """Уведомить всех клиентов об изменении настроек модуля (мгновенно)."""
    _log.debug("Settings changed for module: %s", module_id)
    payload = {"type": "module_settings_changed", "module_id": module_id}
    broadcaster.broadcast(json.dumps(payload), payload, immediate=True)


class EventBusWsBridge:
    """Мост между внутрипроцессной шиной EventBus и WebSocket клиентов."""

    def __init__(self, allowed_patterns: Optional[List[str]] = None, allow_core: bool = False):
        self.allowed_patterns = allowed_patterns if allowed_patterns is not None else ["#"]
        self.allow_core = allow_core
        self._subscribed = False

    def setup(self):
        if self._subscribed:
            return
        from backend.core.bus import event_bus
        for pattern in self.allowed_patterns:
            event_bus.subscribe(pattern, self.on_bus_event)
        self._subscribed = True

    def on_bus_event(self, topic: str, payload: Any):
        if topic.startswith("core.") and not self.allow_core:
            return
        ws_payload = {
            "type": "bus_event",
            "topic": topic,
            "payload": payload,
        }
        broadcaster.broadcast(data_dict=ws_payload, topic=topic, immediate=True)


bus_ws_bridge = EventBusWsBridge()


def __getattr__(name: str):
    if name == "router":
        from backend.api.events import router
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
