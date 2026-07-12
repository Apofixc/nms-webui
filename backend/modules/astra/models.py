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
        # Установка значений по умолчанию, если они пришли как None
        if self.device is None:
            self.device = 0
        if self.budget is None:
            self.budget = False
        if self.ca_pmt_delay is None:
            self.ca_pmt_delay = 3

        # Валидация по типам DVB-адаптеров
        if self.type in ("S", "S2"):
            if self.diseqc is None:
                self.diseqc = 0
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

            if self.type == "S2":
                if self.rolloff is None:
                    self.rolloff = "35"
            else:  # S
                if self.rolloff is not None:
                    raise ValueError("rolloff is only supported for DVB-S2")
                if self.stream_id is not None:
                    raise ValueError("stream_id is only supported for DVB-S2")

            for field in ("bandwidth", "guardinterval", "transmitmode", "hierarchy", "frequency", "symbolrate"):
                if getattr(self, field) is not None:
                    raise ValueError(f"{field} is not supported for DVB-S/S2")

            # Очистка несовместимых полей для сборки корректной таблицы
            self.bandwidth = None
            self.guardinterval = None
            self.transmitmode = None
            self.hierarchy = None
            self.frequency = None
            self.symbolrate = None
            if self.type == "S":
                self.rolloff = None
                self.stream_id = None

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

            if self.type == "T":
                if self.stream_id is not None:
                    raise ValueError("stream_id is only supported for DVB-T2")

            for field in ("tp", "lnb", "lnb_sharing", "diseqc", "tone", "rolloff", "uni_scr", "uni_frequency", "symbolrate"):
                if getattr(self, field) is not None:
                    raise ValueError(f"{field} is not supported for DVB-T/T2")

            # Очистка несовместимых полей для сборки корректной таблицы
            self.tp = None
            self.lnb = None
            self.lnb_sharing = None
            self.diseqc = None
            self.tone = None
            self.rolloff = None
            self.uni_scr = None
            self.uni_frequency = None
            self.symbolrate = None
            if self.type == "T":
                self.stream_id = None

        elif self.type in ("C", "C/AC", "C/B", "C/A", "C/C"):
            if self.frequency is None:
                raise ValueError("frequency is required for DVB-C")
            if self.symbolrate is None:
                raise ValueError("symbolrate is required for DVB-C")

            if self.modulation is None:
                self.modulation = "AUTO"

            for field in (
                "tp", "lnb", "lnb_sharing", "diseqc", "tone", "rolloff", "uni_scr", "uni_frequency",
                "bandwidth", "guardinterval", "transmitmode", "hierarchy", "stream_id"
            ):
                if getattr(self, field) is not None:
                    raise ValueError(f"{field} is not supported for DVB-C")

            # Очистка несовместимых полей для сборки корректной таблицы
            self.tp = None
            self.lnb = None
            self.lnb_sharing = None
            self.diseqc = None
            self.tone = None
            self.rolloff = None
            self.uni_scr = None
            self.uni_frequency = None
            self.stream_id = None
            self.bandwidth = None
            self.guardinterval = None
            self.transmitmode = None
            self.hierarchy = None

        elif self.type == "ATSC":
            if self.frequency is None:
                raise ValueError("frequency is required for ATSC")

            for field in (
                "tp", "lnb", "lnb_sharing", "diseqc", "tone", "rolloff", "uni_scr", "uni_frequency",
                "bandwidth", "guardinterval", "transmitmode", "hierarchy", "stream_id", "symbolrate"
            ):
                if getattr(self, field) is not None:
                    raise ValueError(f"{field} is not supported for ATSC")

            # Очистка несовместимых полей для сборки корректной таблицы
            self.tp = None
            self.lnb = None
            self.lnb_sharing = None
            self.diseqc = None
            self.tone = None
            self.rolloff = None
            self.uni_scr = None
            self.uni_frequency = None
            self.stream_id = None
            self.bandwidth = None
            self.guardinterval = None
            self.transmitmode = None
            self.hierarchy = None
            self.symbolrate = None

        elif self.type == "ASI":
            for field in (
                "tp", "lnb", "lnb_sharing", "diseqc", "tone", "rolloff", "uni_scr", "uni_frequency",
                "bandwidth", "guardinterval", "transmitmode", "hierarchy", "stream_id", "symbolrate", "frequency"
            ):
                if getattr(self, field) is not None:
                    raise ValueError(f"{field} is not supported for DVB-ASI")

            # Очистка несовместимых полей для сборки корректной таблицы (включая General опции)
            self.tp = None
            self.lnb = None
            self.lnb_sharing = None
            self.diseqc = None
            self.tone = None
            self.rolloff = None
            self.uni_scr = None
            self.uni_frequency = None
            self.stream_id = None
            self.bandwidth = None
            self.guardinterval = None
            self.transmitmode = None
            self.hierarchy = None
            self.symbolrate = None
            self.frequency = None
            self.device = None
            self.budget = None
            self.ca_pmt_delay = None
            self.modulation = None

        return self



