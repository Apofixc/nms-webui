"""Astra module — точка входа (factory)."""
from backend.core.plugin.context import ModuleContext
from backend.modules.astra.module import AstraModule


def create_module(ctx: ModuleContext) -> AstraModule:
    return AstraModule(ctx)
