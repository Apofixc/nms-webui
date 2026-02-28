# API эндпоинты модуля stream
# Префикс: /api/v1/m/stream
import logging
import aiohttp
from urllib.parse import urlparse
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

        # Обновляем информацию о воркере: записываем реальный бэкенд и URL вывода
        worker = mod.worker_pool.get_worker(worker_id)
        if worker:
            worker.backend_id = result.backend_used
            worker.output_url = result.output_url

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

    # Удаление hls папки и файла .ts если они есть
    hls_dir = f"/tmp/stream_hls_{stream_id}"
    if os.path.exists(hls_dir):
        for f in glob.glob(f"{hls_dir}/*"):
            try:
                os.remove(f)
            except:
                pass
                
    ts_file = f"/opt/nms-webui/data/streams/{stream_id}.ts"
    if os.path.exists(ts_file):
        try:
            os.remove(ts_file)
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
    
    # HLS сегменты и плейлист
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
    """Универсальный эндпоинт для воспроизведения."""
    mod = _get_module()
    worker = mod.worker_pool.get_worker(stream_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Поток не запущен или уже остановлен")

    task = worker.task
    output_type = task.output_type

    # Общие заголовки для стриминга (чтобы плеер в браузере не тупил)
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Expose-Headers": "*"
    }

    # 1. HLS - раздача файлов
    if output_type == OutputType.HLS:
        return await serve_stream_file(stream_id, "playlist.m3u8")

    # 2. HTTP_TS - раздача из файла (кэша)
    if output_type == OutputType.HTTP_TS:
        # Для Astra оставляем как было, так как Astra отдает свой HTTP_TS по URL
        backend = mod.router._backends.get(worker.backend_id)
        if worker.output_url and ("127.0.0.1" in worker.output_url and backend and backend.backend_id == 'astra'):
            return RedirectResponse(url=worker.output_url)
            
        file_path = f"/opt/nms-webui/data/streams/{stream_id}.ts"
        
        # Ждем пока файл создастся (до 5 секунд)
        for _ in range(50):
            if os.path.exists(file_path):
                break
            await asyncio.sleep(0.1)
            
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Файл потока не успел создаться")

        async def file_generator():
            try:
                # Читаем файл по мере роста
                with open(file_path, "rb") as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            # Если процесс мертв и данных больше нет - выходим
                            if worker.process and worker.process.returncode is not None:
                                break
                            # Если процесса вообще нет, тоже выходим
                            if not worker.process and not worker.output_url:
                                break
                            await asyncio.sleep(0.1)
                            continue
                        yield chunk
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Ошибка чтения файла HTTP_TS: {e}")

        return StreamingResponse(
            file_generator(),
            media_type="video/mp2t",
            headers=headers
        )

    # 3. HTTP - прямой стриминг (stdout или прокси)
    if output_type == OutputType.HTTP:
        backend = mod.router._backends.get(worker.backend_id)
        
        # Если бэкенд предоставил внешний или внутренний HTTP URL для проксирования
        # (Важно: проверяем, что это не ссылка на самого себя, чтобы избежать рекурсии)
        if worker.output_url and ("127.0.0.1" in worker.output_url or "/proxy/" in worker.output_url):
            # Если это путь на нашего же прокси, делаем редирект или проксируем
            if "/proxy/" in worker.output_url:
                return await proxy_stream(stream_id)
                
            async def proxy_internal():
                try:
                    # Увеличиваем таймаут для локальных соединений
                    timeout = aiohttp.ClientTimeout(total=None, connect=5, sock_read=60)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(worker.output_url) as response:
                            async for chunk, _ in response.content.iter_chunks():
                                yield chunk
                except Exception as e:
                    logger.error(f"Error proxying internal stream {worker.output_url}: {e}")
            
            return StreamingResponse(
                proxy_internal(), 
                media_type="video/mp2t",
                headers=headers
            )

        # Если это локальный процесс (FFmpeg, GStreamer), читаем его stdout
        if not backend:
            raise HTTPException(status_code=500, detail=f"Бэкенд '{worker.backend_id}' недоступен")
        
        process = None
        if hasattr(backend, "_streamer") and hasattr(backend._streamer, "_processes"):
            process = backend._streamer._processes.get(stream_id)

        if process and getattr(process, "stdout", None):
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
                media_type="video/mp2t",
                headers=headers
            )

        # Если ничего не подошло, но есть output_url ( Astra / PureProxy )
        if worker.output_url:
             # Если URL начинается с /api - значит это наш же эндпоинт, проксируем его
             if worker.output_url.startswith("/api"):
                 return await proxy_stream(stream_id)
             return RedirectResponse(url=worker.output_url)

        error_msg = f"Поток '{stream_id}' не может быть воспроизведен (нет процесса или URL)"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
        
    if output_type == OutputType.WEBRTC:
        return JSONResponse({"detail": "WebRTC требует отдельного signaling эндпоинта"})

    raise HTTPException(status_code=400, detail="Неизвестный тип вывода")

@router.get("/proxy/{stream_id}")
async def proxy_stream(stream_id: str):
    """Эндпоинт для нативного проксирования потока (pure_proxy)."""
    mod = _get_module()
    worker = mod.worker_pool.get_worker(stream_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Поток не найден")

    url = worker.task.input_url
    protocol = worker.task.input_protocol

    # Общие заголовки для браузера
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Expose-Headers": "*"
    }

    if protocol == StreamProtocol.HTTP:
        async def http_generator():
            try:
                # Берем таймаут из настроек
                timeout = aiohttp.ClientTimeout(total=None, connect=5, sock_read=60)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status >= 400:
                            logger.error(f"Proxy: source error {response.status} for {url}")
                            return
                        async for chunk, _ in response.content.iter_chunks():
                            yield chunk
            except Exception as e:
                logger.error(f"Proxy: exception for {url}: {e}")

        return StreamingResponse(
            http_generator(),
            media_type="video/mp2t",
            headers=headers
        )

    # UDP to HTTP proxying (optimized)
    if protocol == StreamProtocol.UDP:
        try:
            parsed = urlparse(url)
            host = parsed.hostname
            port = parsed.port
            if not host or not port:
                raise ValueError("Invalid UDP URL")

            async def udp_generator():
                # Создаем UDP сокет
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                # Увеличиваем системный буфер приема (критично для мультикаста)
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2 * 1024 * 1024)
                except:
                    pass

                sock.bind(('', port))
                
                # Если мультикаст - подписываемся
                try:
                    import struct
                    membership = struct.pack("4sl", socket.inet_aton(host), socket.INADDR_ANY)
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
                except:
                    pass # Unicast

                sock.setblocking(False)
                loop = asyncio.get_running_loop()
                
                try:
                    while True:
                        data = await loop.sock_recv(sock, 65536)
                        if not data:
                            break
                        yield data
                except asyncio.CancelledError:
                    pass
                finally:
                    sock.close()

            return StreamingResponse(
                udp_generator(), 
                media_type="video/mp2t",
                headers=headers
            )
        except Exception as e:
            logger.error(f"Proxy UDP error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(
        status_code=501, 
        content={"detail": f"Проксирование протокола {protocol.value} еще не реализовано."}
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
