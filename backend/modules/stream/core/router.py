# Маршрутизатор выбора бэкенда
import logging
from typing import Dict, Optional, Set

from .contract import IStreamBackend
from .types import StreamProtocol, OutputType, BackendCapability, StreamTask, PreviewFormat
from .exceptions import NoSuitableBackendError

logger = logging.getLogger(__name__)


class StreamRouter:
    """Маршрутизатор, выбирающий оптимальный бэкенд для задачи.

    Поддерживает два режима:
    1. Auto-Discovery — автоматический подбор по типу протокола и вывода.
    2. Manual Override — принудительное назначение бэкенда.
    """

    def __init__(self) -> None:
        self._backends: dict[str, IStreamBackend] = {}
        # Приоритеты бэкендов (чем меньше число, тем выше приоритет)
        self._priority: dict[str, int] = {}  # backend_id -> base_priority
        
        # Глобальные веса выходных форматов (чем меньше, тем лучше)
        self._format_costs: dict[OutputType, float] = {
            OutputType.WEBRTC: 0.1,   # Минимальная задержка (через движок)
            OutputType.HTTP: 0.5,     # Прямой проброс (минимум задержки, прокси)
            OutputType.HLS: 1.0,      # Универсальность (сегментировано)
            OutputType.HTTP_TS: 2.0,  # Буферизировано (надежность)
        }

        self._preview_format_costs: dict[PreviewFormat, float] = {
            PreviewFormat.JPEG: 0.1,  # Быстро и легко
            PreviewFormat.WEBP: 0.2,  # Хорошее сжатие
            PreviewFormat.AVIF: 0.8,  # Очень эффективно, но очень медленно
            PreviewFormat.PNG: 0.5,   # Без потерь, но тяжело
            PreviewFormat.TIFF: 1.5,  # Очень тяжело, без сжатия
            PreviewFormat.GIF: 2.0,   # Оверхед на анимацию
        }

    def set_format_costs(self, costs: dict[str, float]) -> None:
        """Обновление весов форматов из настроек."""
        for fmt_name, cost in costs.items():
            try:
                # Пытаемся сопоставить имя из конфига с Enum
                fmt = OutputType(fmt_name.lower())
                self._format_costs[fmt] = float(cost)
            except (ValueError, KeyError):
                logger.warning(f"Некорректный формат в настройках весов: {fmt_name}")

    def set_preview_format_costs(self, costs: dict[str, float]) -> None:
        """Обновление весов форматов превью из настроек."""
        for fmt_name, cost in costs.items():
            try:
                fmt = PreviewFormat(fmt_name.lower())
                self._preview_format_costs[fmt] = float(cost)
            except (ValueError, KeyError):
                logger.warning(f"Некорректный формат превью в настройках: {fmt_name}")

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

    def get_backend(self, backend_id: str) -> Optional[IStreamBackend]:
        """Получение экземпляра бэкенда по его ID."""
        return self._backends.get(backend_id)

    def get_all_supported_protocols(self) -> Set[StreamProtocol]:
        """Возвращает набор всех поддерживаемых входных протоколов всеми бэкендами."""
        protocols = set()
        for backend in self._backends.values():
            protocols.update(backend.supported_input_protocols())
        return protocols

    def can_direct_pass(self, task: StreamTask) -> bool:
        """Проверка, можно ли отдать ссылку напрямую (без бэкенда)."""
        # HLS нативно поддерживается или через hls.js
        if task.input_protocol == StreamProtocol.HLS and task.output_type in {OutputType.HLS, OutputType.AUTO}:
            return True
            
        return False

    async def select_stream_backend(self, task: StreamTask, excluded: Optional[Set[str]] = None) -> IStreamBackend:
        """Выбор бэкенда для стриминга.
        Поддерживает резолвинг OutputType.AUTO на основе приоритетов бэкендов.
        """
        # 1. Ручной режим (forced_backend)
        if task.forced_backend:
            backend = self._backends.get(task.forced_backend)
            if backend and await backend.is_available():
                # Валидация протокола для принудительно выбранного бэкенеда
                if task.input_protocol not in backend.supported_input_protocols():
                    supported = ", ".join(sorted([p.value for p in backend.supported_input_protocols()]))
                    raise NoSuitableBackendError(
                        f"Бэкенд '{task.forced_backend}' не поддерживает протокол '{task.input_protocol.value}'. "
                        f"Поддерживаемые им протоколы: {supported}"
                    )

                # Если принудительно выбран бэкенд, но формат AUTO - резолвим его по весам форматов
                if task.output_type == OutputType.AUTO:
                    supported_formats = []
                    for ot in backend.supported_output_types():
                        cost = self._format_costs.get(ot, 5.0)
                        supported_formats.append((ot, cost))
                    
                    if supported_formats:
                        # Сортируем по весу формата
                        supported_formats.sort(key=lambda x: x[1])
                        task.output_type = supported_formats[0][0]
                        return backend
                        
                    raise NoSuitableBackendError(f"Бэкенд '{task.forced_backend}' не поддерживает ни одного выходного формата")
                return backend
            raise NoSuitableBackendError(
                f"Принудительно выбранный бэкенд '{task.forced_backend}' недоступен"
            )

        # 2. Поиск кандидатов
        if task.output_type != OutputType.AUTO:
            candidates = await self._find_candidates(
                protocol=task.input_protocol,
                output_type=task.output_type,
                capability=BackendCapability.STREAMING,
                excluded=excluded,
            )
        else:
            # Резолвинг AUTO: ищем оптимальную пару (Бэкенд + Формат)
            all_backends = await self._find_candidates(
                protocol=task.input_protocol,
                capability=BackendCapability.STREAMING,
                excluded=excluded,
            )
            
            options = []
            for backend in all_backends:
                dynamic_cost = await backend.get_dynamic_cost(task.input_protocol)
                base_priority = self._priority.get(backend.backend_id, 999)
                
                for ot in backend.supported_output_types():
                    format_cost = self._format_costs.get(ot, 5.0)
                    total_cost = base_priority + dynamic_cost + format_cost
                    options.append((backend, ot, total_cost))
            
            if options:
                options.sort(key=lambda x: x[2])
                best_backend, best_format, best_cost = options[0]
                task.output_type = best_format
                logger.debug(f"AUTO-выбор для {task.input_protocol.value}: {best_backend.backend_id} ({best_format.value}), цена={best_cost:.2f}")
                return best_backend
            
            candidates = []

        if not candidates:
            supported = ", ".join(sorted([p.value for p in self.get_all_supported_protocols()]))
            raise NoSuitableBackendError(
                f"Нет доступного бэкенда для {task.input_protocol.value} -> {task.output_type.value}. "
                f"Поддерживаемые входные протоколы: {supported}"
            )

        return candidates[0]

    async def select_preview_backend(
        self,
        protocol: StreamProtocol,
        fmt: PreviewFormat = PreviewFormat.AUTO,
        forced_backend: Optional[str] = None,
        excluded: Optional[Set[str]] = None,
    ) -> tuple[IStreamBackend, PreviewFormat]:
        """Выбор бэкенда для генерации превью и резолвинг формата.
        
        Returns:
            Кортеж (Backend, ResolvedFormat)
        """
        if forced_backend:
            backend = self._backends.get(forced_backend)
            if backend and await backend.is_available():
                res_fmt = fmt
                if fmt == PreviewFormat.AUTO:
                    # Резолвим AUTO для принудительного бэкенда по весам
                    supported = []
                    for pf in backend.supported_preview_formats():
                        cost = self._preview_format_costs.get(pf, 1.0)
                        supported.append((pf, cost))
                    
                    if supported:
                        supported.sort(key=lambda x: x[1])
                        res_fmt = supported[0][0]
                    else:
                        raise NoSuitableBackendError(f"Бэкенд превью '{forced_backend}' не поддерживает ни одного формата")
                return backend, res_fmt
            raise NoSuitableBackendError(
                f"Принудительно выбранный бэкенд превью '{forced_backend}' недоступен"
            )

        # Резолвинг AUTO или подбор лучшего по весам
        all_backends = await self._find_candidates(
            protocol=protocol,
            capability=BackendCapability.PREVIEW,
            excluded=excluded,
        )

        options = []
        for backend in all_backends:
            dynamic_cost = await backend.get_dynamic_cost(protocol)
            base_priority = self._priority.get(backend.backend_id, 999)
            
            # Если формат задан явно
            if fmt != PreviewFormat.AUTO:
                if fmt in backend.supported_preview_formats():
                    format_cost = self._preview_format_costs.get(fmt, 1.0)
                    options.append((backend, fmt, base_priority + dynamic_cost + format_cost))
            else:
                # Если AUTO - перебираем все поддерживаемые форматы
                for pf in backend.supported_preview_formats():
                    format_cost = self._preview_format_costs.get(pf, 1.0)
                    options.append((backend, pf, base_priority + dynamic_cost + format_cost))

        if options:
            options.sort(key=lambda x: x[2])
            best_backend, best_fmt, best_cost = options[0]
            logger.debug(f"PREVIEW-выбор для {protocol.value}: {best_backend.backend_id} ({best_fmt.value}), цена={best_cost:.2f}")
            return best_backend, best_fmt
        
        raise NoSuitableBackendError(
            f"Нет доступного бэкенда превью для {protocol.value} (формат: {fmt.value}). "
            f"Убедитесь, что протокол поддерживается хотя бы одним превью-бэкендом."
        )

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

        # Сортировка по динамической стоимости
        # Общая стоимость = базовый приоритет + динамическая добавка от бэкенда
        costs = []
        for b in candidates:
            dynamic = await b.get_dynamic_cost(protocol)
            base = self._priority.get(b.backend_id, 999)
            costs.append((b, base + dynamic))

        costs.sort(key=lambda x: x[1])
        if costs:
            costs_str = ", ".join([f"{c[0].backend_id}={c[1]:.1f}" for c in costs])
            logger.debug(f"Выбор бэкенда для {protocol.value}: кандидаты [{costs_str}]")
        return [c[0] for c in costs]

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
