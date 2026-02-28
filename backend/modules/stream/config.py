# Схема настроек модуля stream для системного загрузчика
# Используется через entrypoints.settings в manifest.yaml

def schema() -> dict:
    """Возвращает JSON Schema настроек модуля.

    Эта функция вызывается системным загрузчиком для регистрации
    пользовательских настроек в интерфейсе Settings.
    """
    return {
        "type": "object",
        "properties": {
            # --- Пул воркеров ---
            "worker_pool_size": {
                "type": "integer",
                "minimum": 1,
                "maximum": 32,
                "default": 4,
                "description": "Максимальное количество параллельных процессов стриминга",
                "group": "Воркеры",
            },
            "worker_timeout": {
                "type": "integer",
                "minimum": 5,
                "maximum": 300,
                "default": 30,
                "description": "Таймаут ожидания ответа от воркера (секунды)",
                "group": "Воркеры",
            },
            # --- Превью ---
            "preview_format": {
                "type": "string",
                "enum": ["jpeg", "png", "webp"],
                "default": "jpeg",
                "description": "Формат генерации превью по умолчанию",
                "group": "Превью",
            },
            "preview_width": {
                "type": "integer",
                "minimum": 64,
                "maximum": 1920,
                "default": 640,
                "description": "Ширина превью (пиксели)",
                "group": "Превью",
            },
            "preview_quality": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 75,
                "description": "Качество сжатия (для JPEG/WebP)",
                "group": "Превью",
            },
            # --- Выбор бэкендов ---
            "preferred_stream_backend": {
                "type": "string",
                "enum": ["auto", "ffmpeg", "vlc", "gstreamer", "astra", "tsduck", "pure_proxy"],
                "default": "auto",
                "description": "Предпочтительный бэкенд для стриминга",
                "group": "Бэкенды",
            },
            "preferred_preview_backend": {
                "type": "string",
                "enum": ["auto", "ffmpeg", "vlc", "gstreamer", "pure_preview"],
                "default": "auto",
                "description": "Предпочтительный бэкенд для превью",
                "group": "Бэкенды",
            },
            # --- Пути к бинарникам ---
            "ffmpeg_path": {
                "type": "string",
                "default": "ffmpeg",
                "description": "Путь к исполняемому файлу FFmpeg",
                "group": "Пути",
            },
            "vlc_path": {
                "type": "string",
                "default": "cvlc",
                "description": "Путь к исполняемому файлу VLC (headless)",
                "group": "Пути",
            },
            "gstreamer_path": {
                "type": "string",
                "default": "gst-launch-1.0",
                "description": "Путь к исполняемому файлу GStreamer",
                "group": "Пути",
            },
            "astra_path": {
                "type": "string",
                "default": "/opt/Cesbo-Astra-4.4.-monitor/astra4.4.182",
                "description": "Путь к бинарнику Astra 4.4.182",
                "group": "Пути",
            },
            "tsduck_path": {
                "type": "string",
                "default": "tsp",
                "description": "Путь к исполняемому файлу TSDuck (tsp)",
                "group": "Пути",
            },
            # --- Сеть ---
            "proxy_buffer_size": {
                "type": "integer",
                "minimum": 1024,
                "maximum": 1048576,
                "default": 65536,
                "description": "Размер буфера проксирования (байты)",
                "group": "Сеть",
            },
            "http_timeout": {
                "type": "integer",
                "minimum": 1,
                "maximum": 60,
                "default": 10,
                "description": "Таймаут HTTP-подключений (секунды)",
                "group": "Сеть",
            },
        },
    }
