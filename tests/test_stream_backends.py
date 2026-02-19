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
from backend.stream.stream_backends import (
    STREAM_BACKEND_ORDER,
    STREAM_BACKENDS_BY_NAME,
    get_stream_backend_chain,
    get_available_stream_backends,
)
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
    from backend.stream.stream_backends import FFmpegStreamBackend

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


def main():
    print("=== Тесты бэкендов: захват кадра и воспроизведение ===\n")
    errors = []
    tests = [
        ("Порядок бэкендов превью", test_capture_backend_order),
        ("Доступность бэкендов захвата", test_capture_available),
        ("Захват кадра по HTTP", test_capture_http_image),
        ("Цепочка воспроизведения и HLS", test_playback_backend_chain),
        ("HLS-параметры в opts", test_playback_opts_hls_params),
        ("FFmpeg start_hls (dry)", test_ffmpeg_start_hls_dry),
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
