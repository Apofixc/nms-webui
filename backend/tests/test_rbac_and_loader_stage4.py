"""Тесты для Этапа 4 (RBAC, Lockout и Загрузчик модулей)."""
from backend.core.app import create_app
from backend.core.auth import CurrentUser, get_current_user, require_permission
from backend.core.database import get_db_connection
from backend.core.rate_limiter import rate_limiter
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


def test_rbac_implied_permissions():
    """Проверка иерархии прав: управляющее право включает право просмотра."""
    app = FastAPI()

    @app.get("/users/view")
    async def view_users(user: CurrentUser = Depends(require_permission("users.view"))):
        return {"ok": True, "user": user.username}

    client = TestClient(app)

    # Пользователь с прямым правом users.view
    user_direct = CurrentUser(
        id="1", username="u1", full_name="U1", email="", uid="U1",
        role_id="r1", role_name="Viewer", permissions=("users.view",)
    )
    app.dependency_overrides[get_current_user] = lambda: user_direct
    resp1 = client.get("/users/view")
    assert resp1.status_code == 200

    # Пользователь с управляющим правом users.manage (имплицирует users.view)
    user_implied = CurrentUser(
        id="2", username="u2", full_name="U2", email="", uid="U2",
        role_id="r2", role_name="Manager", permissions=("users.manage",)
    )
    app.dependency_overrides[get_current_user] = lambda: user_implied
    resp2 = client.get("/users/view")
    assert resp2.status_code == 200

    # Очистка зависимостей
    app.dependency_overrides.clear()


def test_rbac_superuser_all_bypass():
    """Проверка суперпользователя с правом system.all."""
    app = FastAPI()

    @app.get("/system/secret")
    async def secret_endpoint(user: CurrentUser = Depends(require_permission("settings.edit"))):
        return {"secret": True}

    client = TestClient(app)
    superuser = CurrentUser(
        id="1", username="root", full_name="Root", email="", uid="R1",
        role_id="1", role_name="Superuser", permissions=("system.all",)
    )
    app.dependency_overrides[get_current_user] = lambda: superuser

    resp = client.get("/system/secret")
    assert resp.status_code == 200
    app.dependency_overrides.clear()


def test_account_lockout_policy():
    """Проверка блокировки аккаунта после серии неверных входов."""
    rate_limiter.clear()
    app = create_app()
    client = TestClient(app)

    # Запускаем серию неверных попыток входа для подконтрольного тестового пользователя
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM users WHERE username = 'lockout_test_user'")
        conn.execute(
            "INSERT INTO users (id, username, full_name, hashed_password, is_active, role_id) VALUES (?, ?, ?, ?, 1, '1')",
            ("usr-lockout-01", "lockout_test_user", "Lockout Test", "invalid_hash_string"),
        )
        conn.commit()
    finally:
        conn.close()

    # Делаем 5 неверных попыток входа (очищая rate_limiter перед каждой, чтобы проверять именно lockout аккаунта)
    for _ in range(5):
        rate_limiter.clear()
        client.post("/api/auth/login", json={"username": "lockout_test_user", "password": "wrong_pass"})

    # 6-я попытка должна вернуть ошибку блокировки аккаунта (429)
    rate_limiter.clear()
    resp = client.post("/api/auth/login", json={"username": "lockout_test_user", "password": "wrong_pass"})
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] in ("ACCOUNT_LOCKED", "ACCOUNT_TEMPORARILY_LOCKED", "ACCOUNT_LOCKED_DURATION")
