# Реализация бэкенда VLC на базе встроенного HTTP-вещания
import asyncio
import logging
import os
import socket
import tempfile
import time
from typing import Dict, Optional, Any, List

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat,
)

logger = logging.getLogger(__name__)


class VLCSession:
    """Легковесная сессия для отслеживания HLS-сегментов VLC."""
    def __init__(self, task_id: str, task: StreamTask, buffer_dir: str, segment_duration: int = 5):
        self.task_id = task_id
        self.task = task
        self.buffer_dir = buffer_dir
        self.segment_duration = segment_duration

    @property
    def segments(self) -> List[str]:
        try:
            files = [f for f in os.listdir(self.buffer_dir) if f.endswith(".ts")]
            files.sort()
            # Возвращаем все кроме последнего (последний еще пишется)
            return files[:-1] if len(files) > 0 else []
        except Exception:
            return []

    @property
    def current_segment_name(self) -> Optional[str]:
        try:
            files = [f for f in os.listdir(self.buffer_dir) if f.endswith(".ts")]
            files.sort()
            return files[-1] if len(files) > 0 else None
        except Exception:
            return None


class VLCStreamer:
    """Управление VLC с использованием встроенного HTTP-сервера для проксирования."""

    def __init__(self, settings: dict):
        self._settings = settings
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._local_urls: Dict[str, str] = {}
        self._sessions: Dict[str, VLCSession] = {}

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
        
        # Загружаем настройки HLS
        seglen = int(self._get_setting("hls_seglen", 5))
        numsegs = int(self._get_setting("hls_numsegs", 10))
        
        input_url = task.input_url
        if input_url.startswith("udp://") and "@" not in input_url:
            input_url = input_url.replace("udp://", "udp://@")

        port = None
        local_url = None
        
        # Для HLS и HTTP_TS будем всегда использовать livehttp нарезку
        if task.output_type in (OutputType.HLS, OutputType.HTTP_TS):
            acodec = "mp4a"
            mux = "ts"
            # Изменено на относительный путь
            hls_dir = f"data/streams/hls_{task_id}"
            os.makedirs(hls_dir, exist_ok=True)
            
            # Используем оригинальную команду VLC (livehttp) с корректной длиной сегмента из настроек,
            # Обязательно добавляем splitanywhere=true, иначе на потоках с битыми I-фреймами (как tv3by) 
            # сегмент будет 0 байт бесконечно долго.
            access = f"livehttp{{seglen={seglen},delsegs=true,numsegs={numsegs},splitanywhere=true,index={hls_dir}/playlist.m3u8,index-url=seg-########.ts}}"
            output_path = f"{hls_dir}/seg-########.ts"
            res_type = task.output_type
            
            # Важно: для HLS сообщаем фронту путь к динамическому прокси
            # для HTTP_TS отдаем локальный проксируемый url
            if task.output_type == OutputType.HLS:
                local_url = f"/api/modules/stream/v1/proxy/{task_id}/index.m3u8"
            else:
                local_url = f"/api/modules/stream/v1/play/{task_id}"
            
            # Создаем сессию для API (api.py будет из нее читать segments)
            self._sessions[task_id] = VLCSession(task_id, task, hls_dir, segment_duration=seglen)

        else:
            # OutputType.HTTP (прямой проброс через порт)
            acodec = "mpga" 
            mux = "ts"
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

            # Если используется HTTP порт, ждем его готовности
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
        self._sessions.pop(task_id, None)
        if process:
            try: process.kill(); await process.wait()
            except: pass
        return True

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        """Инфо для проксирования."""
        session = self._sessions.get(task_id)
        if not session:
            return None
            
        if session.task.output_type == OutputType.HTTP_TS:
            return {
                "type": "proxy_buffer",
                "content_type": "video/mp2t",
                "buffer_dir": session.buffer_dir,
                "segments": session.segments,
                "segment_duration": session.segment_duration,
                "get_session": lambda: self._sessions.get(task_id)
            }
        elif session.task.output_type == OutputType.HLS:
            return {
                "type": "hls_playlist",
                "playlist_url": f"/api/modules/stream/v1/proxy/{task_id}/index.m3u8",
                "buffer_dir": session.buffer_dir,
                "segments": session.segments,
                "segment_duration": session.segment_duration
            }
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
