"""Настройки WebUI по модулям. Хранятся в JSON рядом с instances."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from backend.config import _instances_path

# Значения по умолчанию по модулям (все ключи, чтобы при добавлении новых не ломать старые файлы)
DEFAULT_MODULES = {
    "stream": {
        "capture": {
            "backend": "auto",
            "timeout_sec": 10.0,
            # Общее качество JPEG по умолчанию для превью (1–100)
            "jpeg_quality": 90,
            "backends": {
                "ffmpeg": {
                    "bin": "ffmpeg",
                    "analyzeduration_us": 500000,
                    "probesize": 500000,
                    "stimeout_us": 0,
                    "extra_args": "",
                },
                "vlc": {"bin": "vlc", "run_time_sec": 2, "scene_ratio": 1, "network_caching_ms": 1000},
                "gstreamer": {"bin": "gst-launch-1.0", "buffer_size": -1},
            },
        },
        "playback_udp": {
            "backend": "auto",
            "output_format": "http_ts",
            "backends": {
                "ffmpeg": {
                    "bin": "ffmpeg",
                    "buffer_kb": 1024,
                    "extra_args": "",
                    "analyzeduration_us": 500000,
                    "probesize": 500000,
                    "hls_time": 2,
                    "hls_list_size": 5,
                },
                "vlc": {"bin": "vlc", "buffer_kb": 1024, "hls_time": 2, "hls_list_size": 5},
                "gstreamer": {"bin": "gst-launch-1.0", "buffer_kb": 1024, "hls_time": 2, "hls_list_size": 5},
                "tsduck": {"bin": "tsp", "buffer_kb": 1024, "hls_time": 2, "hls_list_size": 5},
                "astra": {"relay_url": "http://localhost:8000"},
            },
        },
    },
}

VALID_CAPTURE_BACKENDS = ("auto", "builtin", "ffmpeg", "vlc", "gstreamer")
VALID_PLAYBACK_UDP_BACKENDS = (
    "auto",
    "ffmpeg",
    "vlc",
    "astra",
    "gstreamer",
    "tsduck",
    "udp_proxy",
)

VALID_PLAYBACK_UDP_OUTPUT_FORMATS = ("http_ts", "hls")


def _webui_settings_path() -> Path:
    return _instances_path().parent / "webui_settings.json"


def _deep_merge(base: dict, override: dict) -> dict:
    """Рекурсивно подмешать override в base (без замены всего узла)."""
    out = deepcopy(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def get_webui_settings() -> dict[str, Any]:
    """Загрузить настройки WebUI. Всегда возвращает структуру с ключом modules."""
    path = _webui_settings_path()
    if not path.exists():
        return {"modules": deepcopy(DEFAULT_MODULES)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    file_modules = data.get("modules")
    if not isinstance(file_modules, dict):
        file_modules = {}
    # Миграция: старый формат с capture_backend / playback_udp_backend на верхнем уровне
    if "capture_backend" in data and data["capture_backend"] in VALID_CAPTURE_BACKENDS:
        stream = file_modules.setdefault("stream", {})
        cap = dict(stream.get("capture") or {})
        cap["backend"] = data["capture_backend"]
        stream["capture"] = cap
    if "playback_udp_backend" in data and data["playback_udp_backend"] in VALID_PLAYBACK_UDP_BACKENDS:
        stream = file_modules.setdefault("stream", {})
        pb = dict(stream.get("playback_udp") or {})
        pb["backend"] = data["playback_udp_backend"]
        stream["playback_udp"] = pb
    modules = _deep_merge(deepcopy(DEFAULT_MODULES), file_modules)
    return {"modules": modules}


def save_webui_settings(update: dict[str, Any]) -> None:
    """Сохранить настройки. update может содержать только modules (или часть); остальное мержится."""
    path = _webui_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    current = get_webui_settings()
    if "modules" in update and isinstance(update["modules"], dict):
        current["modules"] = _deep_merge(current["modules"], update["modules"])
    # Нормализация значений
    stream = current["modules"].setdefault("stream", {})
    cap = stream.setdefault("capture", {})
    if cap.get("backend") not in VALID_CAPTURE_BACKENDS:
        cap["backend"] = DEFAULT_MODULES["stream"]["capture"]["backend"]
    if isinstance(cap.get("timeout_sec"), (int, float)):
        cap["timeout_sec"] = max(1.0, min(120.0, float(cap["timeout_sec"])))
    else:
        cap["timeout_sec"] = DEFAULT_MODULES["stream"]["capture"]["timeout_sec"]
    if cap.get("jpeg_quality") is not None:
        q = cap["jpeg_quality"]
        if isinstance(q, (int, float)):
            cap["jpeg_quality"] = max(1, min(100, int(q)))
        else:
            cap["jpeg_quality"] = None
    pb = stream.setdefault("playback_udp", {})
    if pb.get("backend") not in VALID_PLAYBACK_UDP_BACKENDS:
        pb["backend"] = DEFAULT_MODULES["stream"]["playback_udp"]["backend"]
    # Нормализация формата выхода для UDP (http_ts | hls)
    fmt = pb.get("output_format")
    if fmt not in VALID_PLAYBACK_UDP_OUTPUT_FORMATS:
        pb["output_format"] = DEFAULT_MODULES["stream"]["playback_udp"]["output_format"]
    # Нормализация backends: только известные ключи, bin — непустая строка
    for mod_key, backend_keys in (
        ("capture", ("ffmpeg", "vlc", "gstreamer")),
        ("playback_udp", ("ffmpeg", "vlc", "gstreamer", "tsduck", "astra")),
    ):
        sub = stream.setdefault(mod_key, {})
        if not isinstance(sub, dict):
            sub = {}
            stream[mod_key] = sub
        b = sub.setdefault("backends", {})
        if not isinstance(b, dict):
            b = {}
        default_backs = DEFAULT_MODULES["stream"][mod_key].get("backends") or {}
        default_bin = {"ffmpeg": "ffmpeg", "vlc": "vlc", "gstreamer": "gst-launch-1.0", "tsduck": "tsp"}
        normalized = {}
        for k in backend_keys:
            def_k = default_backs.get(k) or {}
            cur = b.get(k) if isinstance(b.get(k), dict) else {}
            out = dict(def_k)
            out.update((kk, v) for kk, v in cur.items() if v is not None and (not isinstance(v, str) or v != "" or kk in ("bin", "relay_url")))
            if k in default_bin:
                bin_val = out.get("bin")
                if not isinstance(bin_val, str) or not str(bin_val).strip():
                    out["bin"] = def_k.get("bin") or default_bin.get(k, "ffmpeg")
                else:
                    out["bin"] = str(bin_val).strip()
            elif mod_key == "playback_udp" and k == "astra":
                rurl = out.get("relay_url")
                if not isinstance(rurl, str) or not rurl.strip():
                    out["relay_url"] = def_k.get("relay_url") or "http://localhost:8000"
                else:
                    out["relay_url"] = str(rurl).strip()
            if mod_key == "capture" and k == "ffmpeg":
                for num_key, lo, hi in (("analyzeduration_us", 10000, 30_000_000), ("probesize", 10000, 50_000_000)):
                    v = out.get(num_key)
                    if isinstance(v, (int, float)):
                        out[num_key] = max(lo, min(hi, int(v)))
                    else:
                        out[num_key] = def_k.get(num_key, 500000)
                v = out.get("stimeout_us")
                if isinstance(v, (int, float)) and int(v) >= 0:
                    out["stimeout_us"] = min(60_000_000, int(v))
                else:
                    out["stimeout_us"] = def_k.get("stimeout_us", 0)
                if "extra_args" not in out or not isinstance(out.get("extra_args"), str):
                    out["extra_args"] = def_k.get("extra_args", "")
            if mod_key == "capture" and k == "vlc":
                for num_key, lo, hi, d in (("run_time_sec", 1, 30, 2), ("scene_ratio", 1, 100, 1)):
                    v = out.get(num_key)
                    if isinstance(v, (int, float)):
                        out[num_key] = max(lo, min(hi, int(v)))
                    else:
                        out[num_key] = def_k.get(num_key, d)
                v = out.get("network_caching_ms")
                if isinstance(v, (int, float)):
                    out["network_caching_ms"] = max(0, min(60000, int(v)))
                else:
                    out["network_caching_ms"] = def_k.get("network_caching_ms", 1000)
            if mod_key == "capture" and k == "gstreamer":
                v = out.get("buffer_size")
                if isinstance(v, (int, float)) and int(v) >= -1:
                    out["buffer_size"] = int(v) if int(v) <= 0 else min(50_000_000, int(v))
                else:
                    out["buffer_size"] = def_k.get("buffer_size", -1)
            if mod_key == "playback_udp" and k == "ffmpeg":
                v = out.get("buffer_kb")
                if isinstance(v, (int, float)):
                    out["buffer_kb"] = max(64, min(65536, int(v)))
                else:
                    out["buffer_kb"] = def_k.get("buffer_kb", 1024)
                if "extra_args" not in out or not isinstance(out.get("extra_args"), str):
                    out["extra_args"] = def_k.get("extra_args", "")
                for num_key, lo, hi in (("analyzeduration_us", 10000, 30_000_000), ("probesize", 10000, 50_000_000)):
                    v = out.get(num_key)
                    if isinstance(v, (int, float)):
                        out[num_key] = max(lo, min(hi, int(v)))
                    else:
                        out[num_key] = def_k.get(num_key, 500000)
                v = out.get("hls_time")
                if isinstance(v, (int, float)):
                    out["hls_time"] = max(1, min(30, int(v)))
                else:
                    out["hls_time"] = def_k.get("hls_time", 2)
                v = out.get("hls_list_size")
                if isinstance(v, (int, float)):
                    out["hls_list_size"] = max(2, min(30, int(v)))
                else:
                    out["hls_list_size"] = def_k.get("hls_list_size", 5)
            if mod_key == "playback_udp" and k in ("vlc", "gstreamer", "tsduck"):
                v = out.get("buffer_kb")
                if isinstance(v, (int, float)):
                    out["buffer_kb"] = max(64, min(65536, int(v)))
                else:
                    out["buffer_kb"] = def_k.get("buffer_kb", 1024)
                for hkey, hlo, hhi, hdef in (("hls_time", 1, 30, 2), ("hls_list_size", 2, 30, 5)):
                    v = out.get(hkey)
                    if isinstance(v, (int, float)):
                        out[hkey] = max(hlo, min(hhi, int(v)))
                    else:
                        out[hkey] = def_k.get(hkey, hdef)
            normalized[k] = out
        sub["backends"] = normalized
    path.write_text(json.dumps({"modules": current["modules"]}, indent=2, ensure_ascii=False), encoding="utf-8")


def get_stream_capture_backend() -> str:
    """Бэкенд захвата кадра из настроек (stream.capture.backend)."""
    return get_webui_settings()["modules"].get("stream", {}).get("capture", {}).get("backend", "auto")


def get_stream_capture_options() -> dict[str, Any]:
    """Параметры захвата кадра: timeout_sec, jpeg_quality."""
    cap = get_webui_settings()["modules"].get("stream", {}).get("capture", {})
    return {
        "timeout_sec": cap.get("timeout_sec", 10.0),
        "jpeg_quality": cap.get("jpeg_quality"),
    }


def get_stream_playback_udp_backend() -> str:
    """Бэкенд воспроизведения UDP из настроек (stream.playback_udp.backend)."""
    return get_webui_settings()["modules"].get("stream", {}).get("playback_udp", {}).get("backend", "auto")


def get_stream_playback_udp_output_format() -> str:
    """Формат вывода для UDP воспроизведения: http_ts | hls."""
    pb = get_webui_settings()["modules"].get("stream", {}).get("playback_udp", {})
    fmt = pb.get("output_format", "http_ts")
    return fmt if fmt in VALID_PLAYBACK_UDP_OUTPUT_FORMATS else "http_ts"


def get_stream_capture_backend_options() -> dict[str, dict[str, Any]]:
    """Параметры по бэкендам захвата: bin и опции (analyzeduration_us, probesize, run_time_sec, scene_ratio)."""
    cap = get_webui_settings()["modules"].get("stream", {}).get("capture", {})
    b = cap.get("backends") or {}
    default = DEFAULT_MODULES["stream"]["capture"].get("backends") or {}
    def_ff = default.get("ffmpeg") or {}
    def_vlc = default.get("vlc") or {}
    def_gst = default.get("gstreamer") or {}
    ff = b.get("ffmpeg") or {}
    vl = b.get("vlc") or {}
    gs = b.get("gstreamer") or {}
    return {
        "ffmpeg": {
            "bin": (ff.get("bin") or def_ff.get("bin") or "ffmpeg").strip(),
            "analyzeduration_us": ff.get("analyzeduration_us") if ff.get("analyzeduration_us") is not None else def_ff.get("analyzeduration_us", 500000),
            "probesize": ff.get("probesize") if ff.get("probesize") is not None else def_ff.get("probesize", 500000),
            "stimeout_us": ff.get("stimeout_us") if ff.get("stimeout_us") is not None else def_ff.get("stimeout_us", 0),
            "extra_args": (ff.get("extra_args") or def_ff.get("extra_args") or "") if isinstance(ff.get("extra_args"), str) else (def_ff.get("extra_args") or ""),
        },
        "vlc": {
            "bin": (vl.get("bin") or def_vlc.get("bin") or "vlc").strip(),
            "run_time_sec": vl.get("run_time_sec") if vl.get("run_time_sec") is not None else def_vlc.get("run_time_sec", 2),
            "scene_ratio": vl.get("scene_ratio") if vl.get("scene_ratio") is not None else def_vlc.get("scene_ratio", 1),
            "network_caching_ms": vl.get("network_caching_ms") if vl.get("network_caching_ms") is not None else def_vlc.get("network_caching_ms", 1000),
        },
        "gstreamer": {
            "bin": (gs.get("bin") or def_gst.get("bin") or "gst-launch-1.0").strip(),
            "buffer_size": gs.get("buffer_size") if gs.get("buffer_size") is not None else def_gst.get("buffer_size", -1),
        },
    }


def get_stream_playback_udp_backend_options() -> dict[str, dict[str, Any]]:
    """Параметры по бэкендам воспроизведения UDP: bin, buffer_kb, extra_args (для ffmpeg)."""
    pb = get_webui_settings()["modules"].get("stream", {}).get("playback_udp", {})
    b = pb.get("backends") or {}
    default = DEFAULT_MODULES["stream"]["playback_udp"].get("backends") or {}
    def_ff = default.get("ffmpeg") or {}
    ff = b.get("ffmpeg") or {}
    return {
        "ffmpeg": {
            "bin": (ff.get("bin") or def_ff.get("bin") or "ffmpeg").strip(),
            "buffer_kb": ff.get("buffer_kb") if ff.get("buffer_kb") is not None else def_ff.get("buffer_kb", 1024),
            "extra_args": (ff.get("extra_args") or def_ff.get("extra_args") or "") if isinstance(ff.get("extra_args"), str) else (def_ff.get("extra_args") or ""),
            "analyzeduration_us": ff.get("analyzeduration_us") if ff.get("analyzeduration_us") is not None else def_ff.get("analyzeduration_us", 500000),
            "probesize": ff.get("probesize") if ff.get("probesize") is not None else def_ff.get("probesize", 500000),
        },
        "vlc": {
            "bin": (b.get("vlc") or {}).get("bin") or (default.get("vlc") or {}).get("bin") or "vlc",
            "buffer_kb": (b.get("vlc") or {}).get("buffer_kb") if (b.get("vlc") or {}).get("buffer_kb") is not None else (default.get("vlc") or {}).get("buffer_kb", 1024),
        },
        "gstreamer": {
            "bin": (b.get("gstreamer") or {}).get("bin") or (default.get("gstreamer") or {}).get("bin") or "gst-launch-1.0",
            "buffer_kb": (b.get("gstreamer") or {}).get("buffer_kb") if (b.get("gstreamer") or {}).get("buffer_kb") is not None else (default.get("gstreamer") or {}).get("buffer_kb", 1024),
        },
        "tsduck": {
            "bin": (b.get("tsduck") or {}).get("bin") or (default.get("tsduck") or {}).get("bin") or "tsp",
            "buffer_kb": (b.get("tsduck") or {}).get("buffer_kb") if (b.get("tsduck") or {}).get("buffer_kb") is not None else (default.get("tsduck") or {}).get("buffer_kb", 1024),
        },
        "astra": {
            "relay_url": (b.get("astra") or {}).get("relay_url") or (default.get("astra") or {}).get("relay_url") or "http://localhost:8000",
        },
    }
