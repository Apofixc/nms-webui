"""Тесты для проверки однослойных субмодулей и строгой валидации манифеста."""
from __future__ import annotations

from pathlib import Path
import pytest
from pydantic import ValidationError
import yaml

from backend.core.plugin.manifest import ModuleManifest
from backend.core.plugin.loader import discover_manifests, _parse_manifest
from backend.core.plugin.registry import get_module_error, clear_module_error


def test_nested_submodule_rejected(tmp_path: Path):
    """Вложенный субмодуль (папка submodules внутри субмодуля) отклоняется с ошибкой."""
    clear_module_error("parent.child")

    modules_dir = tmp_path / "modules"
    parent_dir = modules_dir / "parent"
    child_dir = parent_dir / "submodules" / "child"
    nested_dir = child_dir / "submodules" / "grandchild"

    parent_dir.mkdir(parents=True)
    child_dir.mkdir(parents=True)
    nested_dir.mkdir(parents=True)

    (parent_dir / "manifest.yaml").write_text(yaml.dump({
        "id": "parent",
        "name": "Parent Module",
        "entrypoints": {"factory": "pkg.mod:create"}
    }), encoding="utf-8")

    (child_dir / "manifest.yaml").write_text(yaml.dump({
        "id": "child",
        "name": "Child Submodule",
        "parent": "parent",
        "entrypoints": {"factory": "pkg.mod:create_sub"}
    }), encoding="utf-8")

    (nested_dir / "manifest.yaml").write_text(yaml.dump({
        "id": "grandchild",
        "name": "Nested Submodule",
        "parent": "child",
        "entrypoints": {"factory": "pkg.mod:create_nested"}
    }), encoding="utf-8")

    manifests = discover_manifests(modules_dir)

    # Родительский модуль найден
    manifest_ids = [m.id for m in manifests]
    assert "parent" in manifest_ids
    # Субмодуль child с парой submodules/ внутри не загрузился
    assert "parent.child" not in manifest_ids
    assert "parent.child.grandchild" not in manifest_ids

    # Зарегистрирована ошибка для субмодуля
    err = get_module_error("parent.child")
    assert err == "вложенные субмодули запрещены"


def test_invalid_manifest_type_i18n_entrypoints_parent(tmp_path: Path):
    """Неверный type, некорректный entrypoints, parent с точкой отклоняются."""
    # 1. Неверный type
    with pytest.raises(ValidationError):
        ModuleManifest(id="test_mod", type="invalid_type")

    # 2. Некорректный entrypoints (без двоеточия)
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(yaml.dump({
        "id": "test_mod",
        "type": "feature",
        "entrypoints": {"router": "invalid_router_path"}
    }), encoding="utf-8")

    manifest = _parse_manifest(manifest_file)
    assert manifest is None

    # 3. Parent с точкой
    with pytest.raises(ValidationError):
        ModuleManifest(id="child", parent="parent.submodule")

    # 4. Проверка отсутствия поля i18n
    valid_m = ModuleManifest(
        id="test_i18n_mod",
        entrypoints={"factory": "pkg.mod:factory_fn"}
    )
    assert not hasattr(valid_m, "i18n")
    assert "i18n" not in valid_m.to_api_dict()


def test_valid_single_layer_module_loads(tmp_path: Path):
    """Валидный однослойный модуль с субмодулем успешно сканируется."""
    modules_dir = tmp_path / "modules"
    parent_dir = modules_dir / "drivers"
    child_dir = parent_dir / "submodules" / "cisco"

    parent_dir.mkdir(parents=True)
    child_dir.mkdir(parents=True)

    (parent_dir / "manifest.yaml").write_text(yaml.dump({
        "id": "drivers",
        "name": "Network Drivers",
        "type": "system",
        "entrypoints": {"factory": "pkg.drivers:create"}
    }), encoding="utf-8")

    (child_dir / "manifest.yaml").write_text(yaml.dump({
        "id": "cisco",
        "name": "Cisco Driver",
        "type": "driver",
        "parent": "drivers",
        "entrypoints": {"factory": "pkg.drivers.cisco:create"}
    }), encoding="utf-8")

    manifests = discover_manifests(modules_dir)
    m_ids = [m.id for m in manifests]

    assert "drivers" in m_ids
    assert "drivers.cisco" in m_ids
    assert len(manifests) == 2


def test_manifest_events_schema_and_publishes_validation():
    """Тест валидации секции events и правила 1-го сегмента publishes."""
    # 1. Валидный модуль с совпадающим 1-м сегментом
    m_valid = ModuleManifest(
        id="sensor_monitor",
        events={
            "publishes": ["sensor_monitor.alert_triggered", "sensor_monitor.data_updated"],
            "subscribes": ["core.modules.enabled"]
        }
    )
    assert m_valid.events.publishes == ["sensor_monitor.alert_triggered", "sensor_monitor.data_updated"]
    assert m_valid.events.subscribes == ["core.modules.enabled"]
    assert m_valid.to_api_dict()["events"] == {
        "publishes": ["sensor_monitor.alert_triggered", "sensor_monitor.data_updated"],
        "subscribes": ["core.modules.enabled"]
    }

    # 2. Неверный 1-й сегмент публикации отклоняется с ValidationError
    with pytest.raises(ValidationError):
        ModuleManifest(
            id="sensor_monitor",
            events={
                "publishes": ["other_module.alert_triggered"]
            }
        )


def test_route_schema_explicit_component():
    """Тест явного задания component в RouteSchema."""
    m = ModuleManifest(
        id="test_route_mod",
        routes=[
            {
                "path": "/test",
                "name": "test-index",
                "component": "views/CustomTestView.vue"
            }
        ]
    )
    assert m.routes[0].component == "views/CustomTestView.vue"
    api_routes = m.to_api_dict()["routes"]
    assert api_routes[0]["component"] == "views/CustomTestView.vue"


def test_event_publish_mismatch_warning(caplog):
    """Тест генерации warning при публикации не задекларированного в манифесте события."""
    import logging
    from backend.core.plugin.registry import register_manifest
    from backend.core.plugin.context import ModuleEvents

    manifest = ModuleManifest(
        id="event_test_mod",
        events={
            "publishes": ["event_test_mod.declared_event"],
            "subscribes": []
        }
    )
    register_manifest(manifest)

    events_context = ModuleEvents("event_test_mod")

    with caplog.at_level(logging.WARNING, logger="nms.plugin.loader"):
        # Публикация не задекларированного события должна выдать warning
        events_context.publish("undeclared_event")
        assert "not declared in manifest.events.publishes" in caplog.text


def test_validate_module_subscriptions_warnings(caplog):
    """Тест сверки подписок с реестром при загрузке модуля."""
    import logging
    from backend.core.plugin.registry import register_manifest
    from backend.core.plugin.loader import validate_module_subscriptions

    subscriber = ModuleManifest(
        id="sub_mod",
        events={
            "publishes": [],
            "subscribes": ["missing_publisher.some_event"]
        }
    )
    register_manifest(subscriber)

    with caplog.at_level(logging.WARNING, logger="nms.plugin.loader"):
        validate_module_subscriptions(subscriber)
        assert "publisher module 'missing_publisher' is not registered" in caplog.text

