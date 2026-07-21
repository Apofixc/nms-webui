import re
from typing import Literal, Any
from pydantic import BaseModel, Field, model_validator, field_validator


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


DVBType = Literal["S", "S2", "T", "T2", "C", "C/AC", "C/B", "C/A", "C/C", "ATSC", "ASI"]
ModulationType = Literal[
    "NONE", "AUTO", "QPSK", "QAM16", "QAM32", "QAM64", "QAM128", "QAM256",
    "VSB8", "VSB16", "PSK8", "APSK16", "APSK32", "DQPSK"
]


class AdapterCreate(BaseModel):
    """Модель для создания DVB-адаптера в Astra."""
    name: str
    adapter: str
    type: DVBType
    tp: str | None = None
    lnb: str | None = None
    monitor: bool | dict | None = None
    device: int | None = 0
    modulation: ModulationType | None = None
    budget: bool | None = False
    ca_pmt_delay: int | None = 3
    buffer_size: int | None = None
    raw_signal: bool | None = None
    log_signal: bool | None = None
    lnb_sharing: bool | None = None
    tone: bool | None = None
    diseqc: int | None = None
    rolloff: Literal["AUTO", "20", "25", "35"] | None = None
    uni_scr: int | None = None
    uni_frequency: int | None = None
    stream_id: int | None = None
    bandwidth: Literal["AUTO", "6mhz", "7mhz", "8mhz"] | None = None
    guardinterval: Literal["AUTO", "1/4", "1/8", "1/16", "1/32"] | None = None
    transmitmode: Literal["AUTO", "1K", "2K", "4K", "8K", "16K", "32K"] | None = None
    hierarchy: Literal["NONE", "AUTO", "1", "2", "4"] | None = None
    symbolrate: int | None = None
    frequency: int | None = None

    @field_validator("adapter", mode="before")
    @classmethod
    def coerce_adapter_to_str(cls, v: Any) -> str:
        if isinstance(v, (int, float)):
            return str(int(v))
        return str(v)

    @model_validator(mode="after")
    def validate_dvb_fields(self) -> "AdapterCreate":
        # Установка значений по умолчанию для General опций
        if self.device is None:
            self.device = 0
        if self.budget is None:
            self.budget = False
        if self.ca_pmt_delay is None:
            self.ca_pmt_delay = 3

        # Определение специфичных полей
        specific_fields = {
            "tp", "lnb", "lnb_sharing", "diseqc", "tone", "rolloff", 
            "uni_scr", "uni_frequency", "stream_id", "bandwidth", 
            "guardinterval", "transmitmode", "hierarchy", "symbolrate", "frequency"
        }

        # Определение разрешенных специфичных полей для каждого типа DVB
        if self.type in ("S", "S2"):
            allowed_specific = {"tp", "lnb", "lnb_sharing", "diseqc", "tone", "uni_scr", "uni_frequency"}
            if self.type == "S2":
                allowed_specific.update({"rolloff", "stream_id"})
        elif self.type in ("T", "T2"):
            allowed_specific = {"frequency", "bandwidth", "guardinterval", "transmitmode", "hierarchy"}
            if self.type == "T2":
                allowed_specific.add("stream_id")
        elif self.type in ("C", "C/AC", "C/B", "C/A", "C/C"):
            allowed_specific = {"frequency", "symbolrate"}
        elif self.type == "ATSC":
            allowed_specific = {"frequency"}
        elif self.type == "ASI":
            allowed_specific = set()
        else:
            allowed_specific = set()

        # Проверка и очистка несовместимых специфичных полей
        forbidden_fields = specific_fields - allowed_specific
        for field in forbidden_fields:
            if getattr(self, field) is not None:
                raise ValueError(f"{field} is not supported for DVB-{self.type}")
            # Зануляем несовместимые поля
            setattr(self, field, None)

        # Специфичные проверки форматов и обязательных полей
        if self.type in ("S", "S2"):
            if not self.tp:
                raise ValueError("tp is required for DVB-S/S2")
            tp_match = re.match(r"^(\d+):([VHRL]):(\d+)$", self.tp)
            if not tp_match:
                raise ValueError(
                    "tp must be in 'frequency:polarization:symbolrate' format (e.g. '11044:V:43200') where polarization is V, H, R, or L"
                )
            if self.lnb:
                lnb_match = re.match(r"^(\d+):(\d+):(\d+)$", self.lnb)
                if not lnb_match:
                    raise ValueError("lnb must be in 'lof1:lof2:slof' format (e.g. '9750:10600:11700')")
            
            if self.modulation is None:
                self.modulation = "NONE"
            if self.diseqc is None:
                self.diseqc = 0
            if self.type == "S2" and self.rolloff is None:
                self.rolloff = "35"

        elif self.type in ("T", "T2"):
            if self.frequency is None:
                raise ValueError("frequency is required for DVB-T/T2")
            
            if self.modulation is None:
                self.modulation = "AUTO"
            if self.bandwidth is None:
                self.bandwidth = "AUTO"
            if self.guardinterval is None:
                self.guardinterval = "AUTO"
            if self.transmitmode is None:
                self.transmitmode = "AUTO"
            if self.hierarchy is None:
                self.hierarchy = "AUTO"

        elif self.type in ("C", "C/AC", "C/B", "C/A", "C/C"):
            if self.frequency is None:
                raise ValueError("frequency is required for DVB-C")
            if self.symbolrate is None:
                raise ValueError("symbolrate is required for DVB-C")

            if self.modulation is None:
                self.modulation = "AUTO"

        elif self.type == "ATSC":
            if self.frequency is None:
                raise ValueError("frequency is required for ATSC")
            
            if self.modulation is None:
                self.modulation = "VSB8"

        return self


class InstancesScanRequest(BaseModel):
    """Модель для запроса слепого сканирования."""
    subnet: str | None = None
    ports: list[int] = Field(default_factory=lambda: [8000])
    api_key: str = "test"
    timeout: float = 1.0


class InstancesScanResultItem(BaseModel):
    """Модель элемента результата сканирования."""
    host: str
    port: int
    api_key: str
    label: str
    online: bool
    version: str




