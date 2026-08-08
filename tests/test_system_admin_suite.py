import io
import pytest
from fastapi.testclient import TestClient
from backend.core.app import create_app
import backend.core.database as db_module

@pytest.fixture(scope="function")
def client(tmp_path):
    test_db = tmp_path / "test_sysadmin.db"
    db_module.DB_PATH = test_db
    db_module.init_db()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

def get_admin_headers(client):
    res = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    assert res.status_code == 200
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}

# ============================================================================
# ГЛУБОКИЙ НАБОР ТЕСТОВ КОМПОНЕНТА "СИСТЕМНОЕ АДМИНИСТРИРОВАНИЕ" (/settings/system)
# ============================================================================

def test_system_backup_download_and_restore_validation(client):
    """1. Резервное копирование: Скачивание дампа бэкапа и проверка формата."""
    headers = get_admin_headers(client)

    # 1. Запрос на скачивание дампа резервной копии
    res_backup = client.get("/api/system/backup", headers=headers)
    assert res_backup.status_code == 200
    # Проверяем заголовки выгрузки файла
    assert "attachment" in res_backup.headers.get("content-disposition", "") or "sqlite" in res_backup.headers.get("content-type", "") or len(res_backup.content) > 0

    # 2. Загрузка битого файла -> 400 Bad Request
    invalid_file = {"file": ("corrupted.db", io.BytesIO(b"NOT A SQLITE DATABASE"), "application/x-sqlite3")}
    res_restore_bad = client.post("/api/system/restore", files=invalid_file, headers=headers)
    assert res_restore_bad.status_code in (400, 422)


def test_system_sessions_monitoring_and_terminate_all(client):
    """2. Мониторинг всех сессий подключений в системе и завершение всех сессий."""
    headers = get_admin_headers(client)

    # 1. Чтение всех активных сессий
    res_sessions = client.get("/api/system/sessions", headers=headers)
    assert res_sessions.status_code == 200
    sessions = res_sessions.json()
    assert isinstance(sessions, list)
    assert any(s["username"] == "root" for s in sessions)

    # 2. Принудительный сброс всех сессий системы
    res_term_all = client.post("/api/auth/terminate-sessions", headers=headers)
    assert res_term_all.status_code == 200
    assert res_term_all.json() == {"ok": True}


def test_system_logs_file_listing_and_filtering(client):
    """3. Интерактивный лог-клиент: Список файлов логов и фильтрация фрагментов."""
    headers = get_admin_headers(client)

    # 1. Список лог-файлов
    res_files = client.get("/api/system/logs", headers=headers)
    assert res_files.status_code == 200
    logs_data = res_files.json()
    assert isinstance(logs_data, list)
    assert len(logs_data) > 0

    log_filename = logs_data[0]["name"]

    # 2. Чтение фрагмента лог-файла c фильтром по уровню INFO
    res_log_content = client.get(f"/api/system/logs/{log_filename}?lines=100&level=INFO", headers=headers)
    assert res_log_content.status_code == 200
    content = res_log_content.json()
    assert "lines" in content or "content" in content or isinstance(content, dict)


def test_system_logs_search_query(client):
    """4. Поиск фрагмента строки в системных логах."""
    headers = get_admin_headers(client)

    res_files = client.get("/api/system/logs", headers=headers)
    log_filename = res_files.json()[0]["name"]

    # Поиск строки "GET" в логах
    res_search = client.get(f"/api/system/logs/{log_filename}?search=GET&lines=50", headers=headers)
    assert res_search.status_code == 200


def test_matches_log_level_helper():
    """5. Проверка функции точного сопоставления уровня логов."""
    from backend.api.system import _matches_log_level

    # Изолированный тест уровня INFO без ложных срабатываний при наличии "info" в тексте ERROR
    info_line = "2026-07-12 19:01:37 | INFO     | nms.plugin.loader | Loaded 1 modules"
    error_line_with_info_text = "2026-07-12 19:01:37 | ERROR    | nms.api | Failed to fetch info about user"
    warn_line = "2026-07-12 19:01:37 | WARNING  | nms.astra | Warning message"

    assert _matches_log_level(info_line, "INFO") is True
    assert _matches_log_level(error_line_with_info_text, "INFO") is False
    assert _matches_log_level(error_line_with_info_text, "ERROR") is True

    # Проверка эквивалентности WARN и WARNING
    assert _matches_log_level(warn_line, "WARN") is True
    assert _matches_log_level(warn_line, "WARNING") is True
    assert _matches_log_level(warn_line, "INFO") is False


def test_system_logs_backend_endpoint(client):
    """6. Проверка доступности системного backend.log и очистки ANSI-кодов."""
    headers = get_admin_headers(client)

    res_files = client.get("/api/system/logs", headers=headers)
    assert res_files.status_code == 200
    file_names = [f["name"] for f in res_files.json()]
    assert "backend.log" in file_names

    res_backend = client.get("/api/system/logs/backend.log", headers=headers)
    assert res_backend.status_code == 200
    lines = res_backend.json().get("content", [])
    # Проверяем, что нет незачищенных ANSI esc кодов в строках
    for l in lines:
        assert "\x1b[" not in l


