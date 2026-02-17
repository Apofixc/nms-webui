"""Захват одного кадра по URL потока (HTTP/UDP). Бэкенды: builtin, FFmpeg, VLC, GStreamer."""
from __future__ import annotations

import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional, Tuple, Type

from backend.utils import find_executable


class CaptureBackend(ABC):
    """Абстрактный бэкенд захвата кадра по URL."""

    @classmethod
    def available(cls) -> bool:
        """Проверка, доступен ли бэкенд в системе."""
        raise NotImplementedError

    @abstractmethod
    def capture(
        self,
        url: str,
        *,
        timeout_sec: float = 10.0,
        output_format: str = "jpeg",
        jpeg_quality: Optional[int] = None,
    ) -> bytes:
        """Захватить один кадр. При ошибке — исключение или пустой bytes. jpeg_quality: 1–100 (None = по умолчанию)."""
        raise NotImplementedError


class FFmpegCaptureBackend(CaptureBackend):
    """Захват кадра через FFmpeg (subprocess). Поддерживает HTTP и UDP."""

    def __init__(
        self,
        ffmpeg_bin: str = "ffmpeg",
        analyzeduration_us: int = 500000,
        probesize: int = 500000,
        stimeout_us: int = 0,
        extra_args: Optional[str] = None,
    ):
        self.ffmpeg_bin = find_executable(ffmpeg_bin) or ffmpeg_bin
        self.analyzeduration_us = max(10000, min(30_000_000, analyzeduration_us))
        self.probesize = max(10000, min(50_000_000, probesize))
        self.stimeout_us = max(0, min(60_000_000, stimeout_us)) if stimeout_us else 0
        self.extra_args_list: list[str] = []
        if extra_args and isinstance(extra_args, str) and extra_args.strip():
            self.extra_args_list = extra_args.strip().split()

    @classmethod
    def available(cls, ffmpeg_bin: str = "ffmpeg", **kwargs: Any) -> bool:
        return find_executable(ffmpeg_bin) is not None

    def capture(
        self,
        url: str,
        *,
        timeout_sec: float = 10.0,
        output_format: str = "jpeg",
        jpeg_quality: Optional[int] = None,
    ) -> bytes:
        ext = "jpg" if output_format == "jpeg" else output_format
        out_file = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
        out_file.close()
        # UDP или локальный .ts файл (от builtin): формат mpegts задаём явно
        is_udp = isinstance(url, str) and url.strip().lower().startswith("udp")
        is_ts_file = isinstance(url, str) and url.lower().endswith(".ts")
        use_mpegts_input = is_udp or is_ts_file
        wait_sec = (timeout_sec + 10.0) if is_udp else timeout_sec
        try:
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-timeout", str(int(wait_sec * 1_000_000)),
                "-protocol_whitelist", "file,http,https,tcp,tls,udp",
            ]
            if self.stimeout_us > 0:
                cmd.extend(["-stimeout", str(self.stimeout_us)])
            cmd.extend(self.extra_args_list)
            if is_udp:
                cmd.extend([
                    "-analyzeduration", str(self.analyzeduration_us),
                    "-probesize", str(self.probesize),
                    "-f", "mpegts", "-i", url,
                ])
            elif use_mpegts_input:
                cmd.extend(["-analyzeduration", str(self.analyzeduration_us), "-probesize", str(self.probesize), "-f", "mpegts", "-i", url])
            else:
                cmd.extend(["-i", url])
            if output_format == "jpeg" and jpeg_quality is not None:
                # FFmpeg -q:v для JPEG: 2–31 (меньше — лучше качество). Маппинг 100→2, 1→31
                q = max(1, min(100, jpeg_quality))
                qv = round(2 + (31 - 2) * (100 - q) / 99) if q < 100 else 2
                cmd.extend(["-q:v", str(qv)])
            cmd.extend([
                "-vframes", "1",
                "-f", "image2",
                out_file.name,
            ])
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=wait_sec + 2,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg failed: {proc.stderr.decode(errors='replace') or proc.stdout.decode(errors='replace')}"
                )
            return Path(out_file.name).read_bytes()
        finally:
            Path(out_file.name).unlink(missing_ok=True)


class VLCCaptureBackend(CaptureBackend):
    """Захват кадра через VLC (subprocess). Резервный вариант."""

    def __init__(
        self,
        vlc_bin: str = "vlc",
        run_time_sec: int = 2,
        scene_ratio: int = 1,
        network_caching_ms: int = 1000,
    ):
        self.vlc_bin = find_executable(vlc_bin) or vlc_bin
        self.run_time_sec = max(1, min(30, run_time_sec))
        self.scene_ratio = max(1, min(100, scene_ratio))
        self.network_caching_ms = max(0, min(60000, network_caching_ms))

    @classmethod
    def available(cls, vlc_bin: str = "vlc", **kwargs: Any) -> bool:
        return find_executable(vlc_bin) is not None

    def capture(
        self,
        url: str,
        *,
        timeout_sec: float = 10.0,
        output_format: str = "jpeg",
        jpeg_quality: Optional[int] = None,
    ) -> bytes:
        out_dir = tempfile.mkdtemp()
        out_path = Path(out_dir) / f"frame.{output_format}"
        try:
            cmd = [
                self.vlc_bin,
                "-I", "dummy",
                "--no-video-title-show",
                f"--network-caching={self.network_caching_ms}",
                f"--run-time={self.run_time_sec}",
                "--vout=vdummy",
                "--no-audio",
                f"--scene-format={output_format}",
                f"--scene-path={out_dir}",
                f"--scene-ratio={self.scene_ratio}",
                url,
                "vlc://quit",
            ]
            subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout_sec + 5,
            )
            if out_path.exists():
                return out_path.read_bytes()
            raise RuntimeError("VLC did not produce output frame")
        finally:
            import shutil as _shutil
            _shutil.rmtree(out_dir, ignore_errors=True)


class BuiltinCaptureBackend(CaptureBackend):
    """
    Захват без внешних процессов.
    - HTTP: GET URL; если ответ image/* — возвращаем тело как кадр.
    - UDP: пишем поток во временный файл (встроенный приём), затем декодируем один кадр
      через первый доступный бэкенд из fallback_chain (FFmpeg, VLC, GStreamer).
    """

    def __init__(self, fallback_chain: Optional[List[Tuple[Type[CaptureBackend], dict]]] = None):
        self._fallback_chain = fallback_chain or []

    @classmethod
    def available(cls, **kwargs: Any) -> bool:
        return True

    def _is_http(self, url: str) -> bool:
        return url.strip().lower().startswith("http://") or url.strip().lower().startswith("https://")

    def _is_udp(self, url: str) -> bool:
        return url.strip().lower().startswith("udp://")

    def capture(
        self,
        url: str,
        *,
        timeout_sec: float = 10.0,
        output_format: str = "jpeg",
        jpeg_quality: Optional[int] = None,
    ) -> bytes:
        if self._is_http(url):
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "NMS-WebUI/1.0"})
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                ct = (resp.headers.get("Content-Type") or "").lower()
                if "image/" not in ct and "image/" not in (resp.headers.get("Content-Type") or ""):
                    raise RuntimeError(f"Builtin: URL не вернул изображение (Content-Type: {ct})")
                data = resp.read()
            if not data:
                raise RuntimeError("Builtin: пустой ответ")
            if output_format != "jpeg" or (jpeg_quality is not None and jpeg_quality != 100):
                return data
            return data

        if self._is_udp(url):
            from backend.stream.udp_to_http import stream_udp_to_file_sync
            out_file = tempfile.NamedTemporaryFile(suffix=".ts", delete=False)
            out_file.close()
            try:
                stream_udp_to_file_sync(url, out_file.name, duration_sec=min(4.0, timeout_sec + 1), max_bytes=1024 * 1024)
                path = out_file.name
                if Path(path).stat().st_size < 188:
                    raise RuntimeError("Builtin: недостаточно данных UDP для кадра")
                for backend_cls, kwargs in self._fallback_chain:
                    if not backend_cls.available(**kwargs):
                        continue
                    try:
                        inst = backend_cls(**kwargs)
                        return inst.capture(
                            path,
                            timeout_sec=timeout_sec,
                            output_format=output_format,
                            jpeg_quality=jpeg_quality,
                        )
                    except Exception:
                        continue
                raise RuntimeError("Builtin: ни один бэкенд из цепочки не смог декодировать кадр из UDP")
            finally:
                Path(out_file.name).unlink(missing_ok=True)

        raise RuntimeError("Builtin: поддерживаются только http(s) и udp URL")


class GStreamerCaptureBackend(CaptureBackend):
    """Захват кадра через GStreamer (gst-launch-1.0). Резервный вариант."""

    def __init__(self, gst_launch: str = "gst-launch-1.0", buffer_size: int = -1):
        self.gst_launch = find_executable(gst_launch) or gst_launch
        self.buffer_size = buffer_size if isinstance(buffer_size, int) and buffer_size > 0 else -1

    @classmethod
    def available(cls, gst_launch: str = "gst-launch-1.0", **kwargs: Any) -> bool:
        return find_executable(gst_launch) is not None

    def capture(
        self,
        url: str,
        *,
        timeout_sec: float = 10.0,
        output_format: str = "jpeg",
        jpeg_quality: Optional[int] = None,
    ) -> bytes:
        out_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        out_file.close()
        try:
            # uridecodebin -> videoconvert -> jpegenc -> filesink
            uri_part = f"uridecodebin uri={url!r}"
            if self.buffer_size > 0:
                uri_part += f" buffer-size={self.buffer_size}"
            pipeline = (
                f"{uri_part} ! "
                "videoconvert ! "
                "jpegenc ! "
                f"filesink location={out_file.name}"
            )
            cmd = [self.gst_launch, "-e", pipeline]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout_sec + 2,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"GStreamer failed: {proc.stderr.decode(errors='replace')}"
                )
            data = Path(out_file.name).read_bytes()
            if not data:
                raise RuntimeError("GStreamer produced empty output")
            return data
        finally:
            Path(out_file.name).unlink(missing_ok=True)


# Порядок попытки бэкендов при выборе «auto» (builtin первым — без внешних процессов)
DEFAULT_CAPTURE_BACKENDS: list[type[CaptureBackend]] = [
    BuiltinCaptureBackend,
    FFmpegCaptureBackend,
    VLCCaptureBackend,
    GStreamerCaptureBackend,
]

# Соответствие имени настройки → класс бэкенда (для ручного выбора)
CAPTURE_BACKEND_BY_NAME: dict[str, type[CaptureBackend]] = {
    "builtin": BuiltinCaptureBackend,
    "ffmpeg": FFmpegCaptureBackend,
    "vlc": VLCCaptureBackend,
    "gstreamer": GStreamerCaptureBackend,
}

# Параметр конструктора и значение по умолчанию для каждого бэкенда (для ручных настроек bin)
# builtin не имеет bin; fallback_chain подставляется при создании фасада.
CAPTURE_BACKEND_INIT_PARAM: dict[str, tuple[str, str]] = {
    "builtin": ("fallback_chain", ""),
    "ffmpeg": ("ffmpeg_bin", "ffmpeg"),
    "vlc": ("vlc_bin", "vlc"),
    "gstreamer": ("gst_launch", "gst-launch-1.0"),
}


def get_capture_backends_for_setting(setting: str) -> list[type[CaptureBackend]]:
    """
    По значению настройки (auto | ffmpeg | vlc | gstreamer) вернуть список классов бэкендов.
    auto — порядок по умолчанию; иначе один выбранный бэкенд.
    """
    if not setting or setting == "auto":
        return list(DEFAULT_CAPTURE_BACKENDS)
    cls = CAPTURE_BACKEND_BY_NAME.get(setting.lower())
    return [cls] if cls else list(DEFAULT_CAPTURE_BACKENDS)


def get_available_capture_backends(backend_options: Optional[dict] = None) -> list[str]:
    """
    Список имён бэкендов захвата, доступных в системе.
    backend_options: { "ffmpeg": {"bin": "ffmpeg"}, ... } — при указании проверка с учётом настроек.
    """
    if not backend_options:
        return [name for name, cls in CAPTURE_BACKEND_BY_NAME.items() if cls.available()]
    result = []
    for name, cls in CAPTURE_BACKEND_BY_NAME.items():
        param, default = CAPTURE_BACKEND_INIT_PARAM.get(name, ("bin", "ffmpeg"))
        opts = backend_options.get(name) or {}
        bin_val = opts.get("bin") or default
        kwargs = {param: bin_val}
        if cls.available(**kwargs):
            result.append(name)
    return result


def _backends_with_options(
    backend_classes: list[type[CaptureBackend]],
    backend_options: dict,
) -> list[tuple[type[CaptureBackend], dict]]:
    """Преобразовать список классов в список (класс, kwargs) с учётом backend_options."""
    name_to_cls = {v: k for k, v in CAPTURE_BACKEND_BY_NAME.items()}
    result = []
    for backend_cls in backend_classes:
        name = name_to_cls.get(backend_cls)
        if name is None:
            result.append((backend_cls, {}))
            continue
        if name == "builtin":
            result.append((backend_cls, {}))
            continue
        param, default = CAPTURE_BACKEND_INIT_PARAM.get(name, ("bin", "ffmpeg"))
        opts = backend_options.get(name) or {}
        bin_val = opts.get("bin") or default
        kwargs = {param: bin_val}
        for k, v in opts.items():
            if k != "bin" and v is not None:
                kwargs[k] = v
        result.append((backend_cls, kwargs))
    return result


def _backend_item(item: Any) -> Tuple[type[CaptureBackend], dict]:
    if isinstance(item, tuple):
        return item[0], item[1]
    return item, {}


class StreamFrameCapture:
    """
    Фасад захвата одного кадра по URL потока (HTTP/UDP).
    При capture() перебирает бэкенды по порядку (builtin → FFmpeg → VLC → GStreamer).
    backends: список (класс, kwargs); для builtin fallback_chain подставляется в __init__.
    """

    def __init__(
        self,
        backends: Optional[list[type[CaptureBackend]] | list[tuple[type[CaptureBackend], dict]]] = None,
    ):
        if backends and len(backends) > 0 and isinstance(backends[0], tuple):
            self._backends = list(backends)
        else:
            classes = backends or DEFAULT_CAPTURE_BACKENDS
            self._backends = [(c, {}) for c in classes]
        if self._backends:
            backend_cls, kwargs = _backend_item(self._backends[0])
            if backend_cls is BuiltinCaptureBackend:
                kwargs = dict(kwargs)
                kwargs["fallback_chain"] = self._backends[1:]
                self._backends[0] = (backend_cls, kwargs)
        self._backend: Optional[CaptureBackend] = None

    @property
    def available(self) -> bool:
        """Есть ли хотя бы один доступный бэкенд."""
        for item in self._backends:
            backend_cls, kwargs = _backend_item(item)
            if backend_cls is BuiltinCaptureBackend:
                return True
            if backend_cls.available(**kwargs):
                return True
        return False

    @property
    def backend_name(self) -> str:
        """Имя последнего успешно использованного бэкенда."""
        if self._backend is None:
            return "none"
        return self._backend.__class__.__name__.replace("CaptureBackend", "").lower()

    def capture(
        self,
        url: str,
        *,
        timeout_sec: float = 10.0,
        output_format: str = "jpeg",
        jpeg_quality: Optional[int] = None,
    ) -> bytes:
        """
        Захватить один кадр по URL. Перебирает бэкенды по порядку до первого успеха.
        """
        last_error: Optional[Exception] = None
        for item in self._backends:
            backend_cls, kwargs = _backend_item(item)
            if not backend_cls.available(**kwargs):
                continue
            try:
                inst = backend_cls(**kwargs)
                data = inst.capture(
                    url,
                    timeout_sec=timeout_sec,
                    output_format=output_format,
                    jpeg_quality=jpeg_quality,
                )
                self._backend = inst
                return data
            except Exception as e:
                last_error = e
                continue
        raise RuntimeError(
            last_error if last_error else "No capture backend available. Install ffmpeg, vlc, or gstreamer."
        )
