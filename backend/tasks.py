"""
Задачи для RQ-воркеров: тяжёлые операции (превью, анализ) выполняются в отдельных процессах.
Запуск воркера: из корня проекта PYTHONPATH=. python -m rq worker --url redis://localhost:6379 nms --with-scheduler
Или: ./run_worker.sh
"""
from pathlib import Path

from backend.stream.capture import StreamFrameCapture


def refresh_previews(items: list[dict]) -> dict:
    """
    Обновить превью в кэше. Вызывается из RQ-воркера.
    :param items: список {"url": str, "cache_path": str} (cache_path — абсолютный путь к файлу)
    :return: {"done": int, "failed": int}
    """
    capture = StreamFrameCapture()
    if not capture.available:
        return {"done": 0, "failed": len(items)}
    done = 0
    failed = 0
    for entry in items:
        if not isinstance(entry, dict):
            failed += 1
            continue
        url = entry.get("url")
        cache_path_str = entry.get("cache_path")
        if not url or not cache_path_str:
            failed += 1
            continue
        path = Path(cache_path_str)
        try:
            raw = capture.capture(url, timeout_sec=10.0, output_format="jpeg")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            done += 1
        except Exception:
            failed += 1
    return {"done": done, "failed": failed}
