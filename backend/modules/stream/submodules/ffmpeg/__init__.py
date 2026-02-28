# Субмодуль FFmpeg — основной универсальный бэкенд
# Поддерживает: стриминг, конвертацию, генерацию превью
import asyncio
import logging
import os
import shutil
import signal
import uuid
from typing import Dict, Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)
from backend.modules.stream.core.exceptions import BackendUnavailableError

logger = logging.getLogger(__name__)


class FFmpegBackend(IStreamBackend):
    """Бэкенд на основе FFmpeg.

    Формирует командные строки ffmpeg для:
    - Стриминга (входной поток → HTTP/HLS/TS вывод)
    - Превью (захват одного кадра из потока)

    Поддерживает все сетевые протоколы на входе.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg", timeout: int = 30) -> None:
        self._ffmpeg_path = ffmpeg_path
        self._timeout = timeout
        # Активные процессы: task_id -> asyncio.subprocess.Process
        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    # --- Свойства контракта ---

    @property
    def backend_id(self) -> str:
        return "ffmpeg"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {
            BackendCapability.STREAMING,
            BackendCapability.CONVERSION,
            BackendCapability.PREVIEW,
        }

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {
            StreamProtocol.HTTP, StreamProtocol.HLS,
            StreamProtocol.UDP, StreamProtocol.RTP, StreamProtocol.RTSP,
        }

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HTTP_TS, OutputType.HLS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return {PreviewFormat.JPEG, PreviewFormat.PNG, PreviewFormat.WEBP}

    # --- Стриминг ---

    async def start_stream(self, task: StreamTask) -> StreamResult:
        """Запуск стриминга через FFmpeg subprocess.

        Формирует команду ffmpeg с параметрами входа/выхода
        и запускает её как асинхронный процесс.
        """
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            cmd = self._build_stream_command(task)
            logger.info(f"FFmpeg стриминг [{task_id}]: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            self._processes[task_id] = process

            # Даём ffmpeg время на инициализацию (2 секунды)
            await asyncio.sleep(2)

            # Проверяем, что процесс не упал сразу
            if process.returncode is not None:
                stderr = await process.stderr.read()
                error_msg = stderr.decode(errors="replace")[-500:]
                return StreamResult(
                    task_id=task_id,
                    success=False,
                    backend_used="ffmpeg",
                    error=f"FFmpeg завершился с кодом {process.returncode}: {error_msg}",
                )

            return StreamResult(
                task_id=task_id,
                success=True,
                backend_used="ffmpeg",
                output_url=f"/api/v1/m/stream/play/{task_id}",
                metadata={"pid": process.pid, "cmd": " ".join(cmd)},
            )

        except Exception as e:
            logger.error(f"Ошибка запуска FFmpeg [{task_id}]: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id,
                success=False,
                backend_used="ffmpeg",
                error=str(e),
            )

    async def stop_stream(self, task_id: str) -> bool:
        """Остановка FFmpeg процесса."""
        process = self._processes.pop(task_id, None)
        if not process:
            return False

        if process.returncode is None:
            # Посылаем SIGTERM для корректного завершения
            try:
                process.send_signal(signal.SIGTERM)
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                # Принудительное завершение
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass

        logger.info(f"FFmpeg поток [{task_id}] остановлен")
        return True

    # --- Превью ---

    async def generate_preview(
        self,
        url: str,
        protocol: StreamProtocol,
        fmt: PreviewFormat,
        width: int = 640,
        quality: int = 75,
    ) -> Optional[bytes]:
        """Генерация превью: захват одного кадра из потока.

        Использует ffmpeg для захвата I-кадра и вывода
        изображения в stdout в указанном формате.
        """
        cmd = self._build_preview_command(url, protocol, fmt, width, quality)
        logger.debug(f"FFmpeg превью: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._timeout,
            )

            if process.returncode != 0:
                error_msg = stderr.decode(errors="replace")[-300:]
                logger.warning(f"FFmpeg превью ошибка: {error_msg}")
                return None

            if not stdout:
                logger.warning("FFmpeg превью: пустой вывод")
                return None

            return stdout

        except asyncio.TimeoutError:
            logger.warning(f"FFmpeg превью: таймаут ({self._timeout}s) для {url}")
            if process.returncode is None:
                process.kill()
            return None
        except Exception as e:
            logger.error(f"FFmpeg превью ошибка: {e}", exc_info=True)
            return None

    # --- Доступность ---

    async def is_available(self) -> bool:
        """Проверка наличия ffmpeg в системе."""
        # Быстрая проверка через shutil
        if shutil.which(self._ffmpeg_path):
            return True

        # Проверка по абсолютному пути
        if os.path.isfile(self._ffmpeg_path) and os.access(self._ffmpeg_path, os.X_OK):
            return True

        return False

    async def health_check(self) -> dict:
        """Расширенная проверка: версия ffmpeg."""
        result = {
            "backend": "ffmpeg",
            "path": self._ffmpeg_path,
            "available": await self.is_available(),
            "version": None,
        }

        if result["available"]:
            try:
                proc = await asyncio.create_subprocess_exec(
                    self._ffmpeg_path, "-version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
                # Первая строка содержит версию
                first_line = stdout.decode(errors="replace").split("\n")[0]
                result["version"] = first_line.strip()
            except Exception:
                pass

        return result

    # --- Построение команд ---

    def _build_stream_command(self, task: StreamTask) -> list[str]:
        """Формирование командной строки ffmpeg для стриминга.

        Структура: ffmpeg -i <input> [фильтры] -f <format> <output>
        """
        cmd = [self._ffmpeg_path]

        # Глобальные опции
        cmd.extend([
            "-hide_banner",
            "-loglevel", "warning",
            "-y",               # Перезаписывать без подтверждения
        ])

        # Входные опции по протоколу
        cmd.extend(self._input_options(task.input_protocol))

        # Входной URL
        cmd.extend(["-i", task.input_url])

        # Выходные опции по типу
        cmd.extend(self._output_options(task.output_type, task.task_id))

        return cmd

    def _build_preview_command(
        self,
        url: str,
        protocol: StreamProtocol,
        fmt: PreviewFormat,
        width: int,
        quality: int,
    ) -> list[str]:
        """Формирование командной строки ffmpeg для захвата кадра."""
        cmd = [self._ffmpeg_path]

        # Глобальные опции
        cmd.extend([
            "-hide_banner",
            "-loglevel", "error",
            "-y",
        ])

        # Протокол-специфичные опции
        cmd.extend(self._input_options(protocol))

        # Вход
        cmd.extend(["-i", url])

        # Захват одного кадра
        cmd.extend(["-vframes", "1"])

        # Масштабирование (сохраняя пропорции)
        cmd.extend(["-vf", f"scale={width}:-1"])

        # Формат вывода
        if fmt == PreviewFormat.JPEG:
            cmd.extend(["-f", "image2", "-c:v", "mjpeg", "-q:v", str(max(1, 31 - quality * 30 // 100))])
        elif fmt == PreviewFormat.PNG:
            cmd.extend(["-f", "image2", "-c:v", "png"])
        elif fmt == PreviewFormat.WEBP:
            cmd.extend(["-f", "webp", "-quality", str(quality)])

        # Вывод в stdout
        cmd.append("pipe:1")

        return cmd

    def _input_options(self, protocol: StreamProtocol) -> list[str]:
        """Протокол-специфичные опции для входа."""
        opts = []

        if protocol == StreamProtocol.UDP:
            # UDP мультикаст/юникаст: буферизация и таймаут
            opts.extend([
                "-buffer_size", "1048576",
                "-fifo_size", "1000000",
            ])
        elif protocol == StreamProtocol.RTSP:
            # RTSP: предпочитаем TCP транспорт
            opts.extend(["-rtsp_transport", "tcp"])
        elif protocol in (StreamProtocol.HTTP, StreamProtocol.HLS):
            # HTTP/HLS: таймаут и reconnect
            opts.extend([
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
                "-timeout", str(self._timeout * 1000000),  # микросекунды
            ])

        return opts

    def _output_options(self, output_type: OutputType, task_id: str | None) -> list[str]:
        """Опции вывода по типу."""
        opts = []

        if output_type == OutputType.HTTP:
            # Прямой MPEG-TS вывод в pipe (для последующего проксирования)
            opts.extend([
                "-c:v", "copy",
                "-c:a", "copy",
                "-f", "mpegts",
                "pipe:1",
            ])
        elif output_type == OutputType.HTTP_TS:
            # Сегментация в .ts файлы
            cache_dir = f"/tmp/stream_ts_{task_id}"
            os.makedirs(cache_dir, exist_ok=True)
            opts.extend([
                "-c:v", "copy",
                "-c:a", "copy",
                "-f", "segment",
                "-segment_time", "4",
                "-segment_format", "mpegts",
                "-segment_list", f"{cache_dir}/playlist.m3u8",
                "-segment_list_type", "m3u8",
                f"{cache_dir}/segment_%03d.ts",
            ])
        elif output_type == OutputType.HLS:
            # HLS вывод с плейлистом
            cache_dir = f"/tmp/stream_hls_{task_id}"
            os.makedirs(cache_dir, exist_ok=True)
            opts.extend([
                "-c:v", "copy",
                "-c:a", "copy",
                "-f", "hls",
                "-hls_time", "4",
                "-hls_list_size", "5",
                "-hls_flags", "delete_segments+append_list",
                "-hls_segment_filename", f"{cache_dir}/seg_%03d.ts",
                f"{cache_dir}/index.m3u8",
            ])
        else:
            # Fallback: MPEG-TS в pipe
            opts.extend([
                "-c:v", "copy",
                "-c:a", "copy",
                "-f", "mpegts",
                "pipe:1",
            ])

        return opts


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда FFmpeg."""
    path = settings.get("ffmpeg_path", "ffmpeg")
    timeout = settings.get("worker_timeout", 30)
    return FFmpegBackend(ffmpeg_path=path, timeout=timeout)
