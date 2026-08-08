"""Система метрик Prometheus для NMS-WebUI."""
from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, Counter, Gauge, Histogram, generate_latest


def _get_or_create_counter(name: str, documentation: str, labelnames: tuple = ()):
    try:
        return Counter(name, documentation, labelnames)
    except Exception:
        return REGISTRY._names_to_collectors.get(name) or REGISTRY._names_to_collectors.get(f"{name}_total")


def _get_or_create_histogram(name: str, documentation: str, labelnames: tuple = ()):
    try:
        return Histogram(name, documentation, labelnames)
    except Exception:
        return REGISTRY._names_to_collectors.get(name) or REGISTRY._names_to_collectors.get(f"{name}_seconds")


def _get_or_create_gauge(name: str, documentation: str):
    try:
        return Gauge(name, documentation)
    except Exception:
        return REGISTRY._names_to_collectors.get(name)


HTTP_REQUESTS_TOTAL = _get_or_create_counter(
    "nms_http_requests_total",
    "Общее количество HTTP-запросов к NMS WebUI",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = _get_or_create_histogram(
    "nms_http_request_duration_seconds",
    "Длительность обработки HTTP-запросов в секундах",
    ["method", "endpoint"],
)

ACTIVE_SESSIONS_COUNT = _get_or_create_gauge(
    "nms_active_sessions_count",
    "Количество активных пользовательских сессий",
)

LOADED_MODULES_COUNT = _get_or_create_gauge(
    "nms_loaded_modules_count",
    "Количество загруженных плагинов/модулей системы",
)


def metrics_endpoint_handler(request: Request = None) -> Response:
    """Обработчик эндпоинта /metrics для сбора данных Prometheus."""
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
