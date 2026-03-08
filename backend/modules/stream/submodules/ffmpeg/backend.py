# Бэкенд FFmpeg — стриминг через внешний процесс ffmpeg.
# Запускает ffmpeg, читает MPEG-TS из stdout (pipe),
# раздаёт данные подписчикам через FFmpegSession.
import asyncio
import logging
import os
import socket
import time
from typing import Dict, Optional

from backend.modules.stream.core.interfaces import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BufferedSession,
)

logger = logging.getLogger(__name__)


class FFmpegSession(BufferedSession):
    """Сессия FFmpeg-стрима с поддержкой буферизации.

    Наследует BufferedSession — общую логику TS-синхронизации,
    pub/sub и сегментированной записи на диск.
    """
    pass


class FFmpegStreamer:
    """Управление процессами FFmpeg.

    Для каждого запроса:
    1. Формирует команду ffmpeg (input → codec → output).
    2. Запускает ffmpeg с выходом в stdout (pipe) или файл (HLS).
    3. Читает stdout и перекидывает байты в FFmpegSession,
       откуда их забирает API через proxy_queue.
    """

    def __init__(self, settings: dict):
        self._settings = settings
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._sessions: Dict[str, FFmpegSession] = {}
        self._bridges: Dict[str, asyncio.Task] = {}

    # ── Вспомогательные ─────────────────────────────────────────────────

    def _get_setting(self, key: str, default=None):
        """Чтение настройки с поддержкой префикса ffmpeg_ (обратная совместимость)."""
        if key in self._settings:
            return self._settings[key]
        prefixed = f"ffmpeg_{key}"
        if prefixed in self._settings:
            return self._settings[prefixed]
        return default

    @staticmethod
    def _get_free_port() -> int:
        """Возвращает свободный порт на localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def _build_input_args(self, task: StreamTask) -> list:
        """Формирование аргументов входа ffmpeg."""
        args = []

        # Общие опции анализа
        analyzeduration = self._get_setting("analyzeduration", 2000000)
        probesize = self._get_setting("probesize", 65536)
        timeout = self._get_setting("timeout", 5000000)

        # Протоколо-специфичные опции
        url = task.input_url
        if task.input_protocol == StreamProtocol.RTSP:
            rtsp_transport = self._get_setting("rtsp_transport", "tcp")
            args.extend(["-rtsp_transport", rtsp_transport])
            args.extend(["-stimeout", str(timeout)])

        elif task.input_protocol == StreamProtocol.UDP:
            if url.startswith("udp://") and "@" not in url:
                url = url.replace("udp://", "udp://@")
            args.extend(["-timeout", str(timeout)])

        elif task.input_protocol in (
            StreamProtocol.SRT, StreamProtocol.RTP,
        ):
            args.extend(["-timeout", str(timeout)])

        elif task.input_protocol == StreamProtocol.RIST:
            if url.startswith("rist://") and "@" not in url:
                url = url.replace("rist://", "rist://@")
            args.extend(["-fflags", "+genpts"])
            args.extend(["-rw_timeout", str(timeout)])
            args.extend(["-analyzeduration", str(analyzeduration)])
            args.extend(["-probesize", str(probesize)])
            args.extend(["-rist_profile", "simple"])
        elif task.input_protocol == StreamProtocol.RTMP:
            args.extend(["-rw_timeout", str(timeout)])
        elif task.input_protocol in (
            StreamProtocol.HTTP, StreamProtocol.HLS,
        ):
            args.extend(["-timeout", str(timeout)])

        args.extend(["-i", url])
        return args

    def _build_codec_args(self, task: StreamTask) -> list:
        """Формирование аргументов кодирования."""
        args = []

        # Видео
        video_codec = self._get_setting("video_codec", "copy")
        args.extend(["-c:v", video_codec])

        if video_codec != "copy":
            video_bitrate = self._get_setting("video_bitrate", "800k")
            video_preset = self._get_setting("video_preset", "veryfast")
            args.extend(["-b:v", str(video_bitrate)])
            args.extend(["-preset", video_preset])

            width = int(self._get_setting("width", 0))
            height = int(self._get_setting("height", 0))
            fps = float(self._get_setting("fps", 0))

            # Масштабирование
            if width > 0 and height > 0:
                args.extend(["-vf", f"scale={width}:{height}"])
            elif width > 0:
                args.extend(["-vf", f"scale={width}:-2"])
            elif height > 0:
                args.extend(["-vf", f"scale=-2:{height}"])

            # Деинтерлейсинг
            deinterlace = self._get_setting("deinterlace", False)
            if deinterlace:
                # Добавляем yadif к существующим фильтрам
                existing_vf = None
                for i, a in enumerate(args):
                    if a == "-vf" and i + 1 < len(args):
                        existing_vf = i + 1
                        break
                if existing_vf is not None:
                    args[existing_vf] = f"yadif,{args[existing_vf]}"
                else:
                    args.extend(["-vf", "yadif"])

            if fps > 0:
                args.extend(["-r", str(fps)])

        # Аудио
        audio_codec = self._get_setting("audio_codec", "copy")
        args.extend(["-c:a", audio_codec])

        if audio_codec != "copy":
            audio_bitrate = self._get_setting("audio_bitrate", "128k")
            audio_channels = int(self._get_setting("audio_channels", 2))
            audio_samplerate = int(self._get_setting("audio_samplerate", 44100))
            args.extend(["-b:a", str(audio_bitrate)])
            args.extend(["-ac", str(audio_channels)])
            args.extend(["-ar", str(audio_samplerate)])

        return args

    # ── Жизненный цикл потока ───────────────────────────────────────────

    async def start(self, task: StreamTask) -> StreamResult:
        """Запуск трансляции FFmpeg."""
        task_id = task.task_id or f"ffmpeg_{int(time.time())}"
        ffmpeg_path = self._get_setting("binary_path", "ffmpeg")
        extra_args = self._get_setting("args", "")

        seglen = int(self._get_setting("hls_time", 5))
        numsegs = int(self._get_setting("hls_list_size", 10))

        # Формируем команду
        cmd = [ffmpeg_path, "-hide_banner", "-nostats", "-y"]
        cmd.extend(self._build_input_args(task))
        cmd.extend(self._build_codec_args(task))

        local_url = None

        if task.output_type == OutputType.HLS:
            # HLS: ffmpeg пишет сегменты на диск
            hls_dir = f"data/streams/hls_{task_id}"
            os.makedirs(hls_dir, exist_ok=True)
            playlist_path = f"{hls_dir}/playlist.m3u8"
            segment_path = f"{hls_dir}/seg-%05d.ts"

            cmd.extend([
                "-f", "hls",
                "-hls_time", str(seglen),
                "-hls_list_size", str(numsegs),
                "-hls_flags", "delete_segments+append_list",
                "-hls_segment_filename", segment_path,
                playlist_path,
            ])

            local_url = f"/api/modules/stream/v1/proxy/{task_id}/index.m3u8"

            session = FFmpegSession(
                task_id=task_id,
                task=task,
                buffer_dir=hls_dir,
                segment_duration=seglen,
                max_segments=numsegs,
            )
            self._sessions[task_id] = session

        else:
            # HTTP / HTTP_TS: ffmpeg пишет MPEG-TS в pipe:1 (stdout)
            cmd.extend(["-f", "mpegts", "pipe:1"])

            buffer_dir = ""
            if task.output_type == OutputType.HTTP_TS:
                buffer_dir = f"data/streams/ffmpeg_ts_{task_id}"
                os.makedirs(buffer_dir, exist_ok=True)
                local_url = f"/api/modules/stream/v1/play/{task_id}"
            else:
                local_url = f"/api/modules/stream/v1/proxy/{task_id}"

            session = FFmpegSession(
                task_id=task_id,
                task=task,
                buffer_dir=buffer_dir,
                segment_duration=seglen,
                max_segments=numsegs,
            )
            self._sessions[task_id] = session

        # Добавляем пользовательские аргументы
        if extra_args:
            import shlex
            cmd.extend(shlex.split(extra_args))

        try:
            logger.info(f"FFmpeg [{task_id}]: запуск {' '.join(cmd)}")

            # Для HLS — stdout не нужен, для pipe — нужен
            stdout = (
                asyncio.subprocess.PIPE
                if task.output_type != OutputType.HLS
                else asyncio.subprocess.DEVNULL
            )

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=stdout,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[task_id] = process

            # Фоновое чтение stderr для логирования ошибок ffmpeg
            asyncio.create_task(
                self._log_stderr(task_id, process)
            )

            # Запускаем мост (читает из stdout процесса)
            if task.output_type != OutputType.HLS:
                self._bridges[task_id] = asyncio.create_task(
                    self._run_bridge(task_id, process, session)
                )

            return StreamResult(
                task_id=task_id,
                success=True,
                backend_used="ffmpeg",
                output_type=task.output_type,
                output_url=local_url,
                process=process,
            )
        except Exception as e:
            logger.error(f"FFmpeg [{task_id}]: ошибка запуска {e}")
            return StreamResult(
                task_id=task_id,
                success=False,
                backend_used="ffmpeg",
                error=str(e),
            )

    async def stop(self, task_id: str) -> bool:
        """Остановка FFmpeg: отмена моста, убийство процесса.
        
        ВАЖНО: НЕ удаляет временные файлы — это задача модуля Stream.
        """
        # 1. Мост
        bridge = self._bridges.pop(task_id, None)
        if bridge:
            bridge.cancel()

        # 2. Сессия
        session = self._sessions.pop(task_id, None)
        if session:
            session.close()

        # 3. Процесс
        process = self._processes.pop(task_id, None)
        if process:
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass

        return True

    # ── Мост: FFmpeg stdout → подписчики ────────────────────────────────

    async def _run_bridge(
        self,
        task_id: str,
        process: asyncio.subprocess.Process,
        session: FFmpegSession,
    ):
        """Фоновая задача: читает MPEG-TS из stdout ffmpeg и рассылает подписчикам."""
        try:
            # Таймаут на первые данные (защита от зависания при RIST/UDP без источника)
            first_chunk_timeout = 15.0
            try:
                chunk = await asyncio.wait_for(
                    process.stdout.read(65536), timeout=first_chunk_timeout
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"FFmpeg [{task_id}]: нет данных {first_chunk_timeout}с — "
                    f"источник не отвечает"
                )
                return

            if not chunk:
                logger.warning(f"FFmpeg [{task_id}]: stdout закрыт без данных")
                return

            await session.process_chunk(chunk)
            logger.info(f"FFmpeg [{task_id}]: мост подключён")

            # Основной цикл чтения (без таймаута — данные уже пошли)
            while task_id in self._processes:
                chunk = await process.stdout.read(65536)
                if not chunk:
                    break
                await session.process_chunk(chunk)

            logger.debug(f"FFmpeg [{task_id}]: мост завершён")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"FFmpeg [{task_id}]: ошибка моста {e}")
        finally:
            session.close()

    async def _log_stderr(self, task_id: str, process: asyncio.subprocess.Process):
        """Фоновое чтение stderr ffmpeg для логирования ошибок."""
        try:
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if text:
                    # Используем INFO для отладки RIST, чтобы видеть ошибки в консоли
                    logger.info(f"FFmpeg [{task_id}] stderr: {text}")
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    # ── Публичный контракт ──────────────────────────────────────────────

    def get_session(self, task_id: str) -> Optional[FFmpegSession]:
        """Получить активную сессию по ID."""
        return self._sessions.get(task_id)

    def get_process(
        self, task_id: str
    ) -> Optional[asyncio.subprocess.Process]:
        """Получить процесс ffmpeg по ID задачи."""
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
        elif session.task.output_type == OutputType.HTTP_TS:
            return {
                "type": "proxy_buffer",
                "content_type": "video/mp2t",
                "buffer_dir": session.buffer_dir,
                "segments": list(session.segments),
                "segment_duration": session.segment_duration,
                "get_session": lambda: self._sessions.get(task_id),
            }
        elif session.task.output_type == OutputType.HLS:
            return {
                "type": "hls_playlist",
                "playlist_url": (
                    f"/api/modules/stream/v1/proxy/{task_id}/index.m3u8"
                ),
                "buffer_dir": session.buffer_dir,
                "segments": list(session.segments),
                "segment_duration": session.segment_duration,
            }
        return None

    def get_active_count(self) -> int:
        """Количество активных процессов FFmpeg."""
        return len(self._processes)

    # ── Превью ──────────────────────────────────────────────────────────

    async def generate_preview(
        self,
        url: str,
        protocol: StreamProtocol,
        fmt: PreviewFormat,
        width: int = 640,
        quality: int = 75,
    ) -> Optional[bytes]:
        """Генерация превью (скриншота) средствами ffmpeg.
        
        Использует ffmpeg -ss для быстрого seek + -frames:v 1 для захвата одного кадра.
        Результат пишется в stdout (pipe:1), без промежуточных файлов.
        """
        ffmpeg_path = self._get_setting("binary_path", "ffmpeg")
        seek_time = int(self._get_setting("preview_seek_time", 2))

        # Подготовка URL
        if url.startswith("udp://") and "@" not in url:
            url = url.replace("udp://", "udp://@")
        if url.startswith("rist://") and "@" not in url:
            url = url.replace("rist://", "rist://@")

        # Формат вывода
        format_map = {
            PreviewFormat.JPEG: ("mjpeg", "jpg"),
            PreviewFormat.PNG: ("png", "png"),
            PreviewFormat.WEBP: ("webp", "webp"),
            PreviewFormat.TIFF: ("tiff", "tiff"),
        }
        out_format, _ = format_map.get(fmt, ("mjpeg", "jpg"))

        # Формируем команду
        cmd = [
            ffmpeg_path, "-hide_banner", "-nostats", "-y",
        ]

        # Для не-стримовых протоколов — seek вперёд
        if protocol not in (
            StreamProtocol.UDP, StreamProtocol.RTP, StreamProtocol.RIST,
        ):
            cmd.extend(["-ss", str(seek_time)])

        # Специфичные опции для протоколов
        if protocol == StreamProtocol.RTSP:
            cmd.extend(["-rtsp_transport", "tcp"])
        if protocol == StreamProtocol.RIST:
            cmd.extend(["-fflags", "+genpts", "-rist_profile", "simple"])

        if protocol in (
            StreamProtocol.UDP, StreamProtocol.RTP, StreamProtocol.RIST,
        ):
            cmd.extend(["-timeout", "5000000"])

        cmd.extend([
            "-i", url,
            "-frames:v", "1",
            "-an",
        ])

        # Масштабирование
        if width > 0:
            cmd.extend(["-vf", f"scale={width}:-2"])

        # Качество для JPEG/WEBP
        if fmt == PreviewFormat.JPEG:
            # ffmpeg quality: 2 (лучше) — 31 (хуже), конвертируем из 0-100
            q = max(2, min(31, int(31 - (quality / 100 * 29))))
            cmd.extend(["-q:v", str(q)])

        cmd.extend(["-f", "image2pipe", "-c:v", out_format, "pipe:1"])

        try:
            logger.info(f"FFmpeg [preview]: запуск {url}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )

            try:
                stdout_data, _ = await asyncio.wait_for(
                    process.communicate(), timeout=20.0
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
                return None

            if stdout_data and len(stdout_data) > 100:
                logger.info(
                    f"FFmpeg [preview]: превью создано "
                    f"({len(stdout_data)} байт)"
                )
                return stdout_data

        except Exception as e:
            logger.error(f"FFmpeg [preview]: ошибка {e}")

        return None
