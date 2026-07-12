from backend.core.plugin.context import ModuleContext
from .module import AstraModule


def create_module(ctx: ModuleContext) -> AstraModule:
    """Точка входа (фабрика) для создания модуля astra."""
    return AstraModule(ctx)
