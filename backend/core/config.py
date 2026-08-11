"""Системные настройки NMS-WebUI."""
from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings


def _get_or_create_secret_key() -> str:
    """Получить SECRET_KEY из env NMS_SECRET_KEY или персистентного файла data/.secret_key."""
    env_key = os.environ.get("NMS_SECRET_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    secret_file = data_dir / ".secret_key"
    legacy_file = data_dir / "secret.key"

    # Обратная совместимость с устаревшим secret.key если .secret_key ещё не создан
    if not secret_file.exists() and legacy_file.exists():
        try:
            key = legacy_file.read_text().strip()
            if key:
                return key
        except Exception:
            pass

    if secret_file.exists():
        try:
            key = secret_file.read_text().strip()
            if key:
                return key
        except Exception:
            pass

    new_key = secrets.token_urlsafe(64)
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        secret_file.write_text(new_key)
        try:
            os.chmod(secret_file, 0o600)
        except OSError:
            pass
    except Exception:
        pass
    return new_key


class Settings(BaseSettings):
    secret_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    enable_hsts: bool = False

    def model_post_init(self, __context):
        if not self.secret_key:
            self.secret_key = _get_or_create_secret_key()


@lru_cache
def get_settings() -> Settings:
    """Получить синглтон настроек."""
    raw_origins = os.environ.get("NMS_CORS_ORIGINS", "").strip()
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()] if raw_origins else ["http://localhost:5173", "http://127.0.0.1:5173"]
    hsts = os.environ.get("NMS_ENABLE_HSTS", "false").lower() in ("true", "1", "yes")

    return Settings(
        secret_key=os.environ.get("NMS_SECRET_KEY", "").strip(),
        cors_origins=origins,
        enable_hsts=hsts,
    )
