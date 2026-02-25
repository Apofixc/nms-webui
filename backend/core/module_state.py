"""Состояние включенности модулей WebUI (enable/disable)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.core.config import _instances_path


def _state_path() -> Path:
    return _instances_path().parent / "modules_state.json"


def load_module_state() -> dict[str, bool]:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): bool(v) for k, v in data.items()}


def save_module_state(state: dict[str, bool]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def is_module_enabled(module_id: str, default: bool = True) -> bool:
    state = load_module_state()
    return state.get(module_id, default)


def set_module_enabled(module_id: str, enabled: bool) -> dict[str, bool]:
    state = load_module_state()
    state[module_id] = bool(enabled)
    save_module_state(state)
    return state


def get_module_state() -> dict[str, bool]:
    return load_module_state()
