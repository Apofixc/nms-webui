# Бэкенд Cesbo Astra — стриминг через Lua-конфигурацию.
# Запускает процесс Astra с Lua-скриптом,
# проксирует данные через HTTP-мост в AstraSession.
import asyncio
import logging
import os
import tempfile
import uuid
import socket
import aiohttp
from typing import Dict, Optional

from backend.modules.stream.core.interfaces import (
    StreamTask, StreamResult, BaseStreamSession,
)

logger = logging.getLogger(__name__)


class AstraSession(BaseStreamSession):
    """Сессия одного канала Astra.

    Наследует BaseStreamSession — общую логику TS-синхронизации,
    pub/sub для подписчиков.
    
    Astra не использует дисковую буферизацию,
    раздаёт чанки MPEG-TS через asyncio.Queue.
    """
    pass


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
            "/opt/astra/astra4.4.182",
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
        """Генерация Lua-конфигурации по документации Astra 4.4."""
        keep_active = self._settings.get("http_keep_active", 0)
        buf_size = self._settings.get("http_buffer_size", 1024)
        buf_fill = self._settings.get("http_buffer_fill", 256)

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
                f"Astra [{task_id}]: запуск port={port} "
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
            logger.error(f"Astra [{task_id}]: ошибка запуска {e}")
            return StreamResult(
                task_id=task_id, success=False,
                backend_used="astra", error=str(e),
            )

    async def stop(self, task_id: str) -> bool:
        """Остановка канала: отмена моста, убийство процесса.
        
        ВАЖНО: Lua-файлы теперь не удаляются здесь.
        Очисткой управляет модуль Stream через get_temp_dirs().
        """
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

        timeout = aiohttp.ClientTimeout(
            total=None, connect=5, sock_read=60,
        )

        try:
            async with aiohttp.ClientSession(timeout=timeout) as client:
                async with client.get(url) as resp:
                    if resp.status != 200:
                        logger.error(
                            f"Astra [{task_id}]: мост HTTP {resp.status}"
                        )
                        return

                    logger.info(f"Astra [{task_id}]: мост подключён")

                    source = resp.content.iter_chunks()
                    async for chunk_data in source:
                        if task_id not in self._processes:
                            break
                        chunk = (
                            chunk_data[0]
                            if isinstance(chunk_data, tuple)
                            else chunk_data
                        )
                        await session.process_chunk(chunk)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Astra [{task_id}]: мост завершён: {e}")
        finally:
            session.close()

    # ── Публичный контракт ──────────────────────────────────────────────

    def get_session(self, task_id: str) -> Optional[AstraSession]:
        """Получить активную сессию по ID."""
        return self._sessions.get(task_id)

    def get_process(
        self, task_id: str
    ) -> Optional[asyncio.subprocess.Process]:
        """Получить процесс Astra по ID задачи."""
        return self._processes.get(task_id)

    def get_active_count(self) -> int:
        """Количество активных процессов Astra."""
        return len(self._processes)
