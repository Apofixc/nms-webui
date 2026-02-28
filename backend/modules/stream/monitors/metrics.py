# Сбор метрик модуля стриминга
import logging
from dataclasses import dataclass, field
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class StreamMetrics:
    """Счетчики метрик модуля стриминга."""
    # Стриминг
    streams_started: int = 0
    streams_stopped: int = 0
    streams_failed: int = 0

    # Превью
    previews_generated: int = 0
    previews_failed: int = 0

    # Бэкенды
    backend_usage: Dict[str, int] = field(default_factory=dict)

    # Fallback
    fallback_count: int = 0

    def record_stream_start(self, backend_id: str) -> None:
        """Фиксация запуска стрима."""
        self.streams_started += 1
        self.backend_usage[backend_id] = self.backend_usage.get(backend_id, 0) + 1

    def record_stream_stop(self) -> None:
        """Фиксация остановки стрима."""
        self.streams_stopped += 1

    def record_stream_failure(self) -> None:
        """Фиксация ошибки стрима."""
        self.streams_failed += 1

    def record_preview(self, backend_id: str) -> None:
        """Фиксация генерации превью."""
        self.previews_generated += 1
        self.backend_usage[backend_id] = self.backend_usage.get(backend_id, 0) + 1

    def record_preview_failure(self) -> None:
        """Фиксация ошибки генерации превью."""
        self.previews_failed += 1

    def record_fallback(self) -> None:
        """Фиксация переключения на резервный бэкенд."""
        self.fallback_count += 1

    def to_dict(self) -> dict:
        """Экспорт метрик в словарь."""
        return {
            "streams": {
                "started": self.streams_started,
                "stopped": self.streams_stopped,
                "failed": self.streams_failed,
                "active": self.streams_started - self.streams_stopped,
            },
            "previews": {
                "generated": self.previews_generated,
                "failed": self.previews_failed,
            },
            "backend_usage": dict(self.backend_usage),
            "fallback_count": self.fallback_count,
        }
