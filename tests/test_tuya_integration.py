"""Интеграционная проверка интеграции модуля tuya с системой NMS-WebUI."""
from pathlib import Path
from backend.core.plugin.loader import discover_manifests
from backend.core.plugin.manifest import ModuleManifest


def test_tuya_manifest_discovery():
    """Проверка автоматического обнаружения manifest.yaml модуля tuya."""
    modules_dir = Path(__file__).resolve().parent.parent / "backend" / "modules"
    manifests = discover_manifests(modules_dir)

    tuya_manifest = next((m for m in manifests if m.id == "tuya"), None)
    assert tuya_manifest is not None, "Модуль tuya должен обнаруживаться в backend/modules"

    assert tuya_manifest.name in ("tuyaTitle", "Управление Tuya")

    assert tuya_manifest.type in ("driver", "feature")

    assert tuya_manifest.entrypoints.factory == "backend.modules.tuya:create_module"
    assert tuya_manifest.entrypoints.router == ["backend.modules.tuya.api:get_router"]


    # Проверка схемы настроек
    assert tuya_manifest.config_schema is not None
    props = tuya_manifest.config_schema.get("properties", {})
    assert "client_id" in props
    assert "client_secret" in props
    assert "region" in props
    assert "default_mode" in props

    # Проверка разрешений
    perm_ids = [p.id for p in tuya_manifest.permissions]
    assert "module.tuya.view" in perm_ids
    assert "module.tuya.edit" in perm_ids
    assert "module.tuya.control" in perm_ids


if __name__ == "__main__":
    test_tuya_manifest_discovery()
    print("[PASS] test_tuya_manifest_discovery")
