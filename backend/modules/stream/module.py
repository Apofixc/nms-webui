# Основной класс модуля стриминга
import logging
import asyncio
import os
import time
import shutil
from backend.modules.base import BaseModule
from typing import Any

from .core.router import StreamRouter
from .core.pipeline import StreamPipeline
from .core.worker_pool import WorkerPool
from .core.loader import SubmoduleLoader
from .core.preview_manager import PreviewManager
from .monitors.metrics import StreamMetrics
from .monitors.health import check_backends_health

logger = logging.getLogger(__name__)


class StreamModule(BaseModule):
    """Headless-модуль для доставки видеопотоков.

    Управляет жизненным циклом:
    1. Инициализация роутера, pipeline, пула воркеров.
    2. Загрузка субмодулей через loader.
    3. Мониторинг здоровья бэкендов.
    4. Периодическая очистка временных файлов.
    """

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._router: StreamRouter | None = None
        self._pipeline: StreamPipeline | None = None
        self._worker_pool: WorkerPool | None = None
        self._loader: SubmoduleLoader | None = None
        self._metrics: StreamMetrics | None = None
        self.preview_manager: PreviewManager | None = None
        self._cleanup_task: asyncio.Task | None = None

    # --- Жизненный цикл ---

    def init(self) -> None:
        """Инициализация ядра: создание компонентов и загрузка бэкендов."""
        settings = self._get_settings()

        # Создание компонентов ядра
        self._router = StreamRouter()
        self._router.set_format_costs(settings.get("format_weights", {}))
        self._router.set_preview_format_costs(settings.get("preview_format_weights", {}))
        self._metrics = StreamMetrics()

        pool_size = settings.get("worker_pool_size", 4)
        pool_timeout = settings.get("worker_timeout", 30)
        self._worker_pool = WorkerPool(
            max_workers=pool_size,
            timeout=pool_timeout,
        )

        max_retries = 2
        self._pipeline = StreamPipeline(
            router=self._router,
            max_retries=max_retries,
        )

        # Загрузка субмодулей
        self._loader = SubmoduleLoader(self._router)
        loaded = self._loader.load_all(settings)

        # Менеджер фоновых превью
        self.preview_manager = PreviewManager(
            cache_dir="data/previews",
            cache_ttl=settings.get("preview_cache_ttl", 15),
            max_workers=settings.get("preview_max_workers", 4),
            settings=settings
        )

        logger.info(
            f"Модуль stream инициализирован: "
            f"воркеры={pool_size}, бэкенды={loaded}"
        )

    def start(self) -> None:
        """Запуск фоновых задач."""
        if self.preview_manager:
            self.preview_manager.start()
            
        # Запуск периодической очистки файлов
        self._cleanup_task = asyncio.create_task(self._run_periodic_cleanup())
        
        logger.info("Модуль stream запущен")

    def stop(self) -> None:
        """Корректное завершение: остановка воркеров, освобождение ресурсов."""
        if self._cleanup_task:
            self._cleanup_task.cancel()

        if self.preview_manager:
            self.preview_manager.stop()
            
        if self._worker_pool:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._worker_pool.stop_all())
            else:
                loop.run_until_complete(self._worker_pool.stop_all())

        logger.info("Модуль stream остановлен")

    async def _run_periodic_cleanup(self):
        """Задача для очистки 'сиротских' файлов раз в 30 минут."""
        while True:
            try:
                await asyncio.sleep(1800) # Раз в 30 минут
                await self._cleanup_orphaned_files()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в фоновой очистке файлов: {e}")

    async def _cleanup_orphaned_files(self):
        """Удаление файлов в data/streams, не принадлежащих активным воркерам."""
        if not self._worker_pool:
            return

        streams_dir = "data/streams"
        if not os.path.exists(streams_dir):
            return

        active_ids = set()
        for w in self._worker_pool._workers.values():
            active_ids.add(w.worker_id)

        now = time.time()
        count = 0

        # Сканируем директорию
        for item in os.listdir(streams_dir):
            item_path = os.path.join(streams_dir, item)
            
            # Проверяем, принадлежит ли файл/папка активному воркеру
            is_active = False
            for wid in active_ids:
                if wid in item:
                    is_active = True
                    break
            
            if is_active:
                continue

            # Если файл не активен, проверяем его возраст (удаляем только если старше 10 минут)
            try:
                mtime = os.path.getmtime(item_path)
                if (now - mtime) > 600: # 10 минут
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    count += 1
            except:
                pass

        if count > 0:
            logger.info(f"Фоновая очистка: удалено {count} 'сиротских' файлов/папок из data/streams")

    def get_status(self) -> dict[str, Any]:
        """Текущее состояние модуля."""
        if not self._worker_pool or not self._router:
            return {"active": False, "reason": "Модуль не инициализирован"}

        return {
            "active": True,
            "workers": {
                "active": self._worker_pool.active_count,
                "max": self._worker_pool.max_workers,
            },
            "backends": self._router.get_registered_backends(),
            "metrics": self._metrics.to_dict() if self._metrics else {},
        }

    # --- Публичный API для использования из api.py ---

    @property
    def router(self) -> StreamRouter:
        """Маршрутизатор бэкендов."""
        if not self._router:
            raise RuntimeError("Модуль stream не инициализирован")
        return self._router

    @property
    def pipeline(self) -> StreamPipeline:
        """Конвейер обработки потоков."""
        if not self._pipeline:
            raise RuntimeError("Модуль stream не инициализирован")
        return self._pipeline

    @property
    def worker_pool(self) -> WorkerPool:
        """Пул воркеров."""
        if not self._worker_pool:
            raise RuntimeError("Модуль stream не инициализирован")
        return self._worker_pool

    @property
    def metrics(self) -> StreamMetrics:
        """Метрики модуля."""
        if not self._metrics:
            raise RuntimeError("Модуль stream не инициализирован")
        return self._metrics

    def get_loaded_backends(self) -> dict:
        """Возвращает словарь загруженных бэкендов для health-проверок."""
        if self._loader:
            return self._loader.get_loaded()
        return {}

    # --- Приватные методы ---

    def _get_settings(self) -> dict:
        """Получение настроек модуля из системного реестра."""
        try:
            from backend.core.plugin.registry import get_module_settings
            return get_module_settings("stream") or {}
        except ImportError:
            logger.warning("Системный реестр недоступен, используются настройки по умолчанию")
            return {}

