# Реализация бэкенда VLC на базе встроенного HTTP-вещания
import asyncio
import logging
import os
import shutil
import aiohttp
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
    """Легковесная сессия для управления потоком VLC и его буфером."""
    def __init__(self, task_id: str, task: StreamTask, buffer_dir: str = "", playlist_path: str = "", segment_duration: int = 5):
        self.task_id = task_id
        self.task = task
        self.buffer_dir = buffer_dir
        self.playlist_path = playlist_path
        self.segment_duration = segment_duration
        self._subscribers: List[asyncio.Queue] = []
        
        # Для ручной сегментации (HTTP_TS)
        self._manual_segments: List[str] = []
        self._current_manual_segment: Optional[str] = None
        self._manual_file = None
        self._seg_idx = 1
        self._seg_start_time = 0
        self._max_segments = 24

    def subscribe(self) -> asyncio.Queue:
        """Подписаться на получение чанков в реальном времени."""
        queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Отписаться."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    def dispatch(self, chunk: bytes):
        """Разослать чанк всем подписчикам."""
        for q in self._subscribers:
            try:
                if q.full(): q.get_nowait()
                q.put_nowait(chunk)
            except: pass

    async def write_manual_chunk(self, chunk: bytes):
        """Ручная сегментация для HTTP_TS (как в builtin_proxy)."""
        now = time.time()
        if not self._manual_file or (now - self._seg_start_time) >= self.segment_duration:
            await self._rotate_manual_segment(now)
        
        if self._manual_file:
            await asyncio.to_thread(self._sync_write, chunk)

    def _sync_write(self, chunk: bytes):
        if self._manual_file:
            try:
                self._manual_file.write(chunk)
                self._manual_file.flush()
            except: pass

    async def _rotate_manual_segment(self, now):
        """Смена ручного сегмента."""
        if self._manual_file:
            f = self._manual_file
            self._manual_file = None
            await asyncio.to_thread(f.close)
            if self._current_manual_segment:
                self._manual_segments.append(self._current_manual_segment)
                if len(self._manual_segments) > self._max_segments:
                    old = self._manual_segments.pop(0)
                    try: os.remove(os.path.join(self.buffer_dir, old))
                    except: pass

        try:
            os.makedirs(self.buffer_dir, exist_ok=True)
            name = f"seg-{self._seg_idx:08d}.ts"
            self._manual_file = open(os.path.join(self.buffer_dir, name), "wb")
            self._current_manual_segment = name
            self._seg_idx += 1
            self._seg_start_time = now
        except: pass

    @property
    def segments(self) -> List[str]:
        if self.task.output_type == OutputType.HTTP_TS:
            return list(self._manual_segments)
        
        # Для HLS используем нативную логику VLC
        try:
            # Для HLS и DASH ищем соответствующие расширения
            ext = ".ts" if self.task.output_type == OutputType.HLS else ".m4s"
            if self.task.output_type == OutputType.DASH and not any(f.endswith(".m4s") for f in os.listdir(self.buffer_dir)):
                 ext = ".ts" # Fallback to TS for DASH
            
            files = [f for f in os.listdir(self.buffer_dir) if f.endswith(ext)]
            files.sort()
            return files[:-1] if len(files) > 0 else []
        except: return []

    @property
    def current_segment_name(self) -> Optional[str]:
        if self.task.output_type == OutputType.HTTP_TS:
            return self._current_manual_segment
            
        try:
            files = [f for f in os.listdir(self.buffer_dir) if f.endswith(".ts")]
            files.sort()
            return files[-1] if len(files) > 0 else None
        except: return None

    async def cleanup(self):
        """Очистка ресурсов."""
        if self._manual_file:
            f = self._manual_file
            self._manual_file = None
            await asyncio.to_thread(f.close)
            
        if self.buffer_dir and os.path.exists(self.buffer_dir):
            try: shutil.rmtree(self.buffer_dir)
            except: pass
        if self.playlist_path and os.path.exists(self.playlist_path):
            try: os.remove(self.playlist_path)
            except: pass


class VLCStreamer:
    """Управление VLC с использованием встроенного HTTP-сервера для проксирования."""

    def __init__(self, settings: dict):
        self._settings = settings
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._local_urls: Dict[str, str] = {}
        self._vlc_internal_urls: Dict[str, str] = {}
        self._bridge_tasks: Dict[str, asyncio.Task] = {}
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
        
        # 1. Настройки видео
        video_codec = self._get_setting("video_codec", "copy")
        video_bitrate = self._get_setting("video_bitrate", 800)
        width = int(self._get_setting("width", 0))
        height = int(self._get_setting("height", 0))
        fps = float(self._get_setting("fps", 0))
        deinterlace = self._get_setting("deinterlace", False)
        deinterlace_mode = self._get_setting("deinterlace_mode", "yadif")
        
        # 2. Настройки аудио
        audio_codec = self._get_setting("audio_codec", "copy")
        audio_bitrate = self._get_setting("audio_bitrate", 128)
        audio_channels = int(self._get_setting("audio_channels", 2))
        audio_samplerate = int(self._get_setting("audio_samplerate", 44100))
        force_audio = self._get_setting("force_audio", True)
        
        # 3. Настройки сети и протоколов
        network_caching = self._get_setting("network_caching", 300)
        low_delay = self._get_setting("low_delay", False)
        rtsp_tcp = self._get_setting("rtsp_tcp", False)
        clock_jitter = self._get_setting("clock_jitter", 500)
        vlc_verbosity = int(self._get_setting("vlc_verbosity", 0))
        
        vlc_args = self._get_setting("args", "")
        
        # Формируем доп. аргументы из настроек
        extra_args = []
        
        # Громкость логов
        if vlc_verbosity == 1: extra_args.append("-v")
        elif vlc_verbosity == 2: extra_args.append("-vv")
        
        # Кэширование и задержка
        if low_delay:
            extra_args.append("--network-caching=100 --clock-jitter=0 --sout-mux-caching=100")
        elif f"--network-caching" not in vlc_args:
            extra_args.append(f"--network-caching={network_caching}")
            
        if rtsp_tcp and "--rtsp-tcp" not in vlc_args:
            extra_args.append("--rtsp-tcp")
        if f"--clock-jitter" not in vlc_args:
            extra_args.append(f"--clock-jitter={clock_jitter}")
            
        full_vlc_args = f"{vlc_args} {' '.join(extra_args)}"

        seglen = int(self._get_setting("hls_seglen", 5))
        numsegs = int(self._get_setting("hls_numsegs", 10))
        
        input_url = task.input_url
        if input_url.startswith("udp://") and "@" not in input_url:
            input_url = input_url.replace("udp://", "udp://@")

        port = None
        local_url = None
        
        # 4. Выходные форматы
        if task.output_type == OutputType.HLS:
            # Для HLS всегда нужно аудио
            hls_acodec = audio_codec if audio_codec != "copy" else "mp4a"
            mux = "ts"
            base_dir = "data/streams"
            hls_dir = f"{base_dir}/hls_{task_id}"
            os.makedirs(hls_dir, exist_ok=True)
            playlist_path = f"{hls_dir}/playlist.m3u8"
            access = f"livehttp{{seglen={seglen},delsegs=true,numsegs={numsegs},splitanywhere=true,index={playlist_path},index-url=seg-########.ts}}"
            output_path = f"{hls_dir}/seg-########.ts"
            local_url = f"/api/modules/stream/v1/proxy/{task_id}/index.m3u8"
            self._sessions[task_id] = VLCSession(task_id, task, hls_dir, playlist_path, segment_duration=seglen)
            acodec = hls_acodec

        elif task.output_type == OutputType.DASH:
            # Для DASH
            acodec = audio_codec if audio_codec != "copy" else "mp4a"
            mux = "dash"
            base_dir = "data/streams"
            dash_dir = f"{base_dir}/dash_{task_id}"
            os.makedirs(dash_dir, exist_ok=True)
            playlist_path = f"{dash_dir}/index.mpd"
            # VLC DASH muxer: use live=1, seglen=seglen
            access = f"livehttp{{seglen={seglen},delsegs=true,numsegs={numsegs},splitanywhere=true,index={playlist_path},index-url=seg-########.ts}}"
            # Note: VLC's DASH muxer is sometimes tricky. We use livehttp with .ts as DASH-TS.
            # Alternatively, if we want real DASH-MP4, we'd need more complex sout.
            local_url = f"/api/modules/stream/v1/proxy/{task_id}/index.mpd"
            self._sessions[task_id] = VLCSession(task_id, task, dash_dir, playlist_path, segment_duration=seglen)
            acodec = acodec

        else:
            default_ac = "mp4a" if task.output_type == OutputType.HTTP_TS else "mpga"
            acodec = audio_codec if audio_codec != "copy" else default_ac
            
            mux = "ts"
            port = self._get_free_port()
            access = "http"
            output_path = f":{port}/stream"
            vlc_url = f"http://127.0.0.1:{port}/stream"
            self._vlc_internal_urls[task_id] = vlc_url
            
            buffer_dir = ""
            if task.output_type == OutputType.HTTP_TS:
                buffer_dir = f"data/streams/vlc_ts_{task_id}"
                os.makedirs(buffer_dir, exist_ok=True)
                local_url = f"/api/modules/stream/v1/play/{task_id}"
            else:
                local_url = f"/api/modules/stream/v1/proxy/{task_id}"
            
            session = VLCSession(task_id, task, buffer_dir=buffer_dir, segment_duration=seglen)
            session._max_segments = numsegs
            self._sessions[task_id] = session
            self._bridge_tasks[task_id] = asyncio.create_task(
                self._vlc_http_bridge(task_id, vlc_url, session)
            )

        # 5. Формирование строки транскодирования (sout)
        transcode_parts = []
        
        # Видео часть
        if video_codec == "h264":
            v_params = [f"vcodec=h264", f"vb={video_bitrate}"]
            if width > 0: v_params.append(f"width={width}")
            if height > 0: v_params.append(f"height={height}")
            if fps > 0: v_params.append(f"fps={fps}")
            if deinterlace: v_params.append(f"deinterlace,vfilter=deinterlace{{mode={deinterlace_mode}}}")
            transcode_parts.append(",".join(v_params))
        
        # Аудио часть
        if audio_codec != "copy" or force_audio:
            a_params = [
                f"acodec={acodec}", 
                f"ab={audio_bitrate}", 
                f"channels={audio_channels}", 
                f"samplerate={audio_samplerate}"
            ]
            transcode_parts.append(",".join(a_params))
            
        if transcode_parts:
            sout = (f"#transcode{{{','.join(transcode_parts)}}}:"
                    f"standard{{access={access},mux={mux},dst={output_path}}}")
        else:
            sout = f"#standard{{access={access},mux={mux},dst={output_path}}}"

        cmd = f"{vlc_path} \"{input_url}\" --sout='{sout}' -I dummy {full_vlc_args}"

        try:
            logger.info(f"VLC Start: {cmd}")
            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
            )
            self._processes[task_id] = process
            if local_url: self._local_urls[task_id] = local_url

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

            return StreamResult(task_id=task_id, success=True, backend_used="vlc",
                                output_type=task.output_type, output_url=local_url, process=process)
        except Exception as e:
            return StreamResult(task_id=task_id, success=False, backend_used="vlc", error=str(e))

    async def stop(self, task_id: str) -> bool:
        process = self._processes.pop(task_id, None)
        self._local_urls.pop(task_id, None)
        self._vlc_internal_urls.pop(task_id, None)
        bridge_task = self._bridge_tasks.pop(task_id, None)
        if bridge_task: bridge_task.cancel()
        session = self._sessions.pop(task_id, None)
        if session: await session.cleanup()
        if process:
            try: process.kill(); await process.wait()
            except: pass
        return True

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        session = self._sessions.get(task_id)
        if not session: return None
        if session.task.output_type == OutputType.HTTP:
            q = session.subscribe()
            return {"type": "proxy_queue", "content_type": "video/mp2t", "queue": q, "unsubscribe": lambda: session.unsubscribe(q)}
        elif session.task.output_type == OutputType.HTTP_TS:
            return {"type": "proxy_buffer", "content_type": "video/mp2t", "buffer_dir": session.buffer_dir,
                    "segments": session.segments, "segment_duration": session.segment_duration,
                    "get_session": lambda: self._sessions.get(task_id)}
        elif session.task.output_type == OutputType.HLS:
            return {"type": "hls_playlist", "playlist_url": f"/api/modules/stream/v1/proxy/{task_id}/index.m3u8",
                    "buffer_dir": session.buffer_dir, "segments": session.segments, "segment_duration": session.segment_duration}
        elif session.task.output_type == OutputType.DASH:
            return {"type": "dash_playlist", "playlist_url": f"/api/modules/stream/v1/proxy/{task_id}/index.mpd",
                    "buffer_dir": session.buffer_dir, "segments": session.segments, "segment_duration": session.segment_duration}
        return None

    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]: return self._processes.get(task_id)

    async def _vlc_http_bridge(self, task_id: str, url: str, session: VLCSession):
        max_attempts = 20
        for attempt in range(max_attempts):
            try:
                await asyncio.sleep(0.5)
                connector = aiohttp.TCPConnector(force_close=True)
                timeout = aiohttp.ClientTimeout(total=None, connect=5, sock_read=60)
                async with aiohttp.ClientSession(timeout=timeout, connector=connector) as http_session:
                    async with http_session.get(url) as response:
                        if response.status == 200:
                            logger.info(f"VLC Bridge [{task_id}]: connected")
                            async for chunk, _ in response.content.iter_chunks():
                                session.dispatch(chunk)
                                if session.task.output_type == OutputType.HTTP_TS:
                                    await session.write_manual_chunk(chunk)
                            return
            except asyncio.CancelledError: break
            except: pass
            await asyncio.sleep(0.5)

    def get_active_count(self) -> int: return len(self._processes)

    async def generate_preview(self, url: str, protocol: StreamProtocol, fmt: PreviewFormat, width: int = 640, quality: int = 75) -> Optional[bytes]:
        """Генерация превью средствами VLC."""
        vlc_path = self._get_setting("binary_path", "cvlc")
        if url.startswith("udp://") and "@" not in url: 
            url = url.replace("udp://", "udp://@")
        
        if fmt == PreviewFormat.JPEG:
            ext = "jpg"
        elif fmt == PreviewFormat.PNG:
            ext = "png"
        elif fmt == PreviewFormat.TIFF:
            ext = "tif"
        else:
            ext = "jpg" # Fallback
            
        prefix = "snap"
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Настройка VLC для снятия одного скриншота
            # --scene-ratio=1000000 гарантирует, что мы не будем спамить файлами
            # --scene-replace перезаписывает файл, оставляя последний удачный кадр
            # --start-time=2 помогает пропустить черные кадры в начале
            cmd = [
                vlc_path,
                url,
                "--intf", "dummy",
                "--vout", "dummy",
                "--no-audio",
                "--no-video-title-show",
                "--start-time", "2",
                "--run-time", "5",
                "--video-filter", "scene",
                "--scene-format", ext,
                "--scene-prefix", prefix,
                "--scene-path", tmp_dir,
                "--scene-ratio", "1",
                "--scene-replace",
                "vlc://quit"
            ]
            
            try:
                logger.info(f"VLC Preview Start: {url}")
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                
                try:
                    # Даем VLC время на инициализацию и захват кадра
                    await asyncio.wait_for(process.wait(), timeout=20.0)
                except asyncio.TimeoutError:
                    try: process.kill(); await process.wait()
                    except: pass
                
                # Ищем файл в папке
                target_file = os.path.join(tmp_dir, f"{prefix}.{ext}")
                
                # VLC иногда добавляет префиксы или меняет имя, проверим содержимое папки
                if not os.path.exists(target_file):
                    for f in os.listdir(tmp_dir):
                        if f.endswith(ext):
                            target_file = os.path.join(tmp_dir, f)
                            break
                
                if os.path.exists(target_file):
                    with open(target_file, "rb") as f:
                        data = f.read()
                    
                    # Масштабирование
                    try:
                        from PIL import Image
                        import io
                        img = Image.open(io.BytesIO(data))
                        if img.width > width:
                            ratio = width / img.width
                            img = img.resize((width, int(img.height * ratio)), Image.LANCZOS)
                            
                            output = io.BytesIO()
                            format_map = {
                                PreviewFormat.JPEG: "JPEG",
                                PreviewFormat.PNG: "PNG",
                                PreviewFormat.WEBP: "WEBP",
                                PreviewFormat.AVIF: "AVIF",
                                PreviewFormat.TIFF: "TIFF",
                                PreviewFormat.GIF: "GIF",
                            }
                            img_format = format_map.get(fmt, "JPEG")
                            save_args = {"format": img_format}
                            if img_format in ["JPEG", "WEBP"]:
                                save_args["quality"] = quality
                            img.save(output, **save_args)
                            data = output.getvalue()
                    except:
                        pass
                        
                    return data
            except Exception as e:
                logger.error(f"VLC Preview error: {e}")
                
        return None
