import os
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NMS_", extra="ignore")

    request_timeout: float = 10.0
    check_interval_sec: int = 30
    log_level: str = "INFO"

    secret_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:9000"]
    secure_headers_enabled: bool = True

    celery_broker_url: str = "pyamqp://guest@localhost//"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        if not _settings.secret_key:
            _settings.secret_key = get_or_create_secret_key()
    return _settings


def get_or_create_secret_key() -> str:
    """Получить или сгенерировать секретный ключ и сохранить в data/.secret_key."""
    global _settings
    if _settings and _settings.secret_key:
        return _settings.secret_key

    # Пробуем прочитать из файла data/.secret_key
    key_file = DATA_DIR / ".secret_key"
    if key_file.exists():
        try:
            key = key_file.read_text(encoding="utf-8").strip()
            if key:
                if _settings:
                    _settings.secret_key = key
                return key
        except Exception:
            pass

    # Если файл не существует или пуст — генерируем новый ключ
    new_key = secrets.token_urlsafe(64)
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        key_file.write_text(new_key, encoding="utf-8")
        try:
            os.chmod(key_file, 0o600)
        except Exception:
            pass
    except Exception as e:
        import logging
        logging.getLogger("nms.config").warning("Could not persist secret key to %s: %s", key_file, e)

    if _settings:
        _settings.secret_key = new_key
    return new_key


