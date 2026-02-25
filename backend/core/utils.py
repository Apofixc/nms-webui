"""Общие утилиты. Поиск исполняемых файлов в PATH и стандартных путях."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

_COMMON_PREFIXES = ("/usr/bin", "/usr/local/bin")


def find_executable(name: str) -> Optional[str]:
    """
    Найти исполняемый файл по имени.
    Сначала ищет в PATH (shutil.which), затем в /usr/bin, /usr/local/bin.
    Так бэкенд находит ffmpeg/tsp даже при ограниченном PATH (например, при запуске из IDE).
    """
    path = shutil.which(name)
    if path:
        return path
    for prefix in _COMMON_PREFIXES:
        p = Path(prefix) / name
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
    return None
