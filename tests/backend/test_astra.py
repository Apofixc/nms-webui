import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.core.config import get_settings, save_instances
from backend.core.plugin.registry import register_instance, get_instance
from backend.core.plugin.context import ModuleContext

# Отключаем фоновую задачу AstraModule для тестов, чтобы pytest не зависал
from backend.modules.astra.module import AstraModule
AstraModule.start = lambda self: None
# stop возвращает корутину, так как в BaseModule он асинхронный
async def dummy_stop(self):
    pass
AstraModule.stop = dummy_stop

from backend.main import app


@pytest.fixture(autouse=True)
def setup_test_instances():
    """Фикстура для использования тестового файла instances.yaml и его очистки."""
    settings = get_settings()
    original_file = settings.instances_file
    test_file = Path("test_instances.yaml")
    settings.instances_file = test_file

    # Инициализируем пустым списком
    save_instances([])

    # Гарантируем, что инстанс AstraModule зарегистрирован в реестре
    module = get_instance("astra")
    if module is None:
        ctx = ModuleContext(
            module_id="astra",
            root=Path("backend/modules/astra"),
            manifest={},
            parent_module_id=None,
            is_submodule=False
        )
        module = AstraModule(ctx)
        register_instance("astra", module)

    yield

    # Очищаем за собой
    if test_file.exists():
        test_file.unlink()
    settings.instances_file = original_file


def test_crud_instances():
    """Тестирование добавления, обновления и удаления инстансов Astra."""
    with TestClient(app) as client:
        # 1. Список изначально пуст
        resp = client.get("/api/v1/m/astra/instances")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 0

        # 2. Добавление инстанса
        payload = {
            "host": "127.0.0.1",
            "port": 8001,
            "api_key": "secret",
            "label": "Test Astra",
        }
        resp = client.post("/api/v1/m/astra/instances", json=payload)
        assert resp.status_code == 200

        # Проверяем список
        resp = client.get("/api/v1/m/astra/instances")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["host"] == "127.0.0.1"
        assert items[0]["port"] == 8001
        assert items[0]["label"] == "Test Astra"
        assert items[0]["online"] is False  # В кэше модуля еще нет данных опроса

        # 3. Обновление инстанса
        update_payload = {"label": "Updated Label", "port": 8002}
        resp = client.put("/api/v1/m/astra/instances/0", json=update_payload)
        assert resp.status_code == 200

        resp = client.get("/api/v1/m/astra/instances")
        items = resp.json()["items"]
        assert items[0]["label"] == "Updated Label"
        assert items[0]["port"] == 8002

        # 4. Удаление инстанса
        resp = client.delete("/api/v1/m/astra/instances/0")
        assert resp.status_code == 200

        resp = client.get("/api/v1/m/astra/instances")
        assert len(resp.json()["items"]) == 0


def test_monitoring_summary_and_channels():
    """Тестирование мониторинга с замоканным AstraClient."""
    with TestClient(app) as client:
        # Добавим инстанс
        payload = {
            "host": "127.0.0.1",
            "port": 8001,
            "api_key": "secret",
            "label": "Test Astra",
        }
        client.post("/api/v1/m/astra/instances", json=payload)

        # Восстанавливаем инстанс в реестре, если первый тест при выходе очистил его
        module = get_instance("astra")
        assert module is not None

        mock_snapshot = {
            "instance": "Managed Instance 8001",
            "hostname": "test-host",
            "astra_version": "4.4.182",
            "time": 1700000000,
            "system": {
                "cpu_percent": 12.5,
                "mem_total_kb": 8000000,
                "mem_available_kb": 4000000,
                "astra_rss_kb": 15000,
            },
            "channels": [
                {
                    "name": "TV_TEST",
                    "ready": True,
                    "scrambled": False,
                    "bitrate": 4500,
                    "cc_errors": 0,
                    "pes_errors": 0,
                    "config": {
                        "input": ["http://127.0.0.1:8100/test"],
                        "output": ["udp://224.100.100.20:1234"],
                    },
                }
            ],
            "adapters": [
                {
                    "name": "Adapter 0",
                    "adapter": 0,
                    "type": "S",
                    "status": {"lock": True, "signal": 85, "snr": 12.4, "ber": 0, "unc": 0},
                }
            ],
            "events": [
                {
                    "time": 1700000000,
                    "level": "info",
                    "context": "system",
                    "message": "Astra started",
                }
            ],
        }

        # Записываем в кэш модуля
        key = "127.0.0.1:8001"
        module.cache[key] = {
            "online": True,
            "last_seen": 1700000000,
            "snapshot": mock_snapshot,
            "error": None,
        }
        module.history[key] = [{"time": 1700000000, "cpu": 12.5, "server_mem": 50.0, "astra_rss": 15000}]

        # 1. Запрос агрегированной статистики
        resp = client.get("/api/v1/m/astra/monitoring/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["instances_total"] == 1
        assert data["instances_online"] == 1
        assert data["channels_total"] == 1
        assert data["channels_ready"] == 1
        assert data["adapters_total"] == 1
        assert data["adapters_active"] == 1
        assert len(data["events"]) == 1
        assert data["events"][0]["message"] == "Astra started"

        # 2. Запрос списка каналов
        resp = client.get("/api/v1/m/astra/monitoring/channels")
        assert resp.status_code == 200
        chans = resp.json()["items"]
        assert len(chans) == 1
        assert chans[0]["name"] == "TV_TEST"
        assert chans[0]["ready"] is True
        assert chans[0]["bitrate"] == 4500

        # 3. Запрос списка адаптеров
        resp = client.get("/api/v1/m/astra/monitoring/adapters")
        assert resp.status_code == 200
        adaps = resp.json()["items"]
        assert len(adaps) == 1
        assert adaps[0]["name"] == "Adapter 0"
        assert adaps[0]["lock"] is True
        assert adaps[0]["snr"] == 12.4


def test_astra_controls():
    """Тестирование новых эндпоинтов управления (exit, channel/adapter create/delete/info)."""
    from unittest.mock import AsyncMock, patch
    with TestClient(app) as client:
        # Добавим инстанс
        payload = {
            "host": "127.0.0.1",
            "port": 8001,
            "api_key": "secret",
            "label": "Test Astra",
        }
        client.post("/api/v1/m/astra/instances", json=payload)

        # Мокаем AstraClient
        with patch("backend.modules.astra.api.AstraClient") as MockAstraClient:
            mock_instance = MockAstraClient.return_value
            mock_instance.exit_astra = AsyncMock(return_value={"ok": True})
            mock_instance.create_channel = AsyncMock(return_value={"status": "created", "name": "HTB"})
            mock_instance.get_channel_info = AsyncMock(return_value={"name": "HTB", "monitored": True, "config": {"input": ["http://1"], "output": ["udp://2"]}})
            mock_instance.create_adapter = AsyncMock(return_value={"status": "created", "name": "adapter_0"})
            mock_instance.delete_adapter = AsyncMock(return_value={"status": "deleted", "name": "adapter_0"})

            # 1. Тест Exit
            resp = client.post("/api/v1/m/astra/instances/0/exit")
            assert resp.status_code == 200
            assert resp.json() == {"ok": True, "detail": "Exit command sent"}
            mock_instance.exit_astra.assert_called_once()

            # 2. Тест создания канала с файловым входом/выходом, Softcam и BISS
            chan_payload = {
                "name": "HTB",
                "input": ["file:///opt/media/video.ts#loop&cam=reader_0&biss=1122330044556600&pass_sdt"],
                "output": ["file:///opt/media/record.ts#aio"],
                "monitor": True,
                "enable": True,
                "timeout": 5,
                "map": "pmt=100",
                "service_name": "HTB Channel",
                "service_provider": "NTV-Plus"
            }
            resp = client.post("/api/v1/m/astra/monitoring/channels/0/create", json=chan_payload)
            assert resp.status_code == 200
            assert resp.json() == {"ok": True, "response": {"status": "created", "name": "HTB"}}
            mock_instance.create_channel.assert_called_once_with(chan_payload)

            # 3. Тест получения инфо о канале
            resp = client.get("/api/v1/m/astra/monitoring/channels/0/HTB/info")
            assert resp.status_code == 200
            assert resp.json()["name"] == "HTB"
            mock_instance.get_channel_info.assert_called_once_with("HTB")

            # 4. Тест создания ATSC адаптера
            adapter_payload = {
                "name": "adapter_0",
                "adapter": 0,
                "type": "ATSC",
                "frequency": 360,
                "modulation": "VSB8",
                "monitor": True,
                "device": 1,
                "budget": True,
                "ca_pmt_delay": 5,
                "raw_signal": True,
                "log_signal": True
            }
            resp = client.post("/api/v1/m/astra/monitoring/adapters/0/create", json=adapter_payload)
            assert resp.status_code == 200
            assert resp.json() == {"ok": True, "response": {"status": "created", "name": "adapter_0"}}
            expected_payload = {**adapter_payload, "adapter": "0"}
            mock_instance.create_adapter.assert_called_once_with(expected_payload)

            # 5. Тест удаления адаптера
            resp = client.delete("/api/v1/m/astra/monitoring/adapters/0/adapter_0")
            assert resp.status_code == 200
            assert resp.json() == {"ok": True, "response": {"status": "deleted", "name": "adapter_0"}}
            mock_instance.delete_adapter.assert_called_once_with("adapter_0")


def test_adapter_validation_success():
    """Тестирование успешной валидации и заполнения дефолтных значений для различных типов DVB-адаптеров."""
    from backend.modules.astra.models import AdapterCreate

    # 1. DVB-S
    adap_s = AdapterCreate(
        name="adapter_s",
        adapter=0,
        type="S",
        tp="11044:V:43200",
    )
    assert adap_s.adapter == "0"
    assert adap_s.modulation == "NONE"
    assert adap_s.diseqc == 0
    assert adap_s.device == 0
    assert adap_s.budget is False
    assert adap_s.ca_pmt_delay == 3

    dump_s = adap_s.model_dump(exclude_none=True)
    assert "frequency" not in dump_s
    assert "symbolrate" not in dump_s
    assert "bandwidth" not in dump_s
    assert "tp" in dump_s
    assert dump_s["diseqc"] == 0
    assert dump_s["device"] == 0
    assert dump_s["budget"] is False
    assert dump_s["ca_pmt_delay"] == 3

    # 2. DVB-S2 с rolloff
    adap_s2 = AdapterCreate(
        name="adapter_s2",
        adapter="1",
        type="S2",
        tp="11044:H:43200",
        rolloff="25",
        stream_id=5,
    )
    assert adap_s2.adapter == "1"
    assert adap_s2.rolloff == "25"
    assert adap_s2.stream_id == 5

    dump_s2 = adap_s2.model_dump(exclude_none=True)
    assert dump_s2["rolloff"] == "25"
    assert dump_s2["stream_id"] == 5

    # 3. DVB-T
    adap_t = AdapterCreate(
        name="adapter_t",
        adapter=2,
        type="T",
        frequency=498,
    )
    assert adap_t.modulation == "AUTO"
    assert adap_t.bandwidth == "AUTO"
    assert adap_t.guardinterval == "AUTO"
    assert adap_t.transmitmode == "AUTO"
    assert adap_t.hierarchy == "AUTO"

    dump_t = adap_t.model_dump(exclude_none=True)
    assert "tp" not in dump_t
    assert "diseqc" not in dump_t
    assert dump_t["frequency"] == 498
    assert dump_t["bandwidth"] == "AUTO"

    # 4. DVB-T2 со stream_id
    adap_t2 = AdapterCreate(
        name="adapter_t2",
        adapter=3,
        type="T2",
        frequency=506,
        stream_id=1,
    )
    assert adap_t2.stream_id == 1

    dump_t2 = adap_t2.model_dump(exclude_none=True)
    assert dump_t2["stream_id"] == 1

    # 5. DVB-C
    adap_c = AdapterCreate(
        name="adapter_c",
        adapter=4,
        type="C",
        frequency=360,
        symbolrate=6900,
    )
    assert adap_c.symbolrate == 6900
    assert adap_c.modulation == "AUTO"

    dump_c = adap_c.model_dump(exclude_none=True)
    assert "tp" not in dump_c
    assert dump_c["frequency"] == 360
    assert dump_c["symbolrate"] == 6900

    # 6. ATSC
    adap_atsc = AdapterCreate(
        name="adapter_atsc",
        adapter=5,
        type="ATSC",
        frequency=360,
        modulation="VSB8",
    )
    assert adap_atsc.frequency == 360
    assert adap_atsc.modulation == "VSB8"

    dump_atsc = adap_atsc.model_dump(exclude_none=True)
    assert "tp" not in dump_atsc
    assert "symbolrate" not in dump_atsc
    assert dump_atsc["frequency"] == 360

    # 7. ASI
    adap_asi = AdapterCreate(
        name="adapter_asi",
        adapter=6,
        type="ASI",
    )
    assert adap_asi.type == "ASI"

    dump_asi = adap_asi.model_dump(exclude_none=True)
    assert "device" not in dump_asi
    assert "budget" not in dump_asi
    assert "ca_pmt_delay" not in dump_asi
    assert "modulation" not in dump_asi
    assert "tp" not in dump_asi
    assert "frequency" not in dump_asi
    assert dump_asi == {"name": "adapter_asi", "adapter": "6", "type": "ASI"}


def test_adapter_validation_failures():
    """Тестирование ошибок валидации и неподдерживаемых параметров для разных типов DVB-адаптеров."""
    from backend.modules.astra.models import AdapterCreate
    from pydantic import ValidationError

    # 1. Отсутствие tp для DVB-S
    with pytest.raises(ValidationError) as exc_info:
        AdapterCreate(name="adapter_err", adapter=0, type="S")
    assert "tp is required" in str(exc_info.value)

    # 2. Неверный формат tp
    with pytest.raises(ValidationError) as exc_info:
        AdapterCreate(name="adapter_err", adapter=0, type="S", tp="11044:X:43200")
    assert "tp must be in 'frequency:polarization:symbolrate' format" in str(exc_info.value)

    # 3. Неверный формат lnb
    with pytest.raises(ValidationError) as exc_info:
        AdapterCreate(name="adapter_err", adapter=0, type="S", tp="11044:V:43200", lnb="9750:10600")
    assert "lnb must be in 'lof1:lof2:slof' format" in str(exc_info.value)

    # 4. rolloff для DVB-S
    with pytest.raises(ValidationError) as exc_info:
        AdapterCreate(name="adapter_err", adapter=0, type="S", tp="11044:V:43200", rolloff="20")
    assert "rolloff is only supported for DVB-S2" in str(exc_info.value)

    # 5. Лишние поля для DVB-S (например, frequency)
    with pytest.raises(ValidationError) as exc_info:
        AdapterCreate(name="adapter_err", adapter=0, type="S", tp="11044:V:43200", frequency=360)
    assert "frequency is not supported for DVB-S/S2" in str(exc_info.value)

    # 6. Отсутствие frequency для DVB-T
    with pytest.raises(ValidationError) as exc_info:
        AdapterCreate(name="adapter_err", adapter=0, type="T")
    assert "frequency is required" in str(exc_info.value)

    # 7. stream_id для DVB-T
    with pytest.raises(ValidationError) as exc_info:
        AdapterCreate(name="adapter_err", adapter=0, type="T", frequency=498, stream_id=1)
    assert "stream_id is only supported for DVB-T2" in str(exc_info.value)

    # 8. tp для DVB-T
    with pytest.raises(ValidationError) as exc_info:
        AdapterCreate(name="adapter_err", adapter=0, type="T", frequency=498, tp="11044:V:43200")
    assert "tp is not supported for DVB-T/T2" in str(exc_info.value)

    # 9. Отсутствие symbolrate для DVB-C
    with pytest.raises(ValidationError) as exc_info:
        AdapterCreate(name="adapter_err", adapter=0, type="C", frequency=360)
    assert "symbolrate is required" in str(exc_info.value)

    # 10. Лишние поля для DVB-ASI (например, frequency)
    with pytest.raises(ValidationError) as exc_info:
        AdapterCreate(name="adapter_err", adapter=0, type="ASI", frequency=360)
    assert "frequency is not supported for DVB-ASI" in str(exc_info.value)


