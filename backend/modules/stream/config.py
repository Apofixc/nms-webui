# Схема настроек модуля stream для системного загрузчика
import yaml
from pathlib import Path

SUBMODULES_DIR = Path(__file__).parent / "submodules"


def get_submodules_info():
    """Сканирует субмодули, возвращает их id, возможности и конфиги."""
    backends_stream = ["auto"]
    backends_preview = ["auto"]
    submodule_configs = {}

    if SUBMODULES_DIR.is_dir():
        for sub_dir in SUBMODULES_DIR.iterdir():
            if not sub_dir.is_dir():
                continue

            manifest_path = sub_dir / "manifest.yaml"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = yaml.safe_load(f)

                    b_id = manifest.get("id", sub_dir.name)
                    b_name = manifest.get("name", b_id)
                    caps = manifest.get("capabilities", [])

                    if "streaming" in caps or "proxy" in caps:
                        backends_stream.append(b_id)
                    if "preview" in caps:
                        backends_preview.append(b_id)

                    # Извлекаем config_schema субмодуля и добавляем префикс
                    schema = manifest.get("config_schema", {}).get("properties", {})
                    for key, prop in schema.items():
                        # Добавляем название субмодуля в группу для красоты UI
                        original_group = prop.get("group", "Настройки")
                        prop["group"] = f"{b_name} ({original_group})"
                        # Сохраняем под ключом с префиксом (например: astra_timeout)
                        prefixed_key = f"{b_id}_{key}"
                        submodule_configs[prefixed_key] = prop

                except Exception as e:
                    pass

    return backends_stream, backends_preview, submodule_configs


def schema() -> dict:
    """Возвращает JSON Schema настроек.
    Динамически включает доступные субмодули и их настройки.
    """
    backends_stream, backends_preview, submodule_configs = get_submodules_info()

    base_properties = {
        # --- Пул воркеров ---
        "worker_pool_size": {
            "type": "integer",
            "minimum": 1,
            "maximum": 32,
            "default": 4,
            "description": "Максимальное количество параллельных процессов стриминга",
            "group": "Ядро (Воркеры)",
        },
        "worker_timeout": {
            "type": "integer",
            "minimum": 5,
            "maximum": 300,
            "default": 30,
            "description": "Таймаут ожидания ответа от воркера (секунды)",
            "group": "Ядро (Воркеры)",
        },
        # --- Выбор бэкендов ---
        "preferred_stream_backend": {
            "type": "string",
            "enum": sorted(list(set(backends_stream))),
            "default": "auto",
            "description": "Предпочтительный бэкенд для стриминга",
            "group": "Маршрутизация",
        },
        "preferred_preview_backend": {
            "type": "string",
            "enum": sorted(list(set(backends_preview))),
            "default": "auto",
            "description": "Предпочтительный бэкенд для превью",
            "group": "Маршрутизация",
        },
    }

    # Объединяем базовые настройки с настройками субмодулей
    base_properties.update(submodule_configs)

    return {
        "type": "object",
        "properties": base_properties,
    }

