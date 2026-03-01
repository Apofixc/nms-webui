# Нативная логика проксирования (HTTP/HLS/UDP)
# Данные перекачиваются при HTTP-запросе клиента через api.py → proxy_stream()
import asyncio
import logging
import time
from typing import Dict, Optional

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType
)

logger = logging.getLogger(__name__)


class ProxySession:
    """Информация об активной прокси-сессии."""

    def __init__(self, task_id: str, task: StreamTask):
        self.task_id = task_id
        self.task = task
        self.started_at = time.time()
        self._cancel_event = asyncio.Event()

    def cancel(self) -> None:
        """Сигнал отмены сессии."""
        self._cancel_event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()


class PureProxyStreamer:
    """Нативный прокси на базе aiohttp и asyncio.

    Управляет регистрацией прокси-сессий. Фактическая перекачка
    данных выполняется в api.py → proxy_stream() при HTTP-запросе клиента.
    Все параметры (буферы, таймауты) берутся из settings.
    """

    def __init__(self, settings: dict):
        self.buffer_size = settings.get("buffer_size", 65536)
        self.connect_timeout = settings.get("connect_timeout", 15)
        self.read_timeout = settings.get("read_timeout", 30)
        self.max_redirects = settings.get("max_redirects", 5)
        self.udp_recv_buffer = settings.get("udp_recv_buffer", 65536)
        self._sessions: Dict[str, ProxySession] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        """Регистрация прокси-сессии.

        Не запускает фоновый процесс — данные будут переданы
        при HTTP-запросе клиента через /proxy/{task_id}.
        """
        task_id = task.task_id or ""

        # Регистрируем сессию
        session = ProxySession(task_id=task_id, task=task)
        self._sessions[task_id] = session

        logger.info(
            f"Прокси-сессия '{task_id}' зарегистрирована: "
            f"{task.input_url} → {task.output_type.value}"
        )

        return StreamResult(
            task_id=task_id,
            success=True,
            backend_used="pure_proxy",
            output_url=f"/api/modules/stream/v1/proxy/{task_id}",
            metadata={
                "type": "native_proxy",
                "protocol": task.input_protocol.value,
                "buffer_size": self.buffer_size,
                "connect_timeout": self.connect_timeout,
            }
        )

    async def stop(self, task_id: str) -> bool:
        """Отмена прокси-сессии."""
        session = self._sessions.pop(task_id, None)
        if session:
            session.cancel()
            logger.info(f"Прокси-сессия '{task_id}' остановлена")
            return True
        return False

    def get_session(self, task_id: str) -> Optional[ProxySession]:
        """Получение сессии по ID."""
        return self._sessions.get(task_id)

    def get_active_count(self) -> int:
        """Количество активных прокси-сессий."""
        return len(self._sessions)
