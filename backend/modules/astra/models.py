from pydantic import BaseModel, Field


class InstanceAdd(BaseModel):
    """Модель для добавления инстанса Astra."""
    host: str
    port: int = Field(ge=1, le=65535)
    api_key: str = "test"
    label: str | None = None


class InstanceUpdate(BaseModel):
    """Модель для обновления параметров инстанса Astra."""
    host: str | None = None
    port: int | None = None
    api_key: str | None = None
    label: str | None = None
