# Конвейер обработки потоков с fallback-логикой
import logging
from typing import Optional

from .contract import IStreamBackend
from .router import StreamRouter
from .types import StreamTask, StreamResult, StreamProtocol, PreviewFormat
from .exceptions import StreamPipelineError, NoSuitableBackendError

logger = logging.getLogger(__name__)


class StreamPipeline:
    """Конвейер обработки потоков.

    Координирует выполнение задач через роутер,
    обеспечивая fallback-переключение при сбоях.
    """

    def __init__(self, router: StreamRouter, max_retries: int = 2) -> None:
        self._router = router
        self._max_retries = max_retries

    async def execute_stream(self, task: StreamTask) -> StreamResult:
        """Запуск стриминга с автоматическим fallback.

        Если основной бэкенд падает, пробуем следующий по приоритету.
        """
        last_error: Optional[str] = None

        for attempt in range(self._max_retries + 1):
            try:
                backend = await self._router.select_stream_backend(task)
                logger.info(
                    f"[Попытка {attempt + 1}] Стриминг через '{backend.backend_id}': "
                    f"{task.input_url}"
                )
                result = await backend.start_stream(task)
                if result.success:
                    return result
                last_error = result.error

            except NoSuitableBackendError as e:
                last_error = str(e)
                break

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Бэкенд сбой (попытка {attempt + 1}): {e}"
                )

            # Исключаем неудачный бэкенд для следующей попытки
            if task.forced_backend:
                break  # Ручной режим: повторов не делаем

        raise StreamPipelineError(
            f"Не удалось запустить стриминг после {self._max_retries + 1} попыток. "
            f"Последняя ошибка: {last_error}"
        )

    async def execute_preview(
        self,
        url: str,
        protocol: StreamProtocol,
        fmt: PreviewFormat = PreviewFormat.JPEG,
        width: int = 640,
        quality: int = 75,
        forced_backend: Optional[str] = None,
    ) -> bytes:
        """Генерация превью с fallback."""
        last_error: Optional[str] = None

        for attempt in range(self._max_retries + 1):
            try:
                backend = await self._router.select_preview_backend(
                    protocol=protocol,
                    forced_backend=forced_backend,
                )
                logger.info(
                    f"[Попытка {attempt + 1}] Превью через '{backend.backend_id}': {url}"
                )
                data = await backend.generate_preview(
                    url=url,
                    protocol=protocol,
                    fmt=fmt,
                    width=width,
                    quality=quality,
                )
                if data:
                    return data
                last_error = "Бэкенд вернул пустой результат"

            except NoSuitableBackendError as e:
                last_error = str(e)
                break

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Ошибка генерации превью (попытка {attempt + 1}): {e}"
                )

            if forced_backend:
                break

        raise StreamPipelineError(
            f"Не удалось сгенерировать превью. Последняя ошибка: {last_error}"
        )
