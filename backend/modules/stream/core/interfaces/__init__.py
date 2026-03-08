# Публичный API модуля stream для субмодулей (бэкендов).
# Субмодули ДОЛЖНЫ импортировать только из этого пакета,
# а не из внутренних компонентов core/.

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.session import BaseStreamSession, BufferedSession
from backend.modules.stream.core.types import (
    StreamTask,
    StreamResult,
    StreamProtocol,
    OutputType,
    PreviewFormat,
    BackendCapability,
    Priority,
)
from backend.modules.stream.core.exceptions import (
    StreamError,
    NoSuitableBackendError,
    StreamPipelineError,
    BackendUnavailableError,
    WorkerPoolExhaustedError,
    InvalidStreamURLError,
    PreviewGenerationError,
)

__all__ = [
    # Контракт
    "IStreamBackend",
    # Базовые сессии
    "BaseStreamSession",
    "BufferedSession",
    # Типы данных
    "StreamTask",
    "StreamResult",
    "StreamProtocol",
    "OutputType",
    "PreviewFormat",
    "BackendCapability",
    "Priority",
    # Исключения
    "StreamError",
    "NoSuitableBackendError",
    "StreamPipelineError",
    "BackendUnavailableError",
    "WorkerPoolExhaustedError",
    "InvalidStreamURLError",
    "PreviewGenerationError",
]
