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
        # --- Выбор драйверов ---
        "preferred_stream_backend": {
            "type": "string",
            "title": "Backend стриминга",
            "enum": sorted(list(set(backends_stream + ["auto"]))),
            "default": "auto",
            "description": "Драйвер, используемый первым (Astra, FFmpeg и др.). auto — выбор по приоритету.",
            "group": "Видео (Глобально)",
        },
        "preferred_preview_backend": {
            "type": "string",
            "title": "Backend превью",
            "enum": sorted(list(set(backends_preview + ["auto"]))),
            "default": "auto",
            "description": "Драйвер для создания скриншотов.",
            "group": "Превью (Глобально)",
        },
        # --- Системные ресурсы ---
        "worker_pool_size": {
            "type": "integer",
            "title": "Максимум параллельных задач",
            "minimum": 1,
            "maximum": 32,
            "default": 4,
            "description": "Лимит одновременно запущенных процессов обработки видео.",
            "group": "Системы и Ресурсы",
        },
        "worker_timeout": {
            "type": "integer",
            "title": "Таймаут процесса (сек)",
            "minimum": 5,
            "maximum": 300,
            "default": 30,
            "description": "Максимальное время работы одной задачи.",
            "group": "Системы и Ресурсы",
        },
        # --- Параметры изображения ---
        "preview_format": {
            "type": "string",
            "title": "Формат снимков",
            "enum": ["jpeg", "png", "webp"],
            "default": "jpeg",
            "description": "Формат файлов превью по умолчанию.",
            "group": "Превью (Глобально)",
        },
        "preview_width": {
            "type": "integer",
            "title": "Ширина кадра (px)",
            "minimum": 64,
            "maximum": 1920,
            "default": 640,
            "description": "Ширина превью (пропорции сохраняются).",
            "group": "Превью (Глобально)",
        },
        "preview_quality": {
            "type": "integer",
            "title": "Качество сжатия (%)",
            "minimum": 1,
            "maximum": 100,
            "default": 75,
            "description": "Степень сжатия для JPEG и WebP.",
            "group": "Превью (Глобально)",
        },
        # --- Сетевые параметры ---
        "proxy_buffer_size": {
            "type": "integer",
            "title": "Размер буфера прокси",
            "minimum": 1024,
            "maximum": 1048576,
            "default": 65536,
            "description": "Объем памяти для проксирования (байт).",
            "group": "Сеть",
        },
        "http_timeout": {
            "type": "integer",
            "title": "Сетевой таймаут (сек)",
            "minimum": 1,
            "maximum": 60,
            "default": 10,
            "description": "Ожидание ответа от удаленного сервера.",
            "group": "Сеть",
        },
        # --- Интерфейс ---
        "default_browser_player_format": {
            "type": "string",
            "title": "Плеер по умолчанию",
            "enum": ["http_ts", "hls", "webrtc", "http"],
            "default": "http_ts",
            "description": "Формат потока при нажатии кнопки Play.",
            "group": "Видео (Глобально)",
        },
    }

    # Объединяем базовые настройки с настройками драйверов
    full_properties = {**base_properties, **submodule_configs}

    return {
        "type": "object",
        "properties": full_properties,
    }

