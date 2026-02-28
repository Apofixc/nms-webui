# Основной класс модуля стриминга
import logging
from backend.modules.base import BaseModule
from typing import Any

from .core.router import StreamRouter
from .core.pipeline import StreamPipeline
from .core.worker_pool import WorkerPool
from .core.loader import SubmoduleLoader
from .monitors.metrics import StreamMetrics
from .monitors.health import check_backends_health

logger = logging.getLogger(__name__)


class StreamModule(BaseModule):
    """Headless-модуль для доставки видеопотоков.

    Управляет жизненным циклом:
    1. Инициализация роутера, pipeline, пула воркеров.
    2. Загрузка субмодулей через loader.
    3. Мониторинг здоровья бэкендов.
    """

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._router: StreamRouter | None = None
        self._pipeline: StreamPipeline | None = None
        self._worker_pool: WorkerPool | None = None
        self._loader: SubmoduleLoader | None = None
        self._metrics: StreamMetrics | None = None

    # --- Жизненный цикл ---

    def init(self) -> None:
        """Инициализация ядра: создание компонентов и загрузка бэкендов."""
        settings = self._get_settings()

        # Создание компонентов ядра
        self._router = StreamRouter()
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

        logger.info(
            f"Модуль stream инициализирован: "
            f"воркеры={pool_size}, бэкенды={loaded}"
        )

    def start(self) -> None:
        """Запуск фоновых задач."""
        logger.info("Модуль stream запущен")

    def stop(self) -> None:
        """Корректное завершение: остановка воркеров, освобождение ресурсов."""
        if self._worker_pool:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._worker_pool.stop_all())
            else:
                loop.run_until_complete(self._worker_pool.stop_all())

        logger.info("Модуль stream остановлен")

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

    # --- Приватные методы ---

    def _get_settings(self) -> dict:
        """Получение настроек модуля из системного реестра."""
        try:
            from backend.core.plugin.registry import get_module_settings
            return get_module_settings("stream") or {}
        except ImportError:
            logger.warning("Системный реестр недоступен, используются настройки по умолчанию")
            return {}
