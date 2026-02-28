# Загрузчик субмодулей (бэкендов)
import importlib
import logging
from pathlib import Path
from typing import Dict, List

from .contract import IStreamBackend
from .router import StreamRouter

logger = logging.getLogger(__name__)

# Директория с субмодулями относительно этого файла
SUBMODULES_DIR = Path(__file__).parent.parent / "submodules"

# Карта субмодулей и их приоритеты по умолчанию
DEFAULT_SUBMODULE_CONFIG = {
    "ffmpeg":       {"priority": 10,  "module": "backend.modules.stream.submodules.ffmpeg"},
    "vlc":          {"priority": 20,  "module": "backend.modules.stream.submodules.vlc"},
    "gstreamer":    {"priority": 30,  "module": "backend.modules.stream.submodules.gstreamer"},
    "astra":        {"priority": 40,  "module": "backend.modules.stream.submodules.astra"},
    "tsduck":       {"priority": 50,  "module": "backend.modules.stream.submodules.tsduck"},
    "pure_proxy":   {"priority": 60,  "module": "backend.modules.stream.submodules.pure_proxy"},
    "pure_webrtc":  {"priority": 70,  "module": "backend.modules.stream.submodules.pure_webrtc"},
    "pure_preview": {"priority": 80,  "module": "backend.modules.stream.submodules.pure_preview"},
}


class SubmoduleLoader:
    """Загрузчик субмодулей.

    Сканирует директорию submodules/ и регистрирует
    все найденные бэкенды в роутере.
    """

    def __init__(self, router: StreamRouter) -> None:
        self._router = router
        self._loaded: Dict[str, IStreamBackend] = {}

    def load_all(self, settings: dict | None = None) -> List[str]:
        """Загрузка всех доступных субмодулей.

        Args:
            settings: Пользовательские настройки модуля (пути к бинарникам и т.д.)

        Returns:
            Список ID успешно загруженных бэкендов.
        """
        loaded_ids = []

        for sub_id, config in DEFAULT_SUBMODULE_CONFIG.items():
            sub_path = SUBMODULES_DIR / sub_id
            if not sub_path.is_dir():
                logger.debug(f"Субмодуль '{sub_id}': директория не найдена, пропуск")
                continue

            try:
                module = importlib.import_module(config["module"])
                # Каждый субмодуль должен предоставить функцию create_backend
                if not hasattr(module, "create_backend"):
                    logger.warning(
                        f"Субмодуль '{sub_id}': отсутствует create_backend()"
                    )
                    continue

                backend: IStreamBackend = module.create_backend(settings or {})
                self._router.register(backend, priority=config["priority"])
                self._loaded[sub_id] = backend
                loaded_ids.append(sub_id)
                logger.info(f"Субмодуль '{sub_id}' успешно загружен")

            except Exception as e:
                logger.warning(f"Субмодуль '{sub_id}': ошибка загрузки — {e}")

        return loaded_ids

    def get_loaded(self) -> Dict[str, IStreamBackend]:
        """Возвращает словарь загруженных бэкендов."""
        return dict(self._loaded)
