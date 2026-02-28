# Маршрутизатор выбора бэкенда
import logging
from typing import Dict, Optional, Set

from .contract import IStreamBackend
from .types import StreamProtocol, OutputType, BackendCapability, StreamTask
from .exceptions import NoSuitableBackendError

logger = logging.getLogger(__name__)


class StreamRouter:
    """Маршрутизатор, выбирающий оптимальный бэкенд для задачи.

    Поддерживает два режима:
    1. Auto-Discovery — автоматический подбор по типу протокола и вывода.
    2. Manual Override — принудительное назначение бэкенда.
    """

    def __init__(self) -> None:
        self._backends: Dict[str, IStreamBackend] = {}
        # Приоритеты бэкендов (чем меньше число, тем выше приоритет)
        self._priority: Dict[str, int] = {}

    def register(self, backend: IStreamBackend, priority: int = 100) -> None:
        """Регистрация бэкенда в маршрутизаторе.

        Args:
            backend: Экземпляр бэкенда, реализующий IStreamBackend.
            priority: Приоритет (0 = наивысший). По умолчанию 100.
        """
        self._backends[backend.backend_id] = backend
        self._priority[backend.backend_id] = priority
        logger.info(
            f"Зарегистрирован бэкенд: {backend.backend_id} "
            f"(приоритет={priority}, возможности={backend.capabilities})"
        )

    def unregister(self, backend_id: str) -> None:
        """Удаление бэкенда из маршрутизатора."""
        self._backends.pop(backend_id, None)
        self._priority.pop(backend_id, None)

    async def select_stream_backend(self, task: StreamTask, excluded: Optional[Set[str]] = None) -> IStreamBackend:
        """Выбор бэкенда для стриминга.

        Если задан forced_backend — используется он.
        Иначе — автоматический подбор по протоколу и типу вывода.

        Raises:
            NoSuitableBackendError: Если подходящий бэкенд не найден.
        """
        # Ручной режим
        if task.forced_backend:
            backend = self._backends.get(task.forced_backend)
            if backend and await backend.is_available():
                return backend
            raise NoSuitableBackendError(
                f"Принудительно выбранный бэкенд '{task.forced_backend}' недоступен"
            )

        # Автовыбор: фильтрация по возможностям и сортировка по приоритету
        candidates = await self._find_candidates(
            protocol=task.input_protocol,
            output_type=task.output_type,
            capability=BackendCapability.STREAMING,
            excluded=excluded,
        )

        if not candidates:
            raise NoSuitableBackendError(
                f"Нет доступного бэкенда для {task.input_protocol.value} -> {task.output_type.value}"
            )

        return candidates[0]

    async def select_preview_backend(
        self,
        protocol: StreamProtocol,
        forced_backend: Optional[str] = None,
        excluded: Optional[Set[str]] = None,
    ) -> IStreamBackend:
        """Выбор бэкенда для генерации превью.

        Raises:
            NoSuitableBackendError: Если подходящий бэкенд не найден.
        """
        if forced_backend:
            backend = self._backends.get(forced_backend)
            if backend and await backend.is_available():
                return backend
            raise NoSuitableBackendError(
                f"Принудительно выбранный бэкенд превью '{forced_backend}' недоступен"
            )

        candidates = await self._find_candidates(
            protocol=protocol,
            capability=BackendCapability.PREVIEW,
            excluded=excluded,
        )

        if not candidates:
            raise NoSuitableBackendError(
                f"Нет доступного бэкенда превью для {protocol.value}"
            )

        return candidates[0]

    async def _find_candidates(
        self,
        protocol: StreamProtocol,
        capability: BackendCapability,
        output_type: Optional[OutputType] = None,
        excluded: Optional[Set[str]] = None,
    ) -> list[IStreamBackend]:
        """Поиск подходящих бэкендов, отсортированных по приоритету."""
        candidates = []
        excluded_set = excluded or set()
        for bid, backend in self._backends.items():
            if bid in excluded_set:
                continue
            # Проверка возможностей
            if capability not in backend.capabilities:
                continue
            # Проверка протокола
            if protocol not in backend.supported_input_protocols():
                continue
            # Проверка типа вывода (если задан)
            if output_type and output_type not in backend.supported_output_types():
                continue
            # Проверка доступности
            if not await backend.is_available():
                continue
            candidates.append(backend)

        # Сортировка по приоритету
        candidates.sort(key=lambda b: self._priority.get(b.backend_id, 999))
        return candidates

    def get_registered_backends(self) -> list[dict]:
        """Список зарегистрированных бэкендов и их характеристик."""
        result = []
        for bid, backend in self._backends.items():
            result.append({
                "id": bid,
                "priority": self._priority.get(bid, 999),
                "capabilities": [c.value for c in backend.capabilities],
            })
        return result
