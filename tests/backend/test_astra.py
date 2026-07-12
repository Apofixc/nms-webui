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
            mock_instance.create_adapter.assert_called_once_with(adapter_payload)

            # 5. Тест удаления адаптера
            resp = client.delete("/api/v1/m/astra/monitoring/adapters/0/adapter_0")
            assert resp.status_code == 200
            assert resp.json() == {"ok": True, "response": {"status": "deleted", "name": "adapter_0"}}
            mock_instance.delete_adapter.assert_called_once_with("adapter_0")


