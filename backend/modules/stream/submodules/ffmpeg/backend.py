# Логика трансляции и конвертации через FFmpeg
import asyncio
import logging
import os
import shlex
import signal
import uuid
from typing import Dict, List, Optional, Set

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    BackendCapability
)

logger = logging.getLogger(__name__)


class FFmpegStreamer:
    """Управление процессами FFmpeg для стриминга.

    Поддерживает два режима:
    1. Автоматическая сборка команды из базовых параметров (для обычных пользователей).
    2. Override-шаблон: если задан override_{pipeline} — используется он (для продвинутых).
    """

    def __init__(self, settings: dict):
        self.binary_path = settings.get("binary_path", "ffmpeg")

        # Глобальные аргументы
        raw_args = settings.get("global_args", "-hide_banner -loglevel error")
        self.global_args = raw_args.split() if isinstance(raw_args, str) else (raw_args or [])

        # -- Сеть (Input) --
        self.rtsp_transport = settings.get("rtsp_transport", "tcp")
        self.udp_buffer_size = settings.get("udp_buffer_size", 1024)
        self.srt_latency = settings.get("srt_latency", 200)

        # -- HTTP_TS Pipeline --
        self.http_ts_codec = settings.get("http_ts_codec", "copy")

        # -- HLS Pipeline --
        self.hls_time = settings.get("hls_time", 5)
        self.hls_list_size = settings.get("hls_list_size", 5)
        self.hls_flags = settings.get("hls_flags", "delete_segments+append_list")
        self.hls_codec = settings.get("hls_codec", "copy")

        # -- WebRTC Pipeline --
        self.webrtc_video_codec = settings.get("webrtc_video_codec", "libx264")
        self.webrtc_video_profile = settings.get("webrtc_video_profile", "baseline")
        self.webrtc_video_bitrate = settings.get("webrtc_video_bitrate", 2000)
        self.webrtc_audio_codec = settings.get("webrtc_audio_codec", "opus")

        # -- Override-шаблоны --
        self.override_http_ts = settings.get("override_http_ts", "")
        self.override_hls = settings.get("override_hls", "")
        self.override_webrtc = settings.get("override_webrtc", "")

        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            cmd = self._build_command(task, task_id)
            logger.info(f"FFmpeg Stream [{task_id}]: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[task_id] = process

            # Даем минимальное время на запуск и проверяем, не умер ли процесс сразу (ошибка синтаксиса)
            await asyncio.sleep(0.3)

            if process.returncode is not None:
                stderr = await process.stderr.read()
                error_msg = stderr.decode(errors="replace")[-500:]
                return StreamResult(
                    task_id=task_id,
                    success=False,
                    backend_used="ffmpeg",
                    error=f"FFmpeg завершился с ошибкой: {error_msg}"
                )

            return StreamResult(
                task_id=task_id,
                success=True,
                backend_used="ffmpeg",
                output_url=f"/api/modules/stream/v1/play/{task_id}",
                metadata={"pid": process.pid, "args": cmd}
            )

        except Exception as e:
            logger.error(f"Ошибка запуска FFmpeg [{task_id}]: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id, success=False,
                backend_used="ffmpeg", error=str(e)
            )

    async def stop(self, task_id: str) -> bool:
        process = self._processes.pop(task_id, None)
        if not process:
            return False

        if process.returncode is None:
            try:
                process.send_signal(signal.SIGTERM)
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
            except ProcessLookupError:
                pass
        return True

    # ── Сборка команд ──────────────────────────────────────────────

    def _build_command(self, task: StreamTask, task_id: str) -> List[str]:
        """Формирование команды FFmpeg.

        Если для данного output_type задан override-шаблон — используем его.
        Иначе собираем команду из базовых параметров.
        """
        # Проверка override
        override = self._get_override(task.output_type, task, task_id)
        if override:
            return override

        cmd = [self.binary_path] + self.global_args

        # ── Input ──
        cmd.extend(self._input_args(task))

        # ── Output ──
        if task.output_type == OutputType.HLS:
            cmd.extend(self._output_hls(task_id))
        elif task.output_type == OutputType.WEBRTC:
            cmd.extend(self._output_webrtc(task_id))
        elif task.output_type in (OutputType.HTTP_TS, OutputType.HTTP):
            cmd.extend(self._output_http_ts(task_id, task.output_type))
        else:
            # По умолчанию MPEG-TS поток в stdout (HTTP)
            cmd.extend(self._output_http_ts(task_id, OutputType.HTTP))

        return cmd

    def _input_args(self, task: StreamTask) -> List[str]:
        """Аргументы входного потока в зависимости от протокола."""
        args: List[str] = []

        if task.input_protocol in (StreamProtocol.UDP, StreamProtocol.RTP):
            args.extend(["-thread_queue_size", str(self.udp_buffer_size), "-overrun_nonfatal", "1"])
        elif task.input_protocol == StreamProtocol.RTSP:
            args.extend(["-rtsp_transport", self.rtsp_transport])
        elif task.input_protocol == StreamProtocol.SRT:
            # Добавляем параметр задержки SRT, если он не вшит в URL
            url = task.input_url
            if "latency=" not in url:
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}latency={self.srt_latency * 1000}"  # SRT ожидает микросекунды
            args.extend(["-i", url])
            return args

        args.extend(["-i", task.input_url])
        return args

    def _output_hls(self, task_id: str) -> List[str]:
        """Выходные аргументы для HLS."""
        hls_dir = f"/tmp/stream_hls_{task_id}"
        os.makedirs(hls_dir, exist_ok=True)

        args = []
        if self.hls_codec == "copy":
            args.extend(["-c", "copy"])
        else:
            args.extend(["-c:v", self.hls_codec, "-c:a", "aac"])

        args.extend([
            "-f", "hls",
            "-hls_time", str(self.hls_time),
            "-hls_list_size", str(self.hls_list_size),
            "-hls_flags", self.hls_flags,
            f"{hls_dir}/playlist.m3u8"
        ])
        return args

    def _output_webrtc(self, task_id: str) -> List[str]:
        """Выходные аргументы для WebRTC (транскодинг в RTP)."""
        rtp_port = 10000 + hash(task_id) % 5000

        args = [
            "-c:v", self.webrtc_video_codec,
            "-b:v", f"{self.webrtc_video_bitrate}k",
        ]

        # Профиль H264 (профиль актуален только для libx264)
        if self.webrtc_video_codec == "libx264":
            args.extend(["-profile:v", self.webrtc_video_profile, "-level", "3.1"])

        args.extend([
            "-pix_fmt", "yuv420p",
            "-c:a", self.webrtc_audio_codec,
            "-f", "rtp",
            f"rtp://127.0.0.1:{rtp_port}"
        ])
        return args

    def _output_http_ts(self, task_id: str, output_type: OutputType) -> List[str]:
        """Выходные аргументы для HTTP (MPEG-TS)."""
        
        # Если это HTTP_TS, кэшируем в файл на диске
        if output_type == OutputType.HTTP_TS:
            output_dest = f"/opt/nms-webui/data/streams/{task_id}.ts"
            args = ["-y"] # перезаписывать, если файл есть
        else:
            # Иначе (HTTP) отдаем в stdout для прямого стриминга
            output_dest = "pipe:1"
            args = []
            
        if self.http_ts_codec == "copy":
            args.extend(["-c", "copy", "-f", "mpegts", output_dest])
        else:
            args.extend(["-c:v", self.http_ts_codec, "-c:a", "aac", "-f", "mpegts", output_dest])
            
        return args

    # ── Override ───────────────────────────────────────────────────

    def _get_override(self, output_type: OutputType, task: StreamTask, task_id: str) -> Optional[List[str]]:
        """Проверяет наличие override-шаблона для данного типа вывода."""
        override_map = {
            OutputType.HTTP_TS: self.override_http_ts,
            OutputType.HTTP: self.override_http_ts,
            OutputType.HLS: self.override_hls,
            OutputType.WEBRTC: self.override_webrtc,
        }

        template = override_map.get(output_type, "")
        if not template:
            return None

        hls_dir = f"/tmp/stream_hls_{task_id}"
        rtp_port = 10000 + hash(task_id) % 5000

        try:
            rendered = template.format(
                binary_path=self.binary_path,
                global_args=" ".join(self.global_args),
                input_url=task.input_url,
                task_id=task_id,
                hls_dir=hls_dir,
                rtp_port=rtp_port,
            )
            return shlex.split(rendered)
        except (KeyError, ValueError) as e:
            logger.warning(f"Ошибка в override-шаблоне для {output_type.value}: {e}. Используется штатная логика.")
            return None

    def get_active_count(self) -> int:
        return len(self._processes)
