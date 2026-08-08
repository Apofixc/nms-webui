"""Глобальная конфигурация приложения NMS WebUI."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NMS_", extra="ignore")

    request_timeout: float = 10.0
    check_interval_sec: int = 30
    log_level: str = "INFO"



_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

