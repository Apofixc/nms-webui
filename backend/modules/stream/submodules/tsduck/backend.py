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
       откуда их забирает API через proxy_queue.
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
            args = [rist_url, "--buffer-size", str(rist_buffer)]
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

        # RTSP → через http (fallback, tsp не имеет нативного RTSP)
        if protocol == StreamProtocol.RTSP:
            args = [url, "--connection-timeout", str(timeout)]
            return "http", args

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

        cmd = self._build_tsp_command(task)
        logger.info(f"TSDuck [{task_id}]: запуск {' '.join(cmd)}")

        # Сессия буферизации
        buffer_dir = f"/tmp/tsduck_buf_{task_id}"
        os.makedirs(buffer_dir, exist_ok=True)
        session = TSDuckSession(
            task_id=task_id,
            task=task,
            buffer_dir=buffer_dir,
        )
        self._sessions[task_id] = session

        try:
            # tsp пишет TS-пакеты в stdout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[task_id] = process

            # Фоновое чтение stderr для логирования
            asyncio.create_task(
                self._log_stderr(task_id, process)
            )

            # Мост: stdout → сессия
            self._bridges[task_id] = asyncio.create_task(
                self._run_bridge(task_id, process, session)
            )

            # URL для прокси-эндпоинта
            output_url = f"/api/modules/stream/v1/proxy/{task_id}"

            return StreamResult(
                task_id=task_id,
                output_url=output_url,
                output_type=task.output_type,
                backend_id="tsduck",
            )

        except Exception as e:
            logger.error(f"TSDuck [{task_id}]: ошибка запуска: {e}")
            self._cleanup(task_id)
            raise

    async def stop(self, task_id: str) -> bool:
        """Остановка процесса tsp."""
        process = self._processes.get(task_id)
        if not process:
            return False

        # Отменяем мост
        bridge = self._bridges.pop(task_id, None)
        if bridge:
            bridge.cancel()

        # Убиваем процесс
        try:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=3.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
        except ProcessLookupError:
            pass

        self._cleanup(task_id)
        logger.info(f"TSDuck [{task_id}]: остановлен")
        return True

    def _cleanup(self, task_id: str):
        """Очистка ресурсов после остановки."""
        self._processes.pop(task_id, None)
        session = self._sessions.pop(task_id, None)
        if session:
            session.close()

    # ── Мост: tsp stdout → подписчики ──────────────────────────────────

    async def _run_bridge(
        self,
        task_id: str,
        process: asyncio.subprocess.Process,
        session: TSDuckSession,
    ):
        """Фоновая задача: читает MPEG-TS из stdout tsp и рассылает подписчикам."""
        try:
            # Таймаут на первые данные (защита от зависания)
            first_chunk_timeout = 15.0
            try:
                chunk = await asyncio.wait_for(
                    process.stdout.read(65536), timeout=first_chunk_timeout
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"TSDuck [{task_id}]: нет данных {first_chunk_timeout}с — "
                    f"источник не отвечает"
                )
                return

            if not chunk:
                logger.warning(f"TSDuck [{task_id}]: stdout закрыт без данных")
                return

            await session.process_chunk(chunk)
            logger.info(f"TSDuck [{task_id}]: мост подключён")

            # Основной цикл чтения
            while task_id in self._processes:
                chunk = await process.stdout.read(65536)
                if not chunk:
                    break
                await session.process_chunk(chunk)

            logger.debug(f"TSDuck [{task_id}]: мост завершён")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"TSDuck [{task_id}]: ошибка моста {e}")
        finally:
            session.close()

    async def _log_stderr(self, task_id: str, process: asyncio.subprocess.Process):
        """Фоновое чтение stderr tsp для логирования ошибок."""
        try:
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if text:
                    logger.info(f"TSDuck [{task_id}] stderr: {text}")
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    # ── Публичный контракт ──────────────────────────────────────────────

    def get_session(self, task_id: str) -> Optional[TSDuckSession]:
        """Доступ к сессии по ID задачи."""
        return self._sessions.get(task_id)

    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]:
        """Доступ к процессу tsp по ID задачи."""
        return self._processes.get(task_id)

    def get_active_count(self) -> int:
        """Количество активных процессов tsp."""
        return len(self._processes)

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        """Информация о воспроизведении для API."""
        session = self._sessions.get(task_id)
        if not session:
            return None

        q, unsub = session.subscribe()
        return {
            "type": "proxy_queue",
            "queue": q,
            "unsubscribe": unsub,
            "content_type": "video/mp2t",
        }
