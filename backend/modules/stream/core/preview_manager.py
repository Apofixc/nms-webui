import asyncio
import logging
import hashlib
import time
from pathlib import Path
from typing import Callable, Awaitable, Optional

logger = logging.getLogger(__name__)

# Transparent 1x1 PNG for stub
STUB_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000b49444154789c636000020000050001e9fa22a40000000049454e44ae42"
    "6082"
)

def normalize_url(url: str) -> str:
    """Очищает URL от специфичных для Astra хэш-параметров."""
    if "#" in url:
        return url.split("#", 1)[0]
    return url

class PreviewManager:
    """
    Управляет генерацией превью в фоне для защиты бэкендов от перегрузок.
    Дедуплицирует запросы, удерживает лимит конкурентности и реализует Negative Caching.
    """
    def __init__(self, cache_dir: str = "/tmp/nms_previews", cache_ttl: int = 15, max_workers: int = 4):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_ttl = cache_ttl
        self.negative_ttl = 30
        
        self._semaphore = asyncio.Semaphore(max_workers)
        self._in_progress = set()
        
        # Negative cache: url_hash -> expires_timestamp
        self._negative_cache = {}
        
    async def get_preview(
        self, 
        url: str, 
        pipeline_func: Callable[[str], Awaitable[Optional[bytes]]],
        fmt: str = "jpeg"
    ) -> tuple[bytes, str]:
        """
        Возвращает (content, media_type).
        Синхронно: либо отдает свежий кэш, либо отдает стаб и запускает генерацию в фоне.
        """
        clean_url = normalize_url(url)
        url_hash = hashlib.md5(clean_url.encode('utf-8')).hexdigest()
        cache_path = self.cache_dir / f"{url_hash}.{fmt}"
        mime_type = f"image/{fmt}"
        
        now = time.time()
        
        # 1. Проверка Negative Cache (если поток падал ранее)
        if url_hash in self._negative_cache:
            if now > self._negative_cache[url_hash]:
                del self._negative_cache[url_hash]
            else:
                return STUB_PNG, "image/png"

        # 2. Проверка валидного кэша
        if cache_path.exists():
            mtime = cache_path.stat().st_mtime
            if now - mtime < self.cache_ttl:
                # Отдаем свежий кэш
                try:
                    return cache_path.read_bytes(), mime_type
                except Exception as e:
                    logger.error(f"Ошибка чтения кэша превью {cache_path}: {e}")
            else:
                # Кэш устарел: отправляем задачу на обновление, отдаем старый кэш
                self._schedule_generation(clean_url, url_hash, cache_path, pipeline_func)
                try:
                    return cache_path.read_bytes(), mime_type
                except Exception:
                    pass
        else:
            # Кэша вообще нет -> Сразу просим сгенерировать
            self._schedule_generation(clean_url, url_hash, cache_path, pipeline_func)
            
        # Возвращаем стаб (заглушку) пока генерация идет в фоне
        return STUB_PNG, "image/png"

    def _schedule_generation(self, url: str, url_hash: str, cache_path: Path, pipeline_func: Callable[[str], Awaitable[Optional[bytes]]]):
        if url_hash in self._in_progress:
            return  # Уже генерируется
            
        self._in_progress.add(url_hash)
        asyncio.create_task(self._worker(url, url_hash, cache_path, pipeline_func))

    async def _worker(self, url: str, url_hash: str, cache_path: Path, pipeline_func: Callable[[str], Awaitable[Optional[bytes]]]):
        try:
            async with self._semaphore:
                # Запускаем генерацию переданной функцией с чистым URL
                data = await pipeline_func(url)
                if data:
                    # Атомарное сохранение: пишем в .tmp и переименовываем
                    tmp_path = cache_path.with_suffix('.tmp')
                    tmp_path.write_bytes(data)
                    tmp_path.rename(cache_path)
                    
                    self._negative_cache.pop(url_hash, None)
                else:
                    self._schedule_negative(url_hash)
        except Exception as e:
            logger.warning(f"Фоновая генерация превью провалилась для '{url}': {e}")
            self._schedule_negative(url_hash)
        finally:
            self._in_progress.discard(url_hash)
            
    def _schedule_negative(self, url_hash: str):
        self._negative_cache[url_hash] = time.time() + self.negative_ttl
