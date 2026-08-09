"""Тесты подсистемы подписок на события Ядра и Модулей."""

import pytest
from backend.core.database import get_db_connection, init_db
from backend.core.subscriptions import (
    create_subscription,
    delete_subscription,
    get_subscribable_sources,
    get_subscription_by_id,
    get_user_subscriptions,
    match_subscriptions_for_event,
    toggle_subscription,
    update_subscription,
)
from backend.core.exceptions import NotFoundError, ValidationError


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM user_notification_subscriptions;")
    conn.close()


def test_crud_subscriptions():
    user_id = "user_test_01"

    # 1. Создание подписки на Модуль
    sub1 = create_subscription(
        user_id=user_id,
        name="Аварии электропитания",
        source_type="module",
        module_id="power",
        min_severity="warning",
        channels=["in_app", "telegram"],
    )
    assert sub1["user_id"] == user_id
    assert sub1["source_type"] == "module"
    assert sub1["module_id"] == "power"
    assert sub1["min_severity"] == "warning"
    assert "telegram" in sub1["channels"]
    assert sub1["enabled"] is True

    # 2. Создание подписки на Ядро системы
    sub2 = create_subscription(
        user_id=user_id,
        name="Системный аудит",
        source_type="system",
        module_id="system",
        min_severity="info",
        channels=["in_app"],
    )
    assert sub2["source_type"] == "system"

    # 3. Список подписок
    user_subs = get_user_subscriptions(user_id)
    assert len(user_subs) == 2

    # 4. Обновление подписки
    updated = update_subscription(
        sub1["id"],
        user_id,
        min_severity="error",
        enabled=False,
    )
    assert updated["min_severity"] == "error"
    assert updated["enabled"] is False

    # 5. Toggle подписки
    toggled = toggle_subscription(sub1["id"], user_id)
    assert toggled["enabled"] is True

    # 6. Удаление подписки
    deleted = delete_subscription(sub1["id"], user_id)
    assert deleted is True
    assert len(get_user_subscriptions(user_id)) == 1


def test_match_subscriptions_for_event():
    user_a = "user_a"
    user_b = "user_b"

    # Пользователь A подписывается на Модуль 'telemetry' с уровнем warning
    create_subscription(
        user_id=user_a,
        name="Telemetry Warnings",
        source_type="module",
        module_id="telemetry",
        min_severity="warning",
        channels=["in_app", "email"],
    )

    # Пользователь B подписывается на Ядро системы 'system' с уровнем error
    create_subscription(
        user_id=user_b,
        name="Core Errors",
        source_type="system",
        module_id="system",
        min_severity="error",
        channels=["telegram"],
    )

    # 1. Событие от модуля telemetry с критичностью info -> Не должно пройти для A (нужен warning)
    matches_info = match_subscriptions_for_event(source_type="module", module_id="telemetry", severity="info")
    assert user_a not in matches_info

    # 2. Событие от модуля telemetry с критичностью error -> Должно совпасть для A
    matches_error = match_subscriptions_for_event(source_type="module", module_id="telemetry", severity="error")
    assert user_a in matches_error
    assert "email" in matches_error[user_a]

    # 3. Событие от Ядра системы с критичностью error -> Должно совпасть для B
    matches_sys = match_subscriptions_for_event(source_type="system", module_id="system", severity="error")
    assert user_b in matches_sys
    assert "telegram" in matches_sys[user_b]


def test_subscribable_sources():
    sources = get_subscribable_sources()
    assert "system" in sources
    assert sources["system"]["type"] == "system"
    assert "modules" in sources
    assert "severities" in sources
    assert "available_channels" in sources


def test_invalid_subscription_validation():
    with pytest.raises(ValidationError):
        create_subscription(user_id="u1", name="Bad", source_type="invalid_type")

    with pytest.raises(ValidationError):
        create_subscription(user_id="u1", name="Bad", min_severity="invalid_sev")
