# Реализация бэкенда VLC на базе встроенного HTTP-вещания
import asyncio
import logging
import os
import socket
import tempfile
import time
from typing import Dict, Optional, Any

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat,
)

logger = logging.getLogger(__name__)


class VLCStreamer:
    """Управление VLC с использованием встроенного HTTP-сервера для проксирования."""

    def __init__(self, settings: dict):
        self._settings = settings
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._local_urls: Dict[str, str] = {}

    def _get_setting(self, key: str, default: any) -> any:
        if key in self._settings: return self._settings[key]
        prefixed = f"vlc_{key}"
        if prefixed in self._settings: return self._settings[prefixed]
        return default

    def _get_free_port(self) -> int:
        """Поиск свободного порта."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or f"vlc_{int(time.time())}"
        vlc_path = self._get_setting("binary_path", "cvlc")
        vlc_args = self._get_setting("args", "--no-audio --network-caching=300")
        video_codec = self._get_setting("video_codec", "copy")
        video_bitrate = self._get_setting("video_bitrate", 800)
        
        input_url = task.input_url
        if input_url.startswith("udp://") and "@" not in input_url:
            input_url = input_url.replace("udp://", "udp://@")

        port = None
        local_url = None
        
        acodec = "mpga" # дефолт, переопределится для HLS
        mux = "ts"      # дефолт

        # Настройка параметров вывода по типу
        if task.output_type == OutputType.HLS:
            acodec = "mp4a"
            hls_dir = f"/tmp/stream_hls_{task_id}"
            os.makedirs(hls_dir, exist_ok=True)
            # Используем модуль livehttp для генерации сегментов
            # Уменьшили длину сегмента до 2 секунд, чтобы старт плеера был быстрым
            access = f"livehttp{{seglen=2,delsegs=true,numsegs=10,index={hls_dir}/playlist.m3u8,index-url=segment-########.ts}}"
            output_path = f"{hls_dir}/segment-########.ts"
            res_type = OutputType.HLS

        elif task.output_type == OutputType.HTTP_TS:
            # Прямая запись в файл, как того ожидает API для HTTP_TS
            file_path = f"/opt/nms-webui/data/streams/{task_id}.ts"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            access = "file"
            output_path = file_path
            res_type = OutputType.HTTP_TS

        else:
            # OutputType.HTTP (или fallback) - HTTP проксирование
            port = self._get_free_port()
            access = "http"
            output_path = f":{port}/stream"
            local_url = f"http://127.0.0.1:{port}/stream"
            res_type = OutputType.HTTP

        # Построение sout в зависимости от кодека
        if video_codec == "h264":
            sout = (
                f"#transcode{{vcodec=h264,vb={video_bitrate},acodec={acodec},ab=128,channels=2,samplerate=44100}}:"
                f"standard{{access={access},mux={mux},dst={output_path}}}"
            )
        else:
            # Если copy, то просто muxing
            sout = f"#standard{{access={access},mux={mux},dst={output_path}}}"

        cmd = f"{vlc_path} \"{input_url}\" --sout='{sout}' -I dummy {vlc_args}"

        try:
            logger.info(f"VLC Start: {cmd}")
            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
            )
            self._processes[task_id] = process
            if local_url:
                self._local_urls[task_id] = local_url

            # Если используется HTTP порт, ждем его готовности (до 15 секунд)
            if port:
                success = False
                for _ in range(30):
                    await asyncio.sleep(0.5)
                    if process.returncode is not None: break
                    try:
                        r, w = await asyncio.open_connection('127.0.0.1', port)
                        w.close(); await w.wait_closed(); success = True; break
                    except: continue

                if not success:
                    await self.stop(task_id)
                    return StreamResult(task_id=task_id, success=False, backend_used="vlc", error="VLC port timeout")

            return StreamResult(
                task_id=task_id, success=True, backend_used="vlc",
                output_type=res_type, output_url=local_url, process=process
            )
        except Exception as e:
            return StreamResult(task_id=task_id, success=False, backend_used="vlc", error=str(e))

    async def stop(self, task_id: str) -> bool:
        process = self._processes.pop(task_id, None)
        self._local_urls.pop(task_id, None)
        if process:
            try: process.kill(); await process.wait()
            except: pass
        return True

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        """Инфо для проксирования."""
        # Для HLS и HTTP_TS `api.py` сам отдаст нужные файлы по стандартным путям.
        return None

    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]: return self._processes.get(task_id)
    def get_active_count(self) -> int: return len(self._processes)

    async def generate_preview(self, url: str, protocol: StreamProtocol, fmt: PreviewFormat, width: int = 640, quality: int = 75) -> Optional[bytes]:
        vlc_path = self._get_setting("binary_path", "cvlc")
        if url.startswith("udp://") and "@" not in url: url = url.replace("udp://", "udp://@")
        with tempfile.TemporaryDirectory() as tmp_dir:
            prefix = "snap"
            ext = "jpg" if fmt == PreviewFormat.JPEG else "png"
            cmd = f"{vlc_path} \"{url}\" -I dummy --no-audio --video-filter=scene --vout=dummy --scene-format={ext} --scene-prefix={prefix} --scene-path={tmp_dir} --scene-replace --scene-frames=1 --run-time=10 vlc://quit"
            try:
                process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await asyncio.wait_for(process.wait(), timeout=25.0)
                path = os.path.join(tmp_dir, f"{prefix}.{ext}")
                if os.path.exists(path):
                    with open(path, "rb") as f: return f.read()
            except: pass
        return None
