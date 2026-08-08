"""Тесты для Этапа 6 и 7 (Metrics, Health, Request-ID, Backups, API v1)."""
from backend.core.app import create_app
from backend.core.backup import create_database_backup
from fastapi.testclient import TestClient


def test_request_id_and_security_headers():
    """Проверка генерации X-Request-ID и отдачи версионированного корня."""
    app = create_app()
    client = TestClient(app)

    resp = client.get("/")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    assert resp.headers["X-Content-Type-Options"] == "nosniff"


def test_prometheus_metrics_endpoint():
    """Проверка отдачи эндпоинта /metrics в формате Prometheus."""
    app = create_app()
    client = TestClient(app)

    # Выполняем тестовый запрос для генерации метрик
    client.get("/health/live")

    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "nms_http_requests_total" in resp.text


def test_health_probes():
    """Проверка liveness и readiness проб."""
    app = create_app()
    client = TestClient(app)

    res_live = client.get("/health/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "alive"

    res_ready = client.get("/health/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ready"


def test_api_v1_versioned_routes():
    """Проверка доступности рутов под префиксом /api/v1."""
    app = create_app()
    client = TestClient(app)

    resp = client.get("/api/v1/health")
    assert resp.status_code == 200


def test_database_backup(tmp_path, monkeypatch):
    """Проверка создания атомарного бэкапа SQLite."""
    import sqlite3
    fake_data = tmp_path / "data"
    fake_db = fake_data / "nms.db"
    fake_data.mkdir()

    conn = sqlite3.connect(fake_db)
    conn.execute("CREATE TABLE test_tbl (id INT);")
    conn.commit()
    conn.close()

    monkeypatch.setattr("backend.core.backup.DB_PATH", fake_db)
    monkeypatch.setattr("backend.core.backup.DATA_DIR", fake_data)
    monkeypatch.setattr("backend.core.backup.BACKUPS_DIR", fake_data / "backups")

    backup_file = create_database_backup(retention_copies=3)
    assert backup_file.exists()
    assert "nms_backup_" in backup_file.name
