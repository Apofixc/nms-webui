import asyncio
import logging
import hashlib
import time
from pathlib import Path
from typing import Callable, Awaitable, Optional

logger = logging.getLogger(__name__)

STUB_SVG = (
    b'<svg width="640" height="360" xmlns="http://www.w3.org/2000/svg">'
    b'<rect width="100%" height="100%" fill="#2a2a2a"/>'
    b'<text x="50%" y="50%" font-family="sans-serif" font-size="24" fill="#888" text-anchor="middle" dominant-baseline="middle">NO IMAGE</text>'
    b'</svg>'
)

def normalize_url(url: str) -> str:
    """Очищает URL от специфичных для Astra хэш-параметров."""
    clean_url = url.split("#", 1)[0] if "#" in url else url
    if "://0:" in clean_url:
        clean_url = clean_url.replace("://0:", "://127.0.0.1:")
    return clean_url

class PreviewManager:
    """
    Управляет генерацией превью в фоне для защиты бэкендов от перегрузок.
    Дедуплицирует запросы, удерживает лимит конкурентности и реализует Negative Caching.
    Работает через единственный фоновый цикл.
    """
    def __init__(self, cache_dir: str = "/opt/nms-webui/data/previews", cache_ttl: int = 60, max_workers: int = 1, settings: Optional[dict] = None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Настройки
        s = settings or {}
        self.cache_ttl = cache_ttl
        self.negative_ttl = 30
        self.cleanup_timeout = s.get("preview_cleanup_timeout", 300)
        self.loop_interval = s.get("preview_loop_interval", 5)
        self.max_workers = max_workers
        
        self._target_channels = {}  # url -> dict
        self._last_update_time = 0
        self._negative_cache = {}
        
        self._semaphore = asyncio.Semaphore(self.max_workers)
        self._loop_task = None
        
    def start(self):
        if self._loop_task is None:
            self._loop_task = asyncio.create_task(self._background_loop())

    def stop(self):
        if self._loop_task:
            self._loop_task.cancel()
            self._loop_task = None

    def get_cache_key(self, name: Optional[str], url: str) -> str:
        if name:
            safe_name = "".join([c if c.isalnum() or c in " ._-" else "_" for c in name])
            return f"{safe_name}_preview"
        clean_url = normalize_url(url)
        return hashlib.md5(clean_url.encode('utf-8')).hexdigest()

    def get_preview_image(self, name: Optional[str], url: str, fmt: str = "jpeg") -> tuple[bytes, str]:
        """Только отдает картинку из кэша (или заглушку), без генерации."""
        cache_key = self.get_cache_key(name, url)
        cache_path = self.cache_dir / f"{cache_key}.{fmt}"
        mime_type = f"image/{fmt}"
        
        if cache_path.exists():
            try:
                # Если файл пустой (0 байт), игнорируем его
                if cache_path.stat().st_size > 0:
                    return cache_path.read_bytes(), mime_type
            except Exception as e:
                logger.error(f"Ошибка чтения кэша превью {cache_path}: {e}")
                
        return STUB_SVG, "image/svg+xml"

    def add_target_channels(self, channels_info: list):
        """
        Добавляет новые каналы к списку для фоновой генерации.
        """
        for ch in channels_info:
            self._target_channels[ch["url"]] = ch
        self._last_update_time = time.time()

    async def _process_target(self, target: dict):
        """Индивидуальная задача генерации одного превью."""
        async with self._semaphore:
            name = target.get("name")
            url = target.get("url")
            func = target.get("func")
            fmt = target.get("fmt", "jpeg")

            cache_key = self.get_cache_key(name, url)
            cache_path = self.cache_dir / f"{cache_key}.{fmt}"
            now = time.time()

            # 1. Negative Cache
            if cache_key in self._negative_cache:
                if now < self._negative_cache[cache_key]:
                    return
                else:
                    del self._negative_cache[cache_key]

            # 2. Cache validation
            if cache_path.exists():
                if cache_path.stat().st_size > 0 and now - cache_path.stat().st_mtime < self.cache_ttl:
                    return

            # 3. Generate!
            try:
                logger.info(f"Запуск генерации превью для {url}")
                data = await func(normalize_url(url))
                if data and len(data) > 0:
                    tmp_path = cache_path.with_suffix('.tmp')
                    tmp_path.write_bytes(data)
                    tmp_path.rename(cache_path)
                    logger.info(f"Превью успешно сохранено: {cache_path} ({len(data)} байт)")
                    self._negative_cache.pop(cache_key, None)
                else:
                    logger.warning(f"Генератор вернул пустые данные для {url}")
                    self._negative_cache[cache_key] = time.time() + self.negative_ttl
            except Exception as e:
                logger.warning(f"Ошибка фоновой генерации для {url}: {e}")
                self._negative_cache[cache_key] = time.time() + self.negative_ttl

    async def _background_loop(self):
        """Фоновый цикл генерации превью."""
        while True:
            try:
                now = time.time()
                # Очищаем список при отсутствии активности клиента
                if self._target_channels and now - self._last_update_time > self.cleanup_timeout:
                    logger.info(f"Клиенты не запрашивали превью более {self.cleanup_timeout}с, очистка очереди.")
                    self._target_channels.clear()

                if not self._target_channels:
                    await asyncio.sleep(2)
                    continue

                # Создаем задачи для всех каналов в очереди
                targets = list(self._target_channels.values())
                tasks = [self._process_target(t) for t in targets]
                
                # Запускаем все задачи параллельно (лимит через семафор внутри)
                await asyncio.gather(*tasks)

                # После полного обхода списка ждем перед новым обходом
                await asyncio.sleep(self.loop_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Сбой в цикле превью: {e}")
                await asyncio.sleep(self.loop_interval)
