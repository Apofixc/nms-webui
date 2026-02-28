# API эндпоинты модуля stream
# Префикс: /api/v1/m/stream
import logging
from fastapi import APIRouter, Query, HTTPException, Response
from fastapi.responses import JSONResponse
from typing import Optional

from .core.types import StreamTask, StreamProtocol, OutputType, PreviewFormat
from .core.exceptions import (
    StreamError,
    NoSuitableBackendError,
    InvalidStreamURLError,
    StreamPipelineError,
)
from .utils import detect_protocol, parse_output_type, parse_preview_format

logger = logging.getLogger(__name__)

router = APIRouter()

# Ссылка на экземпляр модуля (устанавливается при инициализации)
_module = None


def set_module(module) -> None:
    """Привязка экземпляра StreamModule к API-роутеру.

    Вызывается из create_module() или системного загрузчика.
    """
    global _module
    _module = module


def _get_module():
    """Получение текущего экземпляра модуля.

    Raises:
        HTTPException: Если модуль не инициализирован.
    """
    if _module is None:
        raise HTTPException(
            status_code=503,
            detail="Модуль stream не инициализирован"
        )
    return _module


# --- Стриминг ---

@router.post("/start")
async def start_stream(
    url: str,
    output_type: str = Query("http", enum=["http", "http_ts", "hls", "webrtc"]),
    backend: Optional[str] = Query(
        None, description="Принудительный выбор бэкенда (None = автовыбор)"
    ),
):
    """Запуск стриминга по сетевому URL.

    Определяет протокол источника, создаёт задачу и делегирует
    её в pipeline, который подбирает оптимальный бэкенд.

    Параметры:
        url: Сетевой адрес (http://, udp://, rtp://, rtsp://, hls://).
        output_type: Тип выходного потока (http, http_ts, hls, webrtc).
        backend: Принудительный выбор бэкенда (пропустить авто-discovery).

    Returns:
        JSON с информацией о запущенном потоке.
    """
    mod = _get_module()

    try:
        # Определение протокола
        protocol = detect_protocol(url)

        # Создание задачи
        task = StreamTask(
            input_url=url,
            input_protocol=protocol,
            output_type=parse_output_type(output_type),
            forced_backend=backend if backend != "auto" else None,
        )

        # Захват слота в пуле воркеров
        worker_id = await mod.worker_pool.acquire(
            task=task,
            backend_id=backend or "auto",
        )

        # Выполнение через pipeline
        result = await mod.pipeline.execute_stream(task)

        # Запись метрик
        mod.metrics.record_stream_start(result.backend_used)

        return {
            "status": "started",
            "stream_id": worker_id,
            "url": url,
            "protocol": protocol.value,
            "output_type": output_type,
            "backend_used": result.backend_used,
            "output_url": result.output_url,
        }

    except InvalidStreamURLError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NoSuitableBackendError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except StreamPipelineError as e:
        mod.metrics.record_stream_failure()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка запуска стрима: {e}", exc_info=True)
        mod.metrics.record_stream_failure()
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {e}")


@router.post("/stop")
async def stop_stream(stream_id: str):
    """Остановка активного потока.

    Args:
        stream_id: Идентификатор потока (worker_id из /start).

    Returns:
        JSON со статусом остановки.
    """
    mod = _get_module()

    worker = mod.worker_pool.get_worker(stream_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Поток '{stream_id}' не найден"
        )

    # Остановка в бэкенде
    backend = mod.router._backends.get(worker.backend_id)
    if backend:
        await backend.stop_stream(stream_id)

    # Освобождение слота
    await mod.worker_pool.release(stream_id)
    mod.metrics.record_stream_stop()

    return {"status": "stopped", "stream_id": stream_id}


# --- Превью ---

@router.get("/preview")
async def get_preview(
    url: str,
    format: str = Query("jpeg", enum=["jpeg", "png", "webp"]),
    width: int = Query(640, ge=64, le=1920),
    quality: int = Query(75, ge=1, le=100),
    backend: Optional[str] = Query(
        None, description="Принудительный выбор бэкенда превью"
    ),
):
    """Генерация превью (скриншота) из сетевого потока.

    Args:
        url: Сетевой адрес источника.
        format: Формат выходного изображения (jpeg, png, webp).
        width: Ширина превью в пикселях.
        quality: Качество сжатия (для JPEG/WebP).
        backend: Принудительный выбор бэкенда.

    Returns:
        Бинарное изображение в указанном формате.
    """
    mod = _get_module()

    try:
        protocol = detect_protocol(url)
        fmt = parse_preview_format(format)

        # Генерация через pipeline с fallback
        data = await mod.pipeline.execute_preview(
            url=url,
            protocol=protocol,
            fmt=fmt,
            width=width,
            quality=quality,
            forced_backend=backend if backend != "auto" else None,
        )

        # Определение MIME-типа
        mime_map = {
            PreviewFormat.JPEG: "image/jpeg",
            PreviewFormat.PNG: "image/png",
            PreviewFormat.WEBP: "image/webp",
        }

        mod.metrics.record_preview("auto")

        return Response(
            content=data,
            media_type=mime_map.get(fmt, "image/jpeg"),
            headers={"Cache-Control": "no-cache"},
        )

    except InvalidStreamURLError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NoSuitableBackendError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except StreamPipelineError as e:
        mod.metrics.record_preview_failure()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка генерации превью: {e}", exc_info=True)
        mod.metrics.record_preview_failure()
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {e}")


# --- Информация ---

@router.get("/status")
async def get_streams_status():
    """Список всех активных потоков и общий статус модуля."""
    mod = _get_module()

    return {
        "module": mod.get_status(),
        "active_streams": mod.worker_pool.list_workers(),
    }


@router.get("/backends")
async def list_backends():
    """Список всех зарегистрированных бэкендов и их возможностей."""
    mod = _get_module()

    return {
        "backends": mod.router.get_registered_backends(),
    }


@router.get("/metrics")
async def get_metrics():
    """Метрики модуля: счётчики стримов, превью, использование бэкендов."""
    mod = _get_module()

    return mod.metrics.to_dict()


@router.get("/health")
async def health_check():
    """Проверка здоровья всех бэкендов."""
    mod = _get_module()

    loaded = mod._loader.get_loaded() if hasattr(mod, "_loader") and mod._loader else {}
    result = await check_backends_health(loaded)

    return result


# Импорт для health endpoint
from .monitors.health import check_backends_health
