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


class ChannelCreate(BaseModel):
    """Модель для создания ТВ-канала в Astra."""
    name: str
    input: list[str]
    output: list[str]
    monitor: bool | dict | None = None
    enable: bool | None = None
    timeout: int | None = None
    map: str | None = None
    set_pnr: int | None = None
    set_tsid: int | None = None
    http_keep_active: int | None = None
    service_provider: str | None = None
    service_name: str | None = None


class AdapterCreate(BaseModel):
    """Модель для создания DVB-адаптера в Astra."""
    name: str
    adapter: int
    type: str
    tp: str | None = None
    lnb: str | None = None
    monitor: bool | dict | None = None
    device: int | None = None
    modulation: str | None = None
    budget: bool | None = None
    ca_pmt_delay: int | None = None
    raw_signal: bool | None = None
    log_signal: bool | None = None
    lnb_sharing: bool | None = None
    tone: bool | None = None
    diseqc: int | None = None
    rolloff: str | None = None
    uni_scr: int | None = None
    uni_frequency: int | None = None
    stream_id: int | None = None
    bandwidth: str | None = None
    guardinterval: str | None = None
    transmitmode: str | None = None
    hierarchy: str | None = None
    symbolrate: int | None = None
    frequency: int | None = None



