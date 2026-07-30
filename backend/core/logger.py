"""Structured logging setup."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import sys

from pathlib import Path

from backend.core.config import get_settings

NMS_ROOT = Path(__file__).resolve().parent.parent.parent


def setup_logging() -> None:
    """Configure structured logging for the application."""
    level = getattr(logging, get_settings().log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    # Rotating File handler for backend.log (max 10MB x 5 backups)
    log_file_path = NMS_ROOT / "backend.log"
    file_handler = RotatingFileHandler(log_file_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Ensure backend.log exists
    log_file_path.touch(exist_ok=True)

    # Suppress noisy libraries (but keep access logs)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").propagate = True
    logging.getLogger("httpx").setLevel(logging.WARNING)

