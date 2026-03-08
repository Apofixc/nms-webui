# Бэкенд GStreamer — стриминг через gst-launch-1.0.
# Для HTTP: читает MPEG-TS из stdout (fdsink fd=1) и раздаёт подписчикам.
# Для HLS: использует hlssink2 для записи сегментов и плейлиста.
import asyncio
import logging
import os
import shlex
import shutil
import time
from typing import Dict, Optional, List
from urllib.parse import urlparse

from backend.modules.stream.core.interfaces import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    BufferedSession,
)

logger = logging.getLogger(__name__)


class GStreamerSession(BufferedSession):
    """Сессия GStreamer-стрима.

    Для HLS: сканирует нативные сегменты hlssink на диске.
    Для HTTP: использует BufferedSession для pub/sub через мост stdout.
    """

    @property
    def native_segments(self) -> List[str]:
        """Сканирует директорию на наличие сегментов hlssink."""
        if not self.buffer_dir or not os.path.exists(self.buffer_dir):
            return []
        try:
            files = [f for f in os.listdir(self.buffer_dir) if f.endswith(".ts")]
            files.sort()
            # Убираем последний сегмент — он может быть в процессе записи
            return files[:-1] if len(files) > 0 else []
        except Exception as e:
            logger.error(f"GStreamerSession [{self.task_id}]: ошибка сканирования сегментов: {e}")
            return []

    def get_segments_for_output(self) -> List[str]:
        """Возвращает список сегментов для генератора плейлиста."""
        if self.task.output_type == OutputType.HLS:
            return self.native_segments
        return list(self.segments)


class GStreamerStreamer:
    """Управление процессами gst-launch-1.0."""

    def __init__(self, settings: dict):
        self._settings = settings
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._sessions: Dict[str, GStreamerSession] = {}
        self._bridges: Dict[str, asyncio.Task] = {}
        self._base_data_dir = os.path.abspath("data/streams")

    def _get_setting(self, key: str, default=None):
        return self._settings.get(key, default)

    # ── Построение пайплайна ─────────────────────────────────────────

    def _build_pipeline(self, task: StreamTask, buffer_dir: str) -> list:
        """Формирует список аргументов пайплайна GStreamer."""
        input_part = self._build_input(task)
        output_part = self._build_output(task, buffer_dir)
        
        # Если в input_part уже есть плейсхолдер __OUTPUT__, заменяем его
        if "__OUTPUT__" in input_part:
            pipeline_str = input_part.replace("__OUTPUT__", output_part)
        else:
            pipeline_str = f"{input_part} ! {output_part}"
            
        # gst-launch-1.0 принимает элементы пайплайна как отдельные аргументы
        return shlex.split(pipeline_str)

    def _build_input(self, task: StreamTask) -> str:
        """Формирует входную часть пайплайна."""
        url = task.input_url
        protocol = task.input_protocol
        parsed = urlparse(url)

        if protocol == StreamProtocol.UDP:
            host = parsed.hostname or "0.0.0.0"
            port = parsed.port or 1234
            multicast = ""
            if host and not host.startswith("0."):
                multicast = f"address={host} "
            return f"udpsrc {multicast}port={port} ! tsparse"

        if protocol == StreamProtocol.RTP:
            host = parsed.hostname or "0.0.0.0"
            port = parsed.port or 1234
            multicast = ""
            if host and not host.startswith("0."):
                multicast = f"address={host} "
            # Для RTP предполагаем MPEG-TS depayloader
            return (
                f"udpsrc {multicast}port={port} "
                f"caps=\"application/x-rtp,media=(string)video,payload=(int)33\" "
                f"! rtpmp2tdepay ! tsparse"
            )

        if protocol == StreamProtocol.RIST:
            host = parsed.hostname or "0.0.0.0"
            port = parsed.port or self._get_setting("rist_port", 5004)
            return (
                f"ristsrc address={host} port={port} "
                f"! rtpmp2tdepay ! tsparse"
            )

        if protocol == StreamProtocol.SRT:
            srt_mode = self._get_setting("srt_mode", "caller")
            srt_latency = self._get_setting("srt_latency", 125)
            return (
                f"srtsrc uri=\"{url}\" mode={srt_mode} latency={srt_latency} "
                f"! tsparse"
            )

        if protocol == StreamProtocol.TCP:
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 1234
            return f"tcpclientsrc host={host} port={port} ! tsparse"


        if protocol in (StreamProtocol.RTMP, StreamProtocol.RTMPS, StreamProtocol.RTSP, StreamProtocol.HLS):
            # uridecodebin универсален и стабилен для сложных протоколов.
            # Обход бага в rtmp2src (GStreamer 1.24): если путь (app) состоит из 1 сегмента без слеша на конце (например, /test),
            # возникает ошибка "Host is not set". Добавление завершающего слеша исправляет парсинг.
            decode_url = url
            if protocol in (StreamProtocol.RTMP, StreamProtocol.RTMPS) and not url.endswith("/"):
                if parsed.path.count("/") == 1:
                    decode_url += "/"
                    
            return (
                f"uridecodebin uri=\"{decode_url}\" name=dec "
                f"mpegtsmux name=mux ! tsparse ! __OUTPUT__ "
                f"dec. ! queue ! videoconvert ! x264enc tune=zerolatency bitrate=2000 ! h264parse ! mux. "
                f"dec. ! queue ! audioconvert ! avenc_aac ! aacparse ! mux."
            )

        # HTTP: по умолчанию предполагаем MPEG-TS
        return f"souphttpsrc location=\"{url}\" ! tsparse"

    def _needs_remux(self, protocol: StreamProtocol) -> bool:
        """Определяет, нужен ли mpegtsmux перед выводом.
        
        TS-потоки (UDP/RTP/RIST/SRT/HTTP) уже в формате MPEG-TS после tsparse.
        RTSP и RTMP выдают элементарные потоки — их нужно мультиплексировать.
        """
        return protocol in (StreamProtocol.RTSP, StreamProtocol.RTMP)

    def _build_output(self, task: StreamTask, buffer_dir: str) -> str:
        """Формирует выходную часть пайплайна."""
        if task.output_type == OutputType.HLS:
            target_duration = self._get_setting("hls_target_duration", 5)
            max_files = self._get_setting("hls_max_files", 10)
            playlist_path = os.path.join(buffer_dir, "playlist.m3u8")
            segment_path = os.path.join(buffer_dir, "seg-%05d.ts")
            # hlssink принимает muxed TS на входе.
            return (
                f"hlssink location={segment_path} "
                f"playlist-location={playlist_path} "
                f"target-duration={target_duration} "
                f"max-files={max_files}"
            )
        else:
            # HTTP: вывод в stdout.
            return "fdsink fd=1"

    # ── Жизненный цикл потока ────────────────────────────────────────

    async def start(self, task: StreamTask) -> StreamResult:
        """Запуск трансляции GStreamer."""
        task_id = task.task_id
        buffer_dir = os.path.join(self._base_data_dir, f"hls_{task_id}")

        if not os.path.exists(self._base_data_dir):
            os.makedirs(self._base_data_dir, exist_ok=True)

        if task.output_type == OutputType.HLS:
            if os.path.exists(buffer_dir):
                shutil.rmtree(buffer_dir)
            os.makedirs(buffer_dir, exist_ok=True)

        gst_path = self._get_setting("binary_path", "gst-launch-1.0")

        try:
            pipeline_args = self._build_pipeline(task, buffer_dir)
            cmd = [gst_path, "-e", "-q"] + pipeline_args

            logger.info(f"GStreamer [{task_id}]: запуск {' '.join(cmd)}")

            # Создаем сессию
            session = GStreamerSession(
                task_id=task_id,
                task=task,
                buffer_dir=buffer_dir if task.output_type == OutputType.HLS else "",
                segment_duration=self._get_setting("hls_target_duration", 5),
                max_segments=self._get_setting("hls_max_files", 10),
            )
            self._sessions[task_id] = session

            # stdout нужен только для HTTP (fdsink fd=1)
            stdout_action = (
                asyncio.subprocess.PIPE
                if task.output_type != OutputType.HLS
                else asyncio.subprocess.DEVNULL
            )

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=stdout_action,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[task_id] = process

            # Фоновое чтение stderr
            asyncio.create_task(self._log_stderr(task_id, process))

            # Мост stdout → подписчики (только для HTTP)
            if task.output_type != OutputType.HLS:
                self._bridges[task_id] = asyncio.create_task(
                    self._run_bridge(task_id, process, session)
                )

            # Формируем URL для воспроизведения
            if task.output_type == OutputType.HLS:
                # HLS: API будет динамически генерировать index.m3u8 через proxy
                output_url = f"/api/modules/stream/v1/proxy/{task_id}/index.m3u8"
            else:
                output_url = f"/api/modules/stream/v1/proxy/{task_id}"

            return StreamResult(
                task_id=task_id,
                success=True,
                backend_used="gstreamer",
                output_type=task.output_type,
                output_url=output_url,
                process=process,
            )

        except Exception as e:
            logger.error(f"GStreamer [{task_id}]: ошибка запуска: {e}")
            await self.stop(task_id)
            raise

    async def stop(self, task_id: str) -> bool:
        """Остановка GStreamer: отмена моста, завершение процесса."""
        process = self._processes.pop(task_id, None)
        bridge = self._bridges.pop(task_id, None)
        session = self._sessions.pop(task_id, None)

        if bridge:
            bridge.cancel()
        if process:
            try:
                if process.returncode is None:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=3.0)
            except Exception:
                if process and process.returncode is None:
                    process.kill()
        if session:
            session.close()

        logger.info(f"GStreamer [{task_id}]: остановлен")
        return True

    # ── Мост: stdout → подписчики ────────────────────────────────────

    async def _run_bridge(
        self, task_id: str,
        process: asyncio.subprocess.Process,
        session: GStreamerSession
    ):
        """Фоновая задача: читает MPEG-TS из stdout и рассылает подписчикам."""
        try:
            # Таймаут на первые данные
            first_chunk_timeout = 15.0
            try:
                chunk = await asyncio.wait_for(
                    process.stdout.read(65536), timeout=first_chunk_timeout
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"GStreamer [{task_id}]: нет данных {first_chunk_timeout}с — "
                    f"источник не отвечает"
                )
                return

            if not chunk:
                logger.warning(f"GStreamer [{task_id}]: stdout закрыт без данных")
                return

            await session.process_chunk(chunk)
            logger.info(f"GStreamer [{task_id}]: мост подключён")

            # Основной цикл чтения
            while task_id in self._processes:
                chunk = await process.stdout.read(65536)
                if not chunk:
                    break
                await session.process_chunk(chunk)

            logger.debug(f"GStreamer [{task_id}]: мост завершён")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"GStreamer [{task_id}]: ошибка моста {e}")
        finally:
            session.close()

    async def _log_stderr(self, task_id: str, process: asyncio.subprocess.Process):
        """Фоновое чтение stderr для логирования ошибок GStreamer."""
        try:
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if text:
                    logger.info(f"GStreamer [{task_id}] stderr: {text}")
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    # ── Публичный контракт ───────────────────────────────────────────

    def get_session(self, task_id: str) -> Optional[GStreamerSession]:
        """Получить активную сессию по ID."""
        return self._sessions.get(task_id)

    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]:
        """Получить процесс gst-launch-1.0 по ID задачи."""
        return self._processes.get(task_id)

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        """Информация о воспроизведении для клиента."""
        session = self._sessions.get(task_id)
        if not session:
            return None

        if session.task.output_type == OutputType.HTTP:
            q = session.subscribe()
            return {
                "type": "proxy_queue",
                "content_type": "video/mp2t",
                "queue": q,
                "unsubscribe": lambda: session.unsubscribe(q),
            }
        elif session.task.output_type == OutputType.HLS:
            return {
                "type": "hls_playlist",
                "playlist_url": (
                    f"/api/modules/stream/v1/proxy/{task_id}/index.m3u8"
                ),
                "buffer_dir": session.buffer_dir,
                "segments": session.get_segments_for_output(),
                "segment_duration": self._get_setting("hls_target_duration", 5),
            }
        return None

    def get_active_count(self) -> int:
        """Количество активных процессов GStreamer."""
        return len(self._processes)

    def get_temp_dirs(self, task_id: str) -> list:
        """Возвращает временные директории сессии."""
        session = self._sessions.get(task_id)
        return [session.buffer_dir] if session and session.buffer_dir else []
