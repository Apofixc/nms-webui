"""Точка входа модуля управления устройствами Tuya."""
from backend.core.plugin.context import ModuleContext
from backend.modules.tuya.module import TuyaModule


def create_module(ctx: ModuleContext) -> TuyaModule:
    """Фабричная функция создания экземпляра модуля Tuya."""
    return TuyaModule(ctx)
