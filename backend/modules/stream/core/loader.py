# Динамический загрузчик субмодулей (v2)
import importlib
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional

from .contract import IStreamBackend
from .router import StreamRouter

logger = logging.getLogger(__name__)

# Директория с субмодулями относительно этого файла
SUBMODULES_DIR = Path(__file__).parent.parent / "submodules"


class SubmoduleLoader:
    """Загрузчик субмодулей на основе манифестов.

    Сканирует директорию submodules/, ищет manifest.yaml в каждой папке,
    загружает метаданные и регистрирует бэкенд в роутере.
    """

    def __init__(self, router: StreamRouter) -> None:
        self._router = router
        self._loaded: Dict[str, IStreamBackend] = {}
        self._manifests: Dict[str, dict] = {}

    def load_all(self, settings: dict | None = None) -> List[str]:
        """Загрузка всех доступных субмодулей через манифесты.

        Args:
            settings: Глобальные настройки модуля stream.

        Returns:
            Список ID успешно загруженных бэкендов.
        """
        loaded_ids = []

        if not SUBMODULES_DIR.is_dir():
            logger.error(f"Директория субмодулей не найдена: {SUBMODULES_DIR}")
            return []

        # Сканируем поддиректории
        for sub_dir in SUBMODULES_DIR.iterdir():
            if not sub_dir.is_dir():
                continue

            manifest_path = sub_dir / "manifest.yaml"
            if not manifest_path.exists():
                logger.debug(f"Пропуск {sub_dir.name}: manifest.yaml отсутствует")
                continue

            try:
                # 1. Загрузка манифеста
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = yaml.safe_load(f)

                sub_id = manifest.get("id", sub_dir.name)
                priority = manifest.get("priority", 100)
                
                entrypoints = manifest.get("entrypoints", {})
                factory_path = entrypoints.get("factory", "")
                if ":" in factory_path:
                    entry_point_module, factory_func = factory_path.split(":", 1)
                elif factory_path:
                    entry_point_module = factory_path
                else:
                    entry_point_module = f"backend.modules.stream.submodules.{sub_dir.name}"

                # 2. Импорт модуля
                module = importlib.import_module(entry_point_module)

                if not hasattr(module, "create_backend"):
                    logger.warning(f"Субмодуль '{sub_id}': отсутствует create_backend()")
                    continue

                # 3. Инициализация бэкенда
                # Получаем настройки:
                # 1. Из индивидуального реестра субмодуля (например, 'stream.ffmpeg') - ПРИОРИТЕТ
                # 2. Из префиксных значений в 'stream' (старый способ: 'ffmpeg_timeout') - для совместимости
                # 3. Из дефолтов манифеста
                sub_settings = {}
                
                try:
                    from backend.core.plugin.registry import get_module_settings
                    # Попытка №1: Прямые настройки субмодуля
                    sub_settings = get_module_settings(f"stream.{sub_id}") or {}
                except ImportError:
                    pass

                config_schema = manifest.get("config_schema", {}).get("properties", {})
                for key, prop in config_schema.items():
                    # Попытка №2: Префиксный ключ в родительском модуле (для обратной совместимости)
                    prefixed_key = f"{sub_id}_{key}"
                    if settings and prefixed_key in settings:
                        # Только если в sub_settings еще нет этого значения
                        if key not in sub_settings:
                            sub_settings[key] = settings[prefixed_key]
                    elif key not in sub_settings and "default" in prop:
                        # Попытка №3: Значение по умолчанию
                        sub_settings[key] = prop["default"]

                # комбинируем с глобальными для передачи (некоторые бэкенды могут хотеть worker_pool_size и т.д.)
                combined_settings = {**(settings or {}), **sub_settings}

                backend: IStreamBackend = module.create_backend(combined_settings)
                
                # 4. Регистрация в роутере
                self._router.register(backend, priority=priority)
                self._loaded[sub_id] = backend
                self._manifests[sub_id] = manifest
                
                loaded_ids.append(sub_id)
                logger.info(f"Субмодуль '{sub_id}' (v{manifest.get('version', '0.1')}) успешно загружен")

            except Exception as e:
                logger.error(f"Ошибка загрузки субмодуля в '{sub_dir.name}': {e}", exc_info=True)

        return loaded_ids

    def get_loaded(self) -> Dict[str, IStreamBackend]:
        """Возвращает словарь загруженных бэкендов."""
        return dict(self._loaded)

    def get_manifests(self) -> Dict[str, dict]:
        """Возвращает манифесты загруженных субмодулей."""
        return dict(self._manifests)

    def get_manifest(self, sub_id: str) -> Optional[dict]:
        """Возвращает манифест конкретного субмодуля."""
        return self._manifests.get(sub_id)
