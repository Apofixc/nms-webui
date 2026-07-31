"""Тесты для модуля управления устройствами Tuya."""
import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from backend.core.plugin.context import ModuleContext
from backend.core.plugin.manifest import ModuleManifest
from backend.modules.tuya.client import TuyaCloudClient, TuyaDeviceController, TuyaLocalClient
from backend.modules.tuya.module import TuyaModule
from backend.modules.tuya.storage import TuyaDeviceSchema, TuyaStorage


def test_tuya_cloud_signature():
    """Проверка формирования подписи HMAC-SHA256 для Tuya Cloud OpenAPI."""
    client = TuyaCloudClient(client_id="test_client_id", client_secret="test_secret", region="eu")
    sign, t = client._calc_sign("GET", "/v1.0/devices/123", t="1600000000000", access_token="test_token")
    assert sign is not None
    assert len(sign) == 64
    assert sign.isupper()


def test_tuya_storage(tmp_path: Path):
    """Проверка создания, чтения, обновления и удаления устройств в TuyaStorage."""
    storage = TuyaStorage(tmp_path)
    assert len(storage.get_all()) == 0

    device = TuyaDeviceSchema(
        device_id="dev_001",
        name="Смарт Розетка",
        ip="192.168.1.100",
        local_key="1234567890123456",
        mode="auto",
    )
    storage.upsert(device)

    loaded = storage.get("dev_001")
    assert loaded is not None
    assert loaded.name == "Смарт Розетка"
    assert loaded.ip == "192.168.1.100"

    # Обновление статуса
    storage.update_status("dev_001", online=True, dps={"1": True})
    updated = storage.get("dev_001")
    assert updated.online is True
    assert updated.dps == {"1": True}

    # Удаление
    assert storage.delete("dev_001") is True
    assert storage.get("dev_001") is None


@pytest.mark.asyncio
async def test_tuya_device_controller_fallback():
    """Проверка работы TuyaDeviceController в гибридном режиме (auto fallback)."""
    mock_cloud = MagicMock(spec=TuyaCloudClient)
    mock_cloud.send_command = AsyncMock(return_value=True)

    controller = TuyaDeviceController(cloud_client=mock_cloud)

    # В режиме cloud
    res_cloud = await controller.send_command(
        device_id="dev_cloud",
        commands={"1": True},
        mode="cloud",
    )
    assert res_cloud is True
    mock_cloud.send_command.assert_called_once()

    # В режиме auto без локальных данных (IP) — должен примениться fallback на cloud
    mock_cloud.send_command.reset_mock()
    res_auto_fallback = await controller.send_command(
        device_id="dev_auto",
        commands={"1": True},
        mode="auto",
        ip=None,
        local_key=None,
    )
    assert res_auto_fallback is True
    mock_cloud.send_command.assert_called_once()


def test_tuya_module_lifecycle(tmp_path: Path):
    """Проверка жизненного цикла модуля Tuya."""
    manifest = ModuleManifest(id="tuya", name="Tuya Module")
    ctx = ModuleContext(
        module_id="tuya",
        root=tmp_path,
        manifest=manifest.to_api_dict(),
    )
    module = TuyaModule(ctx)
    module.init()

    status = module.get_status()
    assert status["active"] is False
    assert status["total_devices"] == 0

    # Проверка добавления устройства
    module.storage.upsert(TuyaDeviceSchema(device_id="dev_test", name="Тест"))
    new_status = module.get_status()
    assert new_status["total_devices"] == 1


if __name__ == "__main__":
    test_tuya_cloud_signature()
    print("[PASS] test_tuya_cloud_signature")

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_tuya_storage(Path(tmp_dir))
        print("[PASS] test_tuya_storage")
        test_tuya_module_lifecycle(Path(tmp_dir))
        print("[PASS] test_tuya_module_lifecycle")

    asyncio.run(test_tuya_device_controller_fallback())
    print("[PASS] test_tuya_device_controller_fallback")
    print("ALL TESTS PASSED SUCCESSFULLY!")

