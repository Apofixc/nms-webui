# Точка входа модуля stream для системного загрузчика
from backend.core.plugin.context import ModuleContext
from .module import StreamModule
from .api import set_module


def create_module(ctx: ModuleContext) -> StreamModule:
    """Фабричная функция для создания экземпляра модуля.

    После создания модуля привязывает его к API-роутеру,
    чтобы эндпоинты имели доступ к pipeline, worker_pool и метрикам.
    """
    module = StreamModule(ctx)
    # Привязка модуля к API для доступа из эндпоинтов
    set_module(module)
    return module
