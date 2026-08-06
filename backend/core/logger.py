"""Настройка структурированного и неблокирующего логгирования."""
from __future__ import annotations

import logging
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
import queue
import sys

from pathlib import Path

from backend.core.config import get_settings

NMS_ROOT = Path(__file__).resolve().parent.parent.parent

# Глобальная ссылка на слушатель очереди логов
_listener: QueueListener | None = None


def setup_logging() -> None:
    """Настройка неблокирующего логгирования для приложения."""
    global _listener

    # Если ранее был запущен слушатель очереди логов, корректно останавливаем его
    if _listener is not None:
        _listener.stop()
        _listener = None

    level = getattr(logging, get_settings().log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Закрываем и удаляем существующие хэндлеры
    for handler in root.handlers[:]:
        handler.close()
        root.removeHandler(handler)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Хэндлер вывода в стандартный поток (stdout)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    # 2. Файловый хэндлер с ротацией (максимум 10 МБ x 5 бэкапов)
    log_file_path = NMS_ROOT / "backend.log"
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # 3. Асинхронная неблокирующая очередь
    # Запись логов с приложения отправляется в очередь, не блокируя event loop asyncio
    log_queue: queue.Queue = queue.Queue(-1)
    queue_handler = QueueHandler(log_queue)
    root.addHandler(queue_handler)

    # Фоновый поток слушателя берет логи из очереди и записывает в stdout и файл
    _listener = QueueListener(log_queue, stream_handler, file_handler, respect_handler_level=True)
    _listener.start()

    # Подавление слишком шумных сторонних библиотек
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").propagate = True
    logging.getLogger("httpx").setLevel(logging.WARNING)


