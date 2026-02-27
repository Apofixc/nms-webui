class NoBackendFound(Exception):
    """Нет подходящего бэкенда для пары (input_protocol, output_format)."""


class BackendInitializationError(Exception):
    """Ошибка инициализации бэкенда."""


class BackendProcessError(Exception):
    """Ошибка выполнения задачи бэкендом."""
