# Исключения модуля stream


class StreamError(Exception):
    """Базовое исключение модуля стриминга."""
    pass


class NoSuitableBackendError(StreamError):
    """Не найден подходящий бэкенд для выполнения задачи."""
    pass


class StreamPipelineError(StreamError):
    """Ошибка в конвейере обработки потоков."""
    pass


class BackendUnavailableError(StreamError):
    """Бэкенд недоступен (бинарник не найден, сервис не запущен)."""
    pass


class WorkerPoolExhaustedError(StreamError):
    """Все слоты в пуле воркеров заняты."""
    pass


class InvalidStreamURLError(StreamError):
    """Некорректный URL потока (не сетевой протокол или неверный формат)."""
    pass


class PreviewGenerationError(StreamError):
    """Ошибка при генерации превью."""
    pass
