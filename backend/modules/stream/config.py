# Схема настроек модуля stream для системного загрузчика
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Any

SUBMODULES_DIR = Path(__file__).parent / "submodules"


def get_submodules_details() -> Tuple[List[str], List[str], Dict[str, Any]]:
    """Сканирует субмодули и возвращает детальную информацию для генерации схемы."""
    backends_stream = ["auto"]
    backends_preview = ["auto"]
    submodule_data = {}

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
                    formats = manifest.get("formats", {})
                    
                    if "streaming" in caps or "proxy" in caps:
                        backends_stream.append(b_id)
                    
                    preview_formats = formats.get("preview_formats", [])
                    output_formats = formats.get("output_types", [])
                    input_protocols = formats.get("input_protocols", [])

                    if "preview" in caps:
                        backends_preview.append(b_id)

                    # Извлекаем свойства и добавляем префикс
                    raw_props = manifest.get("config_schema", {}).get("properties", {})
                    prefixed_props = {}
                    for key, prop in raw_props.items():
                        # Группировка для UI
                        original_group = prop.get("group", "Настройки")
                        prop["group"] = f"{b_name} ({original_group})"
                        prefixed_props[f"{b_id}_{key}"] = prop

                    submodule_data[b_id] = {
                        "name": b_name,
                        "preview_formats": ["auto"] + [f.lower() for f in preview_formats],
                        "output_formats": ["auto"] + [f.lower() for f in output_formats],
                        "input_protocols": [f.lower() for f in input_protocols],
                        "properties": prefixed_props
                    }

                except Exception:
                    continue

    return backends_stream, backends_preview, submodule_data


def schema() -> dict:
    """Возвращает динамическую JSON Schema настроек с зависимыми Enum.
    
    Использует конструкцию allOf + if-then для фильтрации форматов 
    и отображения специфичных настроек бэкенда.
    """
    backends_stream, backends_preview, submodules = get_submodules_details()

    # Собираем все форматы: стандартные + из субмодулей
    standard_preview_formats = ["auto", "jpeg", "png", "webp", "avif", "tiff", "gif"]
    all_preview_formats = set(standard_preview_formats)
    
    standard_output_formats = ["auto", "http_ts", "hls", "webrtc", "http"]
    all_output_formats = set(standard_output_formats)

    for info in submodules.values():
        all_preview_formats.update(info.get("preview_formats", []))
        all_output_formats.update(info.get("output_formats", []))
    
    global_preview_formats = sorted(list(all_preview_formats))
    global_output_formats = sorted(list(all_output_formats))

    # 1. Базовые свойства (всегда видны)
    # ВАЖНО: Enum здесь обязательны, чтобы UI понимал, что это dropdown (select)
    dynamic_properties = {
        "preferred_stream_backend": {
            "type": "string",
            "title": "Backend стриминга",
            "enum": sorted(list(set(backends_stream))),
        },
        "preferred_preview_backend": {
            "type": "string",
            "title": "Backend превью",
            "enum": sorted(list(set(backends_preview))),
        },
        "default_browser_player_format": {
            "type": "string",
            "title": "Тип выходного потока",
            "enum": global_output_formats,
        },
        "preview_format": {
            "type": "string",
            "title": "Формат снимков",
            "enum": global_preview_formats,
        }
    }

    # 2. Правила зависимостей (Cascading Logic)
    all_of_rules = []
    
    # Правило для случая "auto" — показываем расширенные списки
    all_of_rules.append({
        "if": { "properties": { "preferred_preview_backend": { "const": "auto" } } },
        "then": { "properties": { "preview_format": { "enum": global_preview_formats } } }
    })
    all_of_rules.append({
        "if": { "properties": { "preferred_stream_backend": { "const": "auto" } } },
        "then": { "properties": { "default_browser_player_format": { "enum": global_output_formats } } }
    })

    for b_id, info in submodules.items():
        # Правило для превью
        if b_id in backends_preview:
            # Для конкретного бэкенда сужаем список до его возможностей
            backend_formats = info.get("preview_formats", ["auto"])
            all_of_rules.append({
                "if": {
                    "properties": { "preferred_preview_backend": { "const": b_id } }
                },
                "then": {
                    "properties": {
                        "preview_format": {
                            "enum": backend_formats
                        },
                        **info["properties"]
                    }
                }
            })
        
        # Правило для стриминга
        if b_id in backends_stream:
            # Для конкретного бэкенда сужаем список форматов воспроизведения
            backend_output_formats = info.get("output_formats", ["auto"])
            all_of_rules.append({
                "if": {
                    "properties": { "preferred_stream_backend": { "const": b_id } }
                },
                "then": {
                    "properties": {
                        "default_browser_player_format": {
                            "enum": backend_output_formats
                        },
                        **info["properties"]
                    }
                }
            })

    return {
        "type": "object",
        "properties": dynamic_properties,
        "allOf": all_of_rules
    }

