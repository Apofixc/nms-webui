"""Тесты единого механизма виджетов (backend)."""
import pytest
from backend.core.plugin.manifest import WidgetSchema, ModuleManifest
from backend.core.plugin.widgets import (
    WidgetStatus,
    WidgetType,
    WidgetMetric,
    WidgetAction,
    WidgetDataResponse,
)
from backend.modules.tuya.widgets import get_tuya_summary_widget


def test_widget_schemas_validation():
    """Проверка создания и сериализации единой схемы ответа виджетов."""
    metric = WidgetMetric(
        id="online_cnt",
        label="В сети",
        value=10,
        unit="шт",
        status=WidgetStatus.OK,
        icon="check_circle",
    )
    action = WidgetAction(label="Управление", path="/tuya", icon="arrow_forward")

    resp = WidgetDataResponse(
        status=WidgetStatus.OK,
        type=WidgetType.SUMMARY,
        title="Сводка Tuya",
        metrics=[metric],
        actions=[action],
        extra={"custom_field": 123},
    )

    data = resp.model_dump()
    assert data["status"] == "ok"
    assert data["type"] == "summary"
    assert data["title"] == "Сводка Tuya"
    assert len(data["metrics"]) == 1
    assert data["metrics"][0]["id"] == "online_cnt"
    assert data["metrics"][0]["value"] == 10
    assert len(data["actions"]) == 1
    assert data["actions"][0]["path"] == "/tuya"
    assert data["extra"]["custom_field"] == 123


def test_manifest_widget_schema():
    """Проверка расширенных полей WidgetSchema в манифесте модуля."""
    w = WidgetSchema(
        id="tuya-summary",
        title="tuyaWidgetTitle",
        endpoint="/api/v1/m/tuya/widgets/summary",
        refresh_interval=30,
        type="summary",
    )
    assert w.id == "tuya-summary"
    assert w.refresh_interval == 30
    assert w.type == "summary"

    manifest = ModuleManifest(
        id="test-mod",
        widgets=[w],
    )
    dumped = manifest.to_api_dict() if hasattr(manifest, "to_api_dict") else manifest.model_dump()
    assert len(dumped["widgets"]) == 1
    assert dumped["widgets"][0]["refresh_interval"] == 30


@pytest.mark.asyncio
async def test_tuya_summary_widget_endpoint_format():
    """Проверка унифицированного формата ответа эндпоинта виджета Tuya."""
    data = await get_tuya_summary_widget()
    assert "status" in data
    assert "type" in data
    assert "metrics" in data
    assert "actions" in data
    assert "extra" in data
    assert data["type"] == "summary"
    assert isinstance(data["metrics"], list)
    assert len(data["metrics"]) >= 3  # total, online, offline
    metric_ids = [m["id"] for m in data["metrics"]]
    assert "total" in metric_ids
    assert "online" in metric_ids
    assert "offline" in metric_ids


def test_system_modules_widget_registration():
    """Проверка наличия системного виджета system-modules в get_all_widgets()."""
    from backend.core.plugin.registry import get_all_widgets

    widgets = get_all_widgets()
    widget_ids = [w["id"] for w in widgets]
    assert "system-modules" in widget_ids


@pytest.mark.asyncio
async def test_system_modules_widget_endpoint():
    """Проверка работы эндпоинта системного виджета /api/modules/summary_widget."""
    from backend.core.auth import CurrentUser
    from backend.core.plugin.api import get_system_modules_widget

    mock_user = CurrentUser(
        id="admin",
        username="admin",
        full_name="Admin",
        email=None,
        uid="1",
        role_id="admin",
        role_name="Admin",
        permissions=("modules.view",),
    )
    res = await get_system_modules_widget(user=mock_user)
    assert res["status"] == "ok"
    assert res["type"] == "list"
    assert res["title"] == "modulesCount"
    assert len(res["metrics"]) >= 1
    assert len(res["actions"]) >= 1


