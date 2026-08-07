"""Инициализация экземпляра Celery для фоновых распределенных задач."""
from __future__ import annotations

from celery import Celery
from backend.core.config import get_settings

settings = get_settings()
celery_worker = Celery("nms_worker", broker=settings.celery_broker_url)
