# Субмодуль Cesbo Astra — бэкенд стриминга
# Запускает процесс Astra с Lua-конфигурацией и проксирует данные через очередь.
import asyncio
import logging
import os
import tempfile
import uuid
import socket
import aiohttp
from typing import Dict, Optional, List

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, OutputType
)

logger = logging.getLogger(__name__)


class AstraSession:
    """Сессия одного канала Astra.

    Управляет списком подписчиков (клиентов),
    раздавая им чанки MPEG-TS через asyncio.Queue.
    """

    def __init__(self, task_id: str, task: StreamTask):
        self.task_id = task_id
        self.task = task
        self._subscribers: List[asyncio.Queue] = []

    # ── Подписка / Отписка ──────────────────────────────────────────────

    def subscribe(self) -> asyncio.Queue:
        """Создаёт персональную очередь для нового зрителя."""
        q = asyncio.Queue(maxsize=500)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """Убирает зрителя из рассылки."""
        if q in self._subscribers:
            self._subscribers.remove(q)

    # ── Рассылка данных ─────────────────────────────────────────────────

    def dispatch(self, chunk: bytes):
        """Рассылает чанк всем подписчикам (drop-oldest при переполнении)."""
        for q in self._subscribers:
            try:
                if q.full():
                    q.get_nowait()
                q.put_nowait(chunk)
            except Exception:
                pass

    # ── Завершение ──────────────────────────────────────────────────────

    def close(self):
        """Шлёт None (сигнал конца потока) и очищает список."""
        for q in self._subscribers:
            try:
                q.put_nowait(None)
            except Exception:
                pass
        self._subscribers.clear()


class AstraStreamer:
    """Управление процессами Astra 4.4.

    Для каждого запроса:
    1. Генерирует Lua-скрипт (make_channel).
    2. Запускает `astra --stream script.lua`.
    3. Подключается к HTTP-выходу Astra и перекидывает байты
       в AstraSession, откуда их забирает API через proxy_queue.
    """

    def __init__(self, settings: dict):
        self._settings = settings
        self.binary_path: str = settings.get(
            "binary_path",
            "/opt/Cesbo-Astra-4.4.-monitor/astra4.4.182",
        )
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._temp_files: Dict[str, str] = {}
        self._sessions: Dict[str, AstraSession] = {}
        self._bridges: Dict[str, asyncio.Task] = {}

    # ── Вспомогательные ─────────────────────────────────────────────────

    @staticmethod
    def _get_free_port() -> int:
        """Возвращает свободный порт на localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def _build_lua(self, task_id: str, task: StreamTask, port: int) -> str:
        """Генерация Lua-конфигурации по документации Astra 4.4.

        Формат (https://cdn.cesbo.com/astra/4.4.182-free):
            make_channel({
              name = "...",
              input = { "module://address#options" },
              output = { "http://0:PORT/PATH#keep_active=N" },
            })
        """
        keep_active = self._settings.get("http_keep_active", 0)
        buf_size = self._settings.get("http_buffer_size", 1024)
        buf_fill = self._settings.get("http_buffer_fill", 256)

        # Формируем параметры HTTP Output (документация → HTTP Output Options)
        output_opts = f"keep_active={keep_active}"
        output_opts += f"&buffer_size={buf_size}"
        output_opts += f"&buffer_fill={buf_fill}"

        output_url = f"http://0:{port}/{task_id}#{output_opts}"

        return (
            f'make_channel({{\n'
            f'  name = "{task_id}",\n'
            f'  input = {{ "{task.input_url}" }},\n'
            f'  output = {{ "{output_url}" }},\n'
            f'}})'
        )

    # ── Жизненный цикл потока ───────────────────────────────────────────

    async def start(self, task: StreamTask) -> StreamResult:
        """Запуск канала Astra."""
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            port = self._get_free_port()

            # 1. Lua-скрипт
            lua = self._build_lua(task_id, task, port)
            fd, lua_path = tempfile.mkstemp(
                prefix=f"astra_{task_id}_", suffix=".lua"
            )
            with os.fdopen(fd, "w") as f:
                f.write(lua)
            self._temp_files[task_id] = lua_path

            # 2. Запуск процесса
            logger.info(
                f"Astra [{task_id}] start: port={port} "
                f"input={task.input_url}"
            )
            process = await asyncio.create_subprocess_exec(
                self.binary_path, "--stream", lua_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            self._processes[task_id] = process

            # 3. Сессия + мост
            session = AstraSession(task_id, task)
            self._sessions[task_id] = session

            internal_url = f"http://127.0.0.1:{port}/{task_id}"
            self._bridges[task_id] = asyncio.create_task(
                self._run_bridge(task_id, internal_url, session)
            )

            # Возвращаем путь к прокси-эндпоинту API
            return StreamResult(
                task_id=task_id,
                success=True,
                backend_used="astra",
                output_url=f"/api/modules/stream/v1/proxy/{task_id}",
            )

        except Exception as e:
            logger.error(f"Astra [{task_id}] start error: {e}")
            return StreamResult(
                task_id=task_id, success=False,
                backend_used="astra", error=str(e),
            )

    async def stop(self, task_id: str) -> bool:
        """Остановка канала: отмена моста, убийство процесса, очистка."""
        bridge = self._bridges.pop(task_id, None)
        if bridge:
            bridge.cancel()

        session = self._sessions.pop(task_id, None)
        if session:
            session.close()

        process = self._processes.pop(task_id, None)
        if process:
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass

        lua_path = self._temp_files.pop(task_id, None)
        if lua_path and os.path.exists(lua_path):
            try:
                os.remove(lua_path)
            except Exception:
                pass

        return True

    # ── Мост: Astra HTTP → asyncio.Queue ────────────────────────────────

    async def _run_bridge(
        self,
        task_id: str,
        url: str,
        session: AstraSession,
    ):
        """Фоновая задача: читает MPEG-TS из Astra и рассылает подписчикам."""
        # Даём Astra время поднять HTTP-сервер
        await asyncio.sleep(1.5)

        connector = aiohttp.TCPConnector(force_close=True)
        timeout = aiohttp.ClientTimeout(
            total=None, connect=5, sock_read=60,
        )

        try:
            async with aiohttp.ClientSession(
                timeout=timeout, connector=connector
            ) as client:
                async with client.get(url) as resp:
                    if resp.status != 200:
                        logger.error(
                            f"Astra [{task_id}] bridge: HTTP {resp.status}"
                        )
                        return

                    logger.info(f"Astra [{task_id}] bridge connected")
                    async for chunk, _ in resp.content.iter_chunks():
                        session.dispatch(chunk)
                        # Если процесс уже убит — выходим
                        if task_id not in self._processes:
                            break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Astra [{task_id}] bridge ended: {e}")
        finally:
            session.close()

    # ── Публичный контракт (вызывается из __init__.py) ──────────────────

    def get_session(self, task_id: str) -> Optional[AstraSession]:
        return self._sessions.get(task_id)

    def get_process(
        self, task_id: str
    ) -> Optional[asyncio.subprocess.Process]:
        return self._processes.get(task_id)

    def get_active_count(self) -> int:
        return len(self._processes)
