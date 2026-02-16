"""Конфигурация: список инстансов Astra из YAML. Запись в файл."""
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class InstanceConfig(BaseModel):
    host: str
    port: int = Field(ge=1, le=65535)
    api_key: str = "test"
    label: str | None = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NMS_", extra="ignore")
    instances_file: Path = Path("instances.yaml")
    request_timeout: float = 10.0
    check_interval_sec: int = 30


_settings: Settings | None = None
_instances: list[InstanceConfig] | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def _instances_path() -> Path:
    p = get_settings().instances_file
    if not p.is_absolute():
        p = Path.cwd() / p
    return p


def reload_instances() -> None:
    """Сбросить кэш — при следующем load_instances() будет перечитан файл."""
    global _instances
    _instances = None


def load_instances() -> list[InstanceConfig]:
    """Загрузить инстансы из YAML. При ошибке — пустой список."""
    global _instances
    if _instances is not None:
        return _instances
    path = _instances_path()
    if not path.exists():
        _instances = []
        return _instances
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        raw = data.get("instances") or []
        _instances = [InstanceConfig(**x) for x in raw if isinstance(x, dict)]
    except Exception:
        _instances = []
    return _instances


def save_instances(instances: list[InstanceConfig]) -> None:
    """Сохранить список инстансов в YAML и сбросить кэш."""
    path = _instances_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "instances": [c.model_dump() for c in instances],
    }
    path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    reload_instances()


def add_instance(host: str, port: int, api_key: str = "test", label: str | None = None) -> InstanceConfig:
    """Добавить инстанс в конфиг (если такой host:port ещё нет). Вернуть добавленный или существующий."""
    current = load_instances()
    for c in current:
        if c.host == host and c.port == port:
            return c
    new_one = InstanceConfig(host=host, port=port, api_key=api_key, label=label)
    current = list(current)
    current.append(new_one)
    save_instances(current)
    return new_one


def remove_instance_by_index(index: int) -> bool:
    """Удалить инстанс по индексу. Вернуть True если удалён."""
    current = load_instances()
    if index < 0 or index >= len(current):
        return False
    new_list = [c for i, c in enumerate(current) if i != index]
    save_instances(new_list)
    return True


def get_instance_by_id(instance_id: int) -> tuple[InstanceConfig, str] | None:
    """Вернуть (config, base_url) по индексу или None."""
    instances = load_instances()
    if instance_id < 0 or instance_id >= len(instances):
        return None
    cfg = instances[instance_id]
    base = f"http://{cfg.host}:{cfg.port}"
    return (cfg, base)
