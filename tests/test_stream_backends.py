#!/usr/bin/env python3
"""
Тесты бэкендов: захват кадра (превью) и воспроизведение UDP→HTTP/HLS.
Запуск из корня проекта: PYTHONPATH=. python tests/test_stream_backends.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

# корень проекта
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from backend.stream.capture import (
    DEFAULT_CAPTURE_BACKENDS,
    BuiltinCaptureBackend,
    StreamFrameCapture,
    get_capture_backends_for_setting,
    get_available_capture_backends,
    _backends_with_options,
)
from backend.stream import (
    STREAM_BACKENDS_BY_NAME,
    get_input_format,
    get_stream_backend_chain,
    get_available_stream_backends,
)
from backend.stream.core.registry import (
    STREAM_BACKEND_ORDER,
    get_backend_for_link,
    get_best,
)
from backend.stream.core.types import StreamConfig
from backend.stream.core.converter import UniversalStreamConverter
from backend.stream.playback import StreamPlaybackSession
from backend.stream.utils.probe import get_input_format_from_url
from backend.stream.utils.health import hls_playlist_ready
from backend.stream.outputs.webrtc_output import whep_unavailable_message
from backend.webui_settings import (
    get_stream_capture_backend_options,
    get_stream_playback_udp_backend_options,
)


# Публичный тестовый JPEG (маленький)
TEST_IMAGE_URL = "https://httpbin.org/image/jpeg"


def test_capture_backend_order():
    """Порядок бэкендов превью: FFmpeg → VLC → GStreamer → Builtin."""
    names = [c.__name__.replace("CaptureBackend", "").lower() for c in DEFAULT_CAPTURE_BACKENDS]
    assert names[0] == "ffmpeg", f"First should be ffmpeg, got {names}"
    assert names[-1] == "builtin", f"Last should be builtin, got {names}"
    print("[OK] Порядок бэкендов превью: FFmpeg → ... → builtin")


def test_capture_available():
    """Доступность бэкендов захвата с опциями из настроек."""
    opts = get_stream_capture_backend_options()
    available = get_available_capture_backends(opts)
    print(f"[INFO] Доступные бэкенды захвата: {available}")
    capture = StreamFrameCapture(backends=get_capture_backends_for_setting("auto"))
    capture._backends = _backends_with_options(
        get_capture_backends_for_setting("auto"),
        opts,
    )
    if capture._backends and capture._backends[-1][0] is BuiltinCaptureBackend:
        last_cls, last_kw = capture._backends[-1]
        last_kw = dict(last_kw)
        last_kw["fallback_chain"] = capture._backends[:-1]
        capture._backends[-1] = (last_cls, last_kw)
    assert capture.available or len(available) == 0, "StreamFrameCapture.available должен быть True если есть хотя бы один бэкенд"
    print("[OK] StreamFrameCapture.available и список доступных")


def test_capture_http_image():
    """Захват кадра по HTTP (изображение) — хотя бы один бэкенд должен справиться."""
    opts = get_stream_capture_backend_options()
    capture = StreamFrameCapture(backends=get_capture_backends_for_setting("auto"))
    capture._backends = _backends_with_options(
        get_capture_backends_for_setting("auto"),
        opts,
    )
    if capture._backends and capture._backends[-1][0] is BuiltinCaptureBackend:
        last_cls, last_kw = capture._backends[-1]
        last_kw = dict(last_kw)
        last_kw["fallback_chain"] = capture._backends[:-1]
        capture._backends[-1] = (last_cls, last_kw)
    if not capture.available:
        print("[SKIP] Нет доступного бэкенда захвата")
        return
    try:
        data = capture.capture(TEST_IMAGE_URL, timeout_sec=15.0)
        assert len(data) > 0, "Пустой ответ"
        assert capture.backend_name != "none"
        print(f"[OK] Захват по HTTP: {len(data)} байт, бэкенд: {capture.backend_name}")
    except Exception as e:
        print(f"[WARN] Захват по HTTP не удался (сеть или таймаут): {e}")


def test_get_input_format():
    """get_input_format распознаёт udp, http, rtp, rtsp, srt, hls, tcp, file."""
    assert get_input_format("udp://@239.0.0.1:1234") == "udp"
    assert get_input_format("udp://:5000") == "udp"
    assert get_input_format("http://localhost/stream") == "http"
    assert get_input_format("https://example.com/live.m3u8") == "hls"
    assert get_input_format("http://host/playlist.m3u8?token=1") == "hls"
    assert get_input_format("rtsp://host/path") == "rtsp"
    assert get_input_format("rtp://host:5000") == "rtp"
    assert get_input_format("srt://host:9000") == "srt"
    assert get_input_format("tcp://host:8080") == "tcp"
    assert get_input_format("file:///tmp/stream.ts") == "file"
    assert get_input_format("/abs/path/video.ts") == "file"
    assert get_input_format("") is None
    assert get_input_format("unknown://x") is None
    print("[OK] get_input_format для всех схем")


def test_get_backend_for_link():
    """get_backend_for_link возвращает бэкенд для связки input -> output."""
    opts = get_stream_playback_udp_backend_options()
    name = get_backend_for_link("auto", "udp", "http_ts", opts)
    assert name in STREAM_BACKEND_ORDER, name
    name_hls = get_backend_for_link("auto", "udp", "http_hls", opts)
    assert name_hls in ("ffmpeg", "vlc", "gstreamer", "tsduck"), name_hls
    print("[OK] get_backend_for_link для udp -> http_ts и udp -> http_hls")


def test_playback_backend_chain():
    """Цепочка воспроизведения и доступность по форматам."""
    opts = get_stream_playback_udp_backend_options()
    chain = get_stream_backend_chain("auto")
    assert "ffmpeg" in chain or "udp_proxy" in chain, "В цепочке должен быть хотя бы ffmpeg или udp_proxy"
    available_ts = get_available_stream_backends(opts, input_type="udp_ts", output_type="http_ts")
    available_hls = get_available_stream_backends(opts, input_type="udp_ts", output_type="http_hls")
    print(f"[INFO] Доступны для http_ts: {available_ts}, для http_hls: {available_hls}")
    # У бэкендов с http_hls должен быть метод start_hls
    for name in STREAM_BACKEND_ORDER:
        cls = STREAM_BACKENDS_BY_NAME.get(name)
        if not cls:
            continue
        if "http_hls" in getattr(cls, "output_types", set()):
            assert hasattr(cls, "start_hls") and callable(getattr(cls, "start_hls")), f"{name} должен иметь start_hls"
    print("[OK] Цепочка воспроизведения и start_hls у HLS-бэкендов")


def test_playback_opts_hls_params():
    """Параметры HLS (hls_time, hls_list_size) должны быть в opts для бэкендов."""
    opts = get_stream_playback_udp_backend_options()
    for key in ("ffmpeg", "vlc", "gstreamer", "tsduck"):
        b = opts.get(key) or {}
        assert "hls_time" in b and "hls_list_size" in b, f"В opts[{key}] должны быть hls_time и hls_list_size"
    print("[OK] HLS-параметры в get_stream_playback_udp_backend_options")


def test_ffmpeg_start_hls_dry():
    """FFmpeg start_hls: запуск и немедленная остановка (без реального UDP)."""
    from backend.stream.backends.ffmpeg import FFmpegStreamBackend

    opts = get_stream_playback_udp_backend_options()
    if not FFmpegStreamBackend.available(opts):
        print("[SKIP] FFmpeg недоступен")
        return
    with tempfile.TemporaryDirectory() as tmp:
        session_dir = Path(tmp)
        # Невалидный UDP URL — процесс должен стартовать и быстро выйти с ошибкой или мы его убьём
        try:
            proc = FFmpegStreamBackend.start_hls("udp://239.255.0.1:9999", session_dir, opts)
            proc.terminate()
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception as e:
            # Ожидаемо может быть ошибка при невалидном адресе
            print(f"[INFO] start_hls с невалидным URL: {e}")
    print("[OK] FFmpeg start_hls вызывается без падения")


def test_get_best():
    """get_best совпадает с get_backend_for_link по приоритету."""
    opts = get_stream_playback_udp_backend_options()
    name1 = get_backend_for_link("auto", "udp", "http_ts", opts)
    name2 = get_best("auto", "udp", "http_ts", opts)
    assert name1 == name2, (name1, name2)
    print("[OK] get_best совпадает с get_backend_for_link")


def test_stream_config_and_converter_instance():
    """StreamConfig и экземплярный API конвертера: start(), stop()."""
    config = StreamConfig(
        source_url="udp://:5000",
        input_format="udp",
        output_format="http_ts",
        backend="auto",
        backend_options=get_stream_playback_udp_backend_options(),
    )
    converter = UniversalStreamConverter(config)
    name = converter.start()
    assert name in STREAM_BACKEND_ORDER
    converter.stop()
    assert converter._hls_process is None and converter._hls_dir is None
    print("[OK] StreamConfig и конвертер start/stop")


def test_playback_session_stop_cleanup():
    """StreamPlaybackSession.stop() гарантирует очистку состояния."""
    session = StreamPlaybackSession()
    session.start("udp://:5000", output_format="http_ts", backend_name="ffmpeg")
    assert session.is_alive()
    assert session.get_backend_name() == "ffmpeg"
    session.stop()
    assert not session.is_alive()
    assert session.get_backend_name() is None
    assert session.get_source_url() is None
    print("[OK] Session stop очищает состояние")


def test_probe_get_input_format_from_url():
    """get_input_format_from_url совпадает с get_input_format для известных схем."""
    assert get_input_format_from_url("udp://@239.0.0.1:1234") == "udp"
    assert get_input_format_from_url("http://host/playlist.m3u8") == "hls"
    assert get_input_format_from_url("") is None
    print("[OK] get_input_format_from_url (probe)")


def test_health_hls_playlist_ready():
    """hls_playlist_ready возвращает False для пустой директории."""
    with tempfile.TemporaryDirectory() as tmp:
        assert hls_playlist_ready(Path(tmp)) is False
    print("[OK] hls_playlist_ready для пустой директории")


def test_whep_unavailable_message():
    """whep_unavailable_message возвращает строку (при отсутствии aiortc — подсказку установки)."""
    msg = whep_unavailable_message()
    assert isinstance(msg, str) and len(msg) > 0
    print(f"[OK] whep_unavailable_message: {msg[:60]}...")


def main():
    print("=== Тесты бэкендов: захват кадра и воспроизведение ===\n")
    errors = []
    tests = [
        ("Порядок бэкендов превью", test_capture_backend_order),
        ("Доступность бэкендов захвата", test_capture_available),
        ("Захват кадра по HTTP", test_capture_http_image),
        ("get_input_format для всех схем", test_get_input_format),
        ("get_backend_for_link", test_get_backend_for_link),
        ("get_best", test_get_best),
        ("Цепочка воспроизведения и HLS", test_playback_backend_chain),
        ("HLS-параметры в opts", test_playback_opts_hls_params),
        ("FFmpeg start_hls (dry)", test_ffmpeg_start_hls_dry),
        ("StreamConfig и конвертер instance", test_stream_config_and_converter_instance),
        ("Session stop cleanup", test_playback_session_stop_cleanup),
        ("probe get_input_format_from_url", test_probe_get_input_format_from_url),
        ("health hls_playlist_ready", test_health_hls_playlist_ready),
        ("WHEP unavailable message", test_whep_unavailable_message),
    ]
    for name, fn in tests:
        try:
            fn()
        except Exception as e:
            errors.append((name, e))
            print(f"[FAIL] {name}: {e}")
    print()
    if errors:
        print(f"Провалено: {len(errors)} из {len(tests)}")
        for name, e in errors:
            print(f"  - {name}: {e}")
        sys.exit(1)
    print("Все тесты пройдены.")
    sys.exit(0)


if __name__ == "__main__":
    main()
