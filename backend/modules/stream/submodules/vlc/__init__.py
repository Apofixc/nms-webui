# Субмодуль VLC — резервный бэкенд (стриминг, превью)
# Использует cvlc (VLC без GUI) для транскодирования и захвата кадров
import asyncio
import logging
import os
import shutil
import signal
import tempfile
import uuid
from typing import Dict, Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

logger = logging.getLogger(__name__)


class VLCBackend(IStreamBackend):
    """Бэкенд на основе VLC (cvlc headless).

    Резервный вариант для стриминга и превью.
    Используется когда FFmpeg или GStreamer недоступны.
    """

    def __init__(self, vlc_path: str = "cvlc", timeout: int = 30) -> None:
        self._vlc_path = vlc_path
        self._timeout = timeout
        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    @property
    def backend_id(self) -> str:
        return "vlc"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING, BackendCapability.PREVIEW}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {
            StreamProtocol.HTTP, StreamProtocol.HLS,
            StreamProtocol.UDP, StreamProtocol.RTP, StreamProtocol.RTSP,
        }

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HTTP_TS, OutputType.HLS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return {PreviewFormat.JPEG, PreviewFormat.PNG}

    async def start_stream(self, task: StreamTask) -> StreamResult:
        """Запуск стриминга через VLC."""
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            cmd = self._build_stream_command(task, task_id)
            logger.info(f"VLC [{task_id}]: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[task_id] = process

            await asyncio.sleep(2)

            if process.returncode is not None:
                stderr = await process.stderr.read()
                return StreamResult(
                    task_id=task_id,
                    success=False,
                    backend_used="vlc",
                    error=stderr.decode(errors="replace")[-500:],
                )

            return StreamResult(
                task_id=task_id,
                success=True,
                backend_used="vlc",
                output_url=f"/api/v1/m/stream/play/{task_id}",
                metadata={"pid": process.pid},
            )

        except Exception as e:
            logger.error(f"VLC [{task_id}] ошибка: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id, success=False,
                backend_used="vlc", error=str(e),
            )

    async def stop_stream(self, task_id: str) -> bool:
        """Остановка VLC процесса."""
        process = self._processes.pop(task_id, None)
        if not process:
            return False
        if process.returncode is None:
            try:
                process.send_signal(signal.SIGTERM)
                await asyncio.wait_for(process.wait(), timeout=5)
            except (asyncio.TimeoutError, ProcessLookupError):
                process.kill()
                await process.wait()
        return True

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        """Генерация превью через VLC scene filter.

        VLC может захватить кадр через --video-filter=scene.
        """
        # Создаём временную директорию для вывода
        tmp_dir = tempfile.mkdtemp(prefix="vlc_preview_")
        ext = "jpg" if fmt == PreviewFormat.JPEG else "png"
        output_path = os.path.join(tmp_dir, f"preview.{ext}")

        try:
            cmd = [
                self._vlc_path,
                url,
                "--no-audio",
                "--play-and-exit",
                "--run-time=3",
                f"--video-filter=scene",
                f"--scene-format={ext}",
                f"--scene-ratio=1",
                f"--scene-prefix=preview",
                f"--scene-path={tmp_dir}",
                f"--scene-width={width}",
                "--vout=dummy",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )

            await asyncio.wait_for(process.wait(), timeout=self._timeout)

            # VLC сохраняет как preview00001.jpg (или .png)
            for fname in os.listdir(tmp_dir):
                fpath = os.path.join(tmp_dir, fname)
                if fname.startswith("preview") and os.path.isfile(fpath):
                    with open(fpath, "rb") as f:
                        return f.read()

            return None

        except asyncio.TimeoutError:
            if process.returncode is None:
                process.kill()
            return None
        except Exception as e:
            logger.error(f"VLC превью ошибка: {e}")
            return None
        finally:
            # Очистка временных файлов
            import shutil as _shutil
            _shutil.rmtree(tmp_dir, ignore_errors=True)

    async def is_available(self) -> bool:
        if shutil.which(self._vlc_path):
            return True
        return os.path.isfile(self._vlc_path) and os.access(self._vlc_path, os.X_OK)

    async def health_check(self) -> dict:
        available = await self.is_available()
        result = {"backend": "vlc", "path": self._vlc_path, "available": available}
        if available:
            try:
                proc = await asyncio.create_subprocess_exec(
                    self._vlc_path, "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
                result["version"] = stdout.decode(errors="replace").split("\n")[0].strip()
            except Exception:
                pass
        return result

    def _build_stream_command(self, task: StreamTask, task_id: str) -> list[str]:
        """Построение команды cvlc для стриминга."""
        cmd = [self._vlc_path, task.input_url]

        # Транскодирование и вывод
        if task.output_type == OutputType.HTTP:
            cmd.extend([
                "--sout",
                "#std{access=http,mux=ts,dst=:8080/" + task_id + "}",
            ])
        elif task.output_type == OutputType.HTTP_TS:
            cmd.extend([
                "--sout",
                "#std{access=file,mux=ts,dst=/tmp/vlc_ts_" + task_id + ".ts}",
            ])
        elif task.output_type == OutputType.HLS:
            cache_dir = f"/tmp/vlc_hls_{task_id}"
            os.makedirs(cache_dir, exist_ok=True)
            cmd.extend([
                "--sout",
                f"#std{{access=livehttp{{seglen=4,delsegs=true,index={cache_dir}/index.m3u8,index-url=seg_###.ts}},mux=ts,dst={cache_dir}/seg_###.ts}}",
            ])

        return cmd


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда VLC."""
    path = settings.get("vlc_path", "cvlc")
    timeout = settings.get("worker_timeout", 30)
    return VLCBackend(vlc_path=path, timeout=timeout)
