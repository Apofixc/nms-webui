# Бэкенд TSDuck — стриминг через процесс tsp.
# Запускает tsp с плагинами ввода/вывода, читает MPEG-TS из stdout (pipe),
# раздаёт данные подписчикам через TSDuckSession.
import asyncio
import logging
import os
import time
from typing import Dict, Optional
from urllib.parse import urlparse

from backend.modules.stream.core.interfaces import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    BufferedSession,
)

logger = logging.getLogger(__name__)


class TSDuckSession(BufferedSession):
    """Сессия TSDuck-стрима с поддержкой буферизации.

    Наследует BufferedSession — общую логику TS-синхронизации,
    pub/sub и сегментированной записи на диск.
    """
    pass


class TSDuckStreamer:
    """Управление процессами tsp.

    Для каждого запроса:
    1. Определяет входной плагин по протоколу.
    2. Запускает tsp с выходом в stdout (-O file без аргументов).
    3. Читает stdout и перекидывает байты в TSDuckSession,
       откуда их забирает API через proxy_queue или proxy_buffer.
    """

    def __init__(self, settings: dict):
        self._settings = settings
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._sessions: Dict[str, TSDuckSession] = {}
        self._bridges: Dict[str, asyncio.Task] = {}

    # ── Вспомогательные ─────────────────────────────────────────────────

    def _get_setting(self, key: str, default=None):
        """Получение настройки из конфига бэкенда."""
        return self._settings.get(key, default)

    def _build_tsp_command(self, task: StreamTask) -> list:
        """Формирование полной команды tsp с плагинами.

        Структура: tsp [general-opts] -I <plugin> [input-opts] -O file
        Выход в stdout — через '-O file' без имени файла.
        """
        tsp_path = self._get_setting("binary_path", "tsp")
        buffer_mb = self._get_setting("buffer_size_mb", 16)

        # Общие опции tsp
        cmd = [tsp_path, "--buffer-size-mb", str(buffer_mb)]

        # Входной плагин и его аргументы
        input_plugin, input_args = self._build_input_plugin(task)
        cmd.extend(["-I", input_plugin] + input_args)

        # Выход в stdout
        cmd.extend(["-O", "file"])

        return cmd

    def _build_input_plugin(self, task: StreamTask) -> tuple:
        """Определение входного плагина и аргументов по протоколу.

        Returns:
            Кортеж (имя_плагина, [аргументы]).
        """
        url = task.input_url
        protocol = task.input_protocol
        parsed = urlparse(url)
        timeout = self._get_setting("receive_timeout", 5000)

        # UDP / RTP → плагин 'ip'
        if protocol in (StreamProtocol.UDP, StreamProtocol.RTP):
            # tsp -I ip [address:]port
            host = parsed.hostname or ""
            port = parsed.port or 1234
            if host:
                addr = f"{host}:{port}"
            else:
                addr = str(port)
            args = [addr, "--receive-timeout", str(timeout)]
            return "ip", args

        # RIST → плагин 'rist'
        if protocol == StreamProtocol.RIST:
            # tsp -I rist rist://@host:port
            rist_url = url
            if rist_url.startswith("rist://") and "@" not in rist_url:
                rist_url = rist_url.replace("rist://", "rist://@")
            rist_buffer = self._get_setting("rist_buffer_size", 1000)
            rist_profile = self._get_setting("rist_profile", "simple")
            args = [rist_url, "--buffer-size", str(rist_buffer), "--profile", rist_profile]
            return "rist", args

        # SRT → плагин 'srt'
        if protocol == StreamProtocol.SRT:
            # tsp -I srt --caller host:port
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 8890
            srt_mode = self._get_setting("srt_mode", "caller")
            srt_latency = self._get_setting("srt_latency", 120)
            args = [f"--{srt_mode}", f"{host}:{port}"]
            args.extend(["--latency", str(srt_latency)])
            # Передача streamid из query-параметров
            if parsed.query:
                for param in parsed.query.split("&"):
                    if param.startswith("streamid="):
                        args.extend(["--streamid", param.split("=", 1)[1]])
            return "srt", args

        # HTTP → плагин 'http'
        if protocol == StreamProtocol.HTTP:
            args = [url, "--connection-timeout", str(timeout)]
            return "http", args

        # HLS → плагин 'hls'
        if protocol == StreamProtocol.HLS:
            args = [url]
            return "hls", args

        # Fallback: пробуем как http
        logger.warning(
            f"TSDuck: неизвестный протокол {protocol.value}, "
            f"пробуем как HTTP"
        )
        args = [url]
        return "http", args

    # ── Жизненный цикл потока ───────────────────────────────────────────

    async def start(self, task: StreamTask) -> StreamResult:
        """Запуск процесса tsp и моста чтения."""
        task_id = task.task_id
        session = None
        process = None

        try:
            cmd = self._build_tsp_command(task)
            logger.info(f"TSDuck [{task_id}]: запуск {' '.join(cmd)}")

            # 1. Создаем сессию (BufferedSession для сегментации на диск)
            buffer_dir = f"/tmp/tsduck_buf_{task_id}"
            os.makedirs(buffer_dir, exist_ok=True)
            session = TSDuckSession(task_id, task, buffer_dir)
            self._sessions[task_id] = session

            # 2. Запускаем процесс tsp
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[task_id] = process

            # 3. Запускаем логирование и мост
            asyncio.create_task(self._log_stderr(task_id, process))
            self._bridges[task_id] = asyncio.create_task(
                self._run_bridge(task_id, process, session)
            )

            # 4. Формируем результат (backend_used="tsduck" и success=True)
            output_url = f"/api/modules/stream/v1/proxy/{task_id}"
            return StreamResult(
                task_id=task_id,
                success=True,
                backend_used="tsduck",
                output_type=task.output_type,
                output_url=output_url,
                process=process
            )

        except Exception as e:
            logger.error(f"TSDuck [{task_id}]: ошибка запуска: {e}")
            if task_id in self._processes or process:
                await self.stop(task_id)
            elif session:
                session.close()
                self._sessions.pop(task_id, None)
            raise

    async def stop(self, task_id: str) -> bool:
        """Остановка процесса и очистка ресурсов."""
        process = self._processes.pop(task_id, None)
        bridge = self._bridges.pop(task_id, None)
        session = self._sessions.pop(task_id, None)

        if bridge:
            bridge.cancel()

        if process:
            try:
                if process.returncode is None:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=2.0)
                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()
            except ProcessLookupError:
                pass

        if session:
            session.close()

        logger.info(f"TSDuck [{task_id}]: остановлен")
        return True

    # ── Мост: tsp stdout → подписчики ──────────────────────────────────

    async def _run_bridge(
        self,
        task_id: str,
        process: asyncio.subprocess.Process,
        session: TSDuckSession,
    ):
        """Фоновая задача: читает MPEG-TS из stdout tsp и рассылает подписчикам."""
        try:
            # Таймаут на первые данные
            first_chunk_timeout = 15.0
            chunk = b""
            try:
                chunk = await asyncio.wait_for(
                    process.stdout.read(65536), timeout=first_chunk_timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"TSDuck [{task_id}]: нет данных {first_chunk_timeout}с")
                return

            if not chunk:
                logger.warning(f"TSDuck [{task_id}]: stdout закрыт без данных")
                return

            await session.process_chunk(chunk)
            logger.info(f"TSDuck [{task_id}]: мост подключён")

            # Основной цикл
            while task_id in self._processes:
                chunk = await process.stdout.read(65536)
                if not chunk:
                    break
                await session.process_chunk(chunk)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"TSDuck [{task_id}]: ошибка моста {e}")
        finally:
            session.close()

    async def _log_stderr(self, task_id: str, process: asyncio.subprocess.Process):
        """Фоновое чтение stderr tsp."""
        try:
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if text:
                    logger.info(f"TSDuck [{task_id}] stderr: {text}")
        except Exception:
            pass

    # ── Публичный контракт ──────────────────────────────────────────────

    def get_session(self, task_id: str) -> Optional[TSDuckSession]:
        return self._sessions.get(task_id)

    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]:
        return self._processes.get(task_id)

    def get_active_count(self) -> int:
        return len(self._processes)

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        """Информация о воспроизведении для API."""
        session = self._sessions.get(task_id)
        if not session:
            return None

        # Для обычного HTTP (рассылка через очереди)
        if session.task.output_type == OutputType.HTTP:
            q = session.subscribe()
            return {
                "type": "proxy_queue",
                "content_type": "video/mp2t",
                "queue": q,
                "unsubscribe": lambda: session.unsubscribe(q),
            }
        
        # Для HTTP_TS (рассылка через сегменты на диске)
        elif session.task.output_type == OutputType.HTTP_TS:
            return {
                "type": "proxy_buffer",
                "content_type": "video/mp2t",
                "buffer_dir": session.buffer_dir,
                "segments": list(session.segments),
                "segment_duration": session.segment_duration,
                "get_session": lambda: self._sessions.get(task_id),
            }

        return None
