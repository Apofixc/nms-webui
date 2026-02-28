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
            "title": "Параллельные процессы (воркеры)",
            "minimum": 1,
            "maximum": 32,
            "default": 4,
            "description": "Максимальное число одновременно запущенных задач стриминга (FFmpeg/VLC и др.)",
            "group": "Система и Ресурсы",
        },
        "worker_timeout": {
            "type": "integer",
            "title": "Таймаут воркера (сек)",
            "minimum": 5,
            "maximum": 300,
            "default": 30,
            "description": "Время ожидания ответа от процесса перед его принудительной остановкой",
            "group": "Система и Ресурсы",
        },
        # --- Выбор бэкендов ---
        "preferred_stream_backend": {
            "type": "string",
            "title": "Основной драйвер вещания",
            "enum": sorted(list(set(backends_stream))),
            "default": "auto",
            "description": "Драйвер, который будет пробовать запуститься первым (auto = автоматический выбор)",
            "group": "Движки и Драйверы",
        },
        "preferred_preview_backend": {
            "type": "string",
            "title": "Основной драйвер превью",
            "enum": sorted(list(set(backends_preview))),
            "default": "auto",
            "description": "Драйвер для генерации скриншотов (auto = автоматический выбор)",
            "group": "Движки и Драйверы",
        },
        "default_browser_player_format": {
            "type": "string",
            "title": "Формат плеера по умолчанию",
            "enum": ["http_ts", "hls", "webrtc", "http"],
            "default": "http_ts",
            "description": "Формат потока, который запрашивается при нажатии Play в карточке канала",
            "group": "Интерфейс",
        },
        # --- Параметры изображения ---
        "preview_format": {
            "type": "string",
            "title": "Формат снимков (превью)",
            "enum": ["jpeg", "png", "webp"],
            "default": "jpeg",
            "description": "Формат файлов для сохранения превью каналов",
            "group": "Превью",
        },
        "preview_width": {
            "type": "integer",
            "title": "Ширина кадра (px)",
            "minimum": 64,
            "maximum": 1920,
            "default": 640,
            "description": "Размер превью по горизонтали (пропорции сохраняются)",
            "group": "Превью",
        },
        "preview_quality": {
            "type": "integer",
            "title": "Качество сжатия (%)",
            "minimum": 1,
            "maximum": 100,
            "default": 75,
            "description": "Для форматов JPEG и WebP (1-100)",
            "group": "Превью",
        },
        # --- Сеть ---
        "proxy_buffer_size": {
            "type": "integer",
            "title": "Размер буфера прокси (байт)",
            "minimum": 1024,
            "maximum": 1048576,
            "default": 65536,
            "description": "Объем данных для внутреннего прокси-сервера",
            "group": "Сеть",
        },
        "http_timeout": {
            "type": "integer",
            "title": "Таймаут сети (сек)",
            "minimum": 1,
            "maximum": 60,
            "default": 10,
            "description": "Максимальное время ожидания HTTP-ответа от источника",
            "group": "Сеть",
        },
    }

    return {
        "type": "object",
        "properties": base_properties,
    }

