# Бэкенд TSDuck — стриминг через процесс tsp.
# Запускает tsp с плагинами ввода/вывода.
# Для HTTP: читает MPEG-TS из stdout и раздаёт подписчикам.
# Для HLS: использует плагин -O hls для записи сегментов в data/streams/hls_{id}.
# Плейлист генерируется динамически через API (как в VLC/FFmpeg).
import asyncio
import logging
import os
import shutil
import time
from typing import Dict, Optional, List
from urllib.parse import urlparse

from backend.modules.stream.core.interfaces import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    BufferedSession,
)

logger = logging.getLogger(__name__)


class TSDuckSession(BufferedSession):
    """Сессия TSDuck-стрима.
    
    Поддерживает сканирование нативных сегментов TSDuck для генерации плейлиста в API.
    """

    @property
    def native_segments(self) -> List[str]:
        """Сканирует директорию на наличие сегментов TSDuck (seg-000000.ts)."""
        if not self.buffer_dir or not os.path.exists(self.buffer_dir):
            return []
        try:
            # TSDuck создает файлы вида seg-000000.ts, seg-000001.ts...
            files = [f for f in os.listdir(self.buffer_dir) if f.endswith(".ts")]
            files.sort()
            # В TSDuck/VLC принято отдавать все готовые сегменты
            return files[:-1] if len(files) > 0 else []
        except Exception as e:
            logger.error(f"TSDuckSession [{self.task_id}]: ошибка сканирования сегментов: {e}")
            return []

    def get_segments_for_output(self) -> List[str]:
        """Возвращает список сегментов для генератора плейлиста."""
        if self.task.output_type == OutputType.HLS:
            return self.native_segments
        return list(self.segments)


class TSDuckStreamer:
    """Управление процессами tsp."""

    def __init__(self, settings: dict):
        self._settings = settings
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._sessions: Dict[str, TSDuckSession] = {}
        self._bridges: Dict[str, asyncio.Task] = {}
        self._base_data_dir = os.path.abspath("data/streams")

    def _get_setting(self, key: str, default=None):
        return self._settings.get(key, default)

    def _build_tsp_command(self, task: StreamTask, buffer_dir: str) -> list:
        tsp_path = self._get_setting("binary_path", "tsp")
        buffer_mb = self._get_setting("buffer_size_mb", 16)

        cmd = [tsp_path, "--buffer-size-mb", str(buffer_mb)]

        # Входной плагин
        input_plugin, input_args = self._build_input_plugin(task)
        cmd.extend(["-I", input_plugin] + input_args)

        # Выходной плагин
        if task.output_type == OutputType.HLS:
            # -O hls seg.ts --live 5
            # Плейлист НЕ генерируем средствами TSDuck, его сгенерирует API
            segment_template = os.path.join(buffer_dir, "seg-00000001.ts")
            cmd.extend([
                "-O", "hls", segment_template,
                "--live", "5",
                "--intra-close",
                "--duration", "5",
                "--align-first-segment"
            ])
        else:
            # Стандартный выход в stdout для HTTP
            cmd.extend(["-O", "file"])

        return cmd

    def _build_input_plugin(self, task: StreamTask) -> tuple:
        url = task.input_url
        protocol = task.input_protocol
        parsed = urlparse(url)
        timeout = self._get_setting("receive_timeout", 5000)

        if protocol in (StreamProtocol.UDP, StreamProtocol.RTP):
            host = parsed.hostname or ""
            port = parsed.port or 1234
            addr = f"{host}:{port}" if host else str(port)
            args = [addr, "--receive-timeout", str(timeout)]
            return "ip", args

        if protocol == StreamProtocol.RIST:
            rist_url = url
            if rist_url.startswith("rist://") and "@" not in rist_url:
                rist_url = rist_url.replace("rist://", "rist://@")
            rist_buffer = self._get_setting("rist_buffer_size", 10000)
            rist_profile = self._get_setting("rist_profile", "simple")
            args = [rist_url, "--buffer-size", str(rist_buffer), "--profile", rist_profile]
            return "rist", args

        if protocol == StreamProtocol.SRT:
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 8890
            srt_mode = self._get_setting("srt_mode", "caller")
            srt_latency = self._get_setting("srt_latency", 120)
            args = [f"--{srt_mode}", f"{host}:{port}", "--latency", str(srt_latency)]
            if parsed.query:
                for param in parsed.query.split("&"):
                    if param.startswith("streamid="):
                        args.extend(["--streamid", param.split("=", 1)[1]])
            return "srt", args

        if protocol == StreamProtocol.HTTP:
            return "http", [url, "--connection-timeout", str(timeout)]

        if protocol == StreamProtocol.HLS:
            return "hls", [url]

        return "http", [url]

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id
        buffer_dir = os.path.join(self._base_data_dir, f"hls_{task_id}")
        
        if not os.path.exists(self._base_data_dir):
            os.makedirs(self._base_data_dir, exist_ok=True)
            
        if os.path.exists(buffer_dir):
            shutil.rmtree(buffer_dir)
        os.makedirs(buffer_dir, exist_ok=True)

        try:
            cmd = self._build_tsp_command(task, buffer_dir)
            logger.info(f"TSDuck [{task_id}]: запуск {' '.join(cmd)}")

            session = TSDuckSession(task_id, task, buffer_dir)
            self._sessions[task_id] = session

            stdout_action = asyncio.subprocess.PIPE if task.output_type == OutputType.HTTP else asyncio.subprocess.DEVNULL
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=stdout_action,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[task_id] = process

            asyncio.create_task(self._log_stderr(task_id, process))

            if task.output_type == OutputType.HTTP:
                self._bridges[task_id] = asyncio.create_task(
                    self._run_bridge(task_id, process, session)
                )

            # Формируем прямой URL в зависимости от типа (как в VLC)
            if task.output_type == OutputType.HLS:
                output_url = f"/api/modules/stream/v1/proxy/{task_id}/index.m3u8"
            elif task.output_type == OutputType.HTTP_TS:
                output_url = f"/api/modules/stream/v1/play/{task_id}"
            else:
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
            await self.stop(task_id)
            raise

    async def stop(self, task_id: str) -> bool:
        process = self._processes.pop(task_id, None)
        bridge = self._bridges.pop(task_id, None)
        session = self._sessions.pop(task_id, None)

        if bridge:
            bridge.cancel()
        if process:
            try:
                if process.returncode is None:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=2.0)
            except Exception:
                if process and process.returncode is None:
                    process.kill()
        if session:
            session.close()
            # Очистка папки с сегментами
            if os.path.exists(session.buffer_dir):
                shutil.rmtree(session.buffer_dir, ignore_errors=True)

        logger.info(f"TSDuck [{task_id}]: остановлен")
        return True

    async def _run_bridge(self, task_id: str, process: asyncio.subprocess.Process, session: TSDuckSession):
        try:
            while task_id in self._processes:
                chunk = await process.stdout.read(65536)
                if not chunk:
                    break
                await session.process_chunk(chunk)
        except Exception as e:
            logger.error(f"TSDuck [{task_id}]: ошибка моста {e}")
        finally:
            session.close()

    async def _log_stderr(self, task_id: str, process: asyncio.subprocess.Process):
        try:
            while True:
                line = await process.stderr.readline()
                if not line: break
                text = line.decode("utf-8", errors="replace").strip()
                if text: logger.info(f"TSDuck [{task_id}] stderr: {text}")
        except Exception: pass

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        session = self._sessions.get(task_id)
        if not session: return None

        if session.task.output_type == OutputType.HTTP:
            q = session.subscribe()
            return {
                "type": "proxy_queue",
                "content_type": "video/mp2t",
                "queue": q,
                "unsubscribe": lambda: session.unsubscribe(q),
            }
        
        elif session.task.output_type == OutputType.HLS:
            # Тип hls_playlist заставляет API использовать эндпоинт /proxy/{id}/index.m3u8
            # который динамически генерирует плейлист на основе session.get_segments_for_output()
            return {
                "type": "hls_playlist",
                "playlist_url": f"/api/modules/stream/v1/proxy/{task_id}/index.m3u8",
                "buffer_dir": session.buffer_dir,
                "segments": session.get_segments_for_output(),
                "segment_duration": 5,
            }
        return None

    def get_session(self, task_id: str) -> Optional[TSDuckSession]:
        return self._sessions.get(task_id)

    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]:
        return self._processes.get(task_id)

    def get_active_count(self) -> int:
        return len(self._processes)

    def get_temp_dirs(self, task_id: str) -> list:
        session = self._sessions.get(task_id)
        return [session.buffer_dir] if session else []
