# API эндпоинты модуля stream
# Префикс: /api/v1/m/stream
import logging
from fastapi import APIRouter, Query, HTTPException, Response
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel

from .core.types import StreamTask, StreamProtocol, OutputType, PreviewFormat
from .core.exceptions import (
    StreamError,
    NoSuitableBackendError,
    InvalidStreamURLError,
    StreamPipelineError,
)
from .utils import detect_protocol, parse_output_type, parse_preview_format

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/modules/stream/v1", tags=["stream"])

def get_router(*args, **kwargs):
    return router

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

    # Удаление hls папки если она есть
    hls_dir = f"/tmp/stream_hls_{stream_id}"
    if os.path.exists(hls_dir):
        for f in glob.glob(f"{hls_dir}/*"):
            try:
                os.remove(f)
            except:
                pass

    return {"status": "stopped", "stream_id": stream_id}

from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, RedirectResponse
import os
import glob
import asyncio

# --- Serve Streams ---

@router.get("/play/{stream_id}/{filename:path}")
async def serve_stream_file(stream_id: str, filename: str):
    """Раздача HLS фрагментов и плейлиста для трансляции."""
    hls_dir = f"/tmp/stream_hls_{stream_id}"
    file_path = os.path.join(hls_dir, filename)

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Файл потока не найден")

    headers = {
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": "*"
    }
    
    return FileResponse(file_path, headers=headers)

@router.get("/play/{stream_id}")
async def play_stream(stream_id: str):
    """Универсальный эндпоинт для воспроизведения.
    
    Для HLS: возвращает playlist.m3u8
    Для HTTP_TS: возвращает StreamingResponse из stdout процесса
    Для WebRTC: заглушка (требует отдельной реализации signaling)
    Для native_proxy: перенаправляет на прокси
    """
    mod = _get_module()
    worker = mod.worker_pool.get_worker(stream_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Поток не запущен или уже остановлен")

    task = worker.task
    output_type = task.output_type

    if output_type == OutputType.HLS:
        return await serve_stream_file(stream_id, "playlist.m3u8")

    if output_type in (OutputType.HTTP, OutputType.HTTP_TS):
        backend = mod.router._backends.get(worker.backend_id)
        if not backend:
            raise HTTPException(status_code=500, detail="Бэкенд недоступен")
        
        # Безопасное получение процесса (только для локальных сабпроцессов)
        process = None
        if hasattr(backend, "_streamer") and hasattr(backend._streamer, "_processes"):
            process = backend._streamer._processes.get(stream_id)

        if not process or not getattr(process, "stdout", None):
            # Возможно это stream-proxy astra
            if worker.backend_id == "astra":
                meta = worker.result.metadata if hasattr(worker, 'result') and worker.result else {}
                if meta and "output_url" in meta:
                    return RedirectResponse(url=meta["output_url"])
            if worker.backend_id == "pure_proxy":
                return RedirectResponse(url=f"/api/modules/stream/v1/proxy/{stream_id}")
            
            error_msg = f"Процесс стриминга '{stream_id}' на бэкенде '{worker.backend_id}' не найден или stdout недоступен"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        async def stream_generator():
            try:
                while True:
                    chunk = await process.stdout.read(65536)
                    if not chunk:
                        break
                    yield chunk
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Ошибка чтения stdout для потока {stream_id}: {e}")

        return StreamingResponse(
            stream_generator(),
            media_type="video/mp2t"
        )
        
    if output_type == OutputType.WEBRTC:
        return JSONResponse({"detail": "WebRTC требует отдельного signaling эндпоинта"})

    raise HTTPException(status_code=400, detail="Неизвестный тип вывода")

@router.get("/proxy/{stream_id}")
async def proxy_stream(stream_id: str):
    """Эндпоинт для нативного проксирования потока (pure_proxy)."""
    return JSONResponse(
        status_code=501, 
        content={"detail": "Нативное проксирование еще не реализовано в API слое."}
    )

@router.get("/webrtc/{stream_id}")
async def webrtc_stream(stream_id: str):
    """Эндпоинт для WebRTC signaling."""
    return JSONResponse(
        status_code=501, 
        content={"detail": "WebRTC signaling еще не реализовано в API слое."}
    )

# --- Превью ---

@router.get("/preview")
async def get_preview(
    url: str = Query(None, description="URL источника (как запасной вариант)"),
    name: Optional[str] = Query(None, description="Название канала для извлечения кэша (например tv3)"),
    format: str = Query("jpeg", enum=["jpeg", "png", "webp"]),
):
    """
    Получение превью (скриншота) из кэша (БЕЗ генерации).
    Возвращает картинку из папки data/previews или файл-заглушку.
    """
    if not url and not name:
        raise HTTPException(status_code=400, detail="Missing parameter: 'name' or 'url' is required")
        
    mod = _get_module()
    
    data, mime = mod.preview_manager.get_preview_image(name=name, url=url or "", fmt=format)
    return Response(
        content=data,
        media_type=mime,
        headers={"Cache-Control": "no-cache"},
    )


class PreviewRequestItem(BaseModel):
    name: Optional[str] = None
    url: str

class PreviewBatchRequest(BaseModel):
    channels: list[PreviewRequestItem]


@router.post("/preview/generate")
async def generate_preview_batch(
    batch: PreviewBatchRequest,
    format: str = Query("jpeg", enum=["jpeg", "png", "webp"]),
    width: int = Query(640, ge=64, le=1920),
    quality: int = Query(75, ge=1, le=100),
    backend: Optional[str] = Query(None, description="Принудительный выбор бэкенда превью"),
):
    """
    Запрос на фоновую генерацию превью для списка каналов.
    Менеджер обновит свой целевой список и будет генерировать их в фоне.
    """
    mod = _get_module()
    fmt_enum = parse_preview_format(format)

    target_channels = []

    def make_preview_func(proto, fmt_e, w, q, b):
        async def _generate_preview(clean_url: str) -> Optional[bytes]:
            try:
                # Отключаем fallback перебор (max_retries_override=0)
                return await mod.pipeline.execute_preview(
                    url=clean_url,
                    protocol=proto,
                    fmt=fmt_e,
                    width=w,
                    quality=q,
                    forced_backend=b if b != "auto" else None,
                    max_retries_override=0,
                )
            except Exception as e:
                logger.warning(f"Ошибка фоновой генерации превью для {clean_url}: {e}")
                return None
        return _generate_preview

    for item in batch.channels:
        try:
            protocol = detect_protocol(item.url)
        except InvalidStreamURLError:
            continue

        target_channels.append({
            "name": item.name,
            "url": item.url,
            "fmt": fmt_enum.value,
            "func": make_preview_func(protocol, fmt_enum, width, quality, backend)
        })

    mod.preview_manager.add_target_channels(target_channels)
    mod.metrics.record_preview("auto")
    return {"status": "accepted", "count": len(target_channels)}

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
