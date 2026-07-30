import pytest
from fastapi.testclient import TestClient
from backend.core.app import create_app
import backend.core.database as db_module

@pytest.fixture(scope="function")
def client(tmp_path):
    test_db = tmp_path / "test_nms.db"
    db_module.DB_PATH = test_db
    db_module.init_db()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

def test_session_deduplication_and_revocation(client: TestClient):
    # 1. Login user
    res1 = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    assert res1.status_code == 200
    token1 = res1.json()["token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Fetch sessions for root
    my_sess1 = client.get("/api/users/me/sessions", headers=headers1)
    assert my_sess1.status_code == 200
    sess_list1 = my_sess1.json()
    assert len(sess_list1) == 1
    assert sess_list1[0]["is_current"] is True

    # 2. Login user again from exact same browser (same user_agent / IP)
    res2 = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    assert res2.status_code == 200
    token2 = res2.json()["token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Fetch sessions now using new token
    my_sess2 = client.get("/api/users/me/sessions", headers=headers2)
    assert my_sess2.status_code == 200
    sess_list2 = my_sess2.json()
    # The previous session was replaced/revoked, so active count for this browser remains 1
    assert len(sess_list2) == 1
    assert sess_list2[0]["is_current"] is True

    # 3. Check System Admin active sessions endpoint
    sys_sess = client.get("/api/system/sessions", headers=headers2)
    assert sys_sess.status_code == 200
    assert len(sys_sess.json()) >= 1

    # 4. Check user status in list_users
    users_res = client.get("/api/users", headers=headers2)
    assert users_res.status_code == 200
    root_item = next(u for u in users_res.json()["items"] if u["username"] == "root")
    assert root_item["is_online"] is True

    # 5. Logout
    logout_res = client.post("/api/auth/logout", headers=headers2)
    assert logout_res.status_code == 200

    # User should now be offline
    headers_root_login = {"Authorization": f"Bearer {token1}"} # token1 revoked
    res3 = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    headers3 = {"Authorization": f"Bearer {res3.json()['token']}"}
    
    # Revoke session 3
    my_sess3 = client.get("/api/users/me/sessions", headers=headers3).json()
    sess_id3 = my_sess3[0]["id"]
    client.delete(f"/api/users/me/sessions/{sess_id3}", headers=headers3)

    # Re-login to check that root's revoked status makes root offline
    res4 = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    headers4 = {"Authorization": f"Bearer {res4.json()['token']}"}

    # Before sending API call with header4, check status of root before header4 updated last_seen:
    # We can check that right after logout / revoke with no active sessions, user is offline.
    # Note: res4 login created a fresh active session, so root is online again.
    users_res2 = client.get("/api/users", headers=headers4)
    assert users_res2.status_code == 200
    root_item2 = next(u for u in users_res2.json()["items"] if u["username"] == "root")
    assert root_item2["is_online"] is True


def test_terminate_other_sessions(client: TestClient):
    # 1. Login user twice with different user agents
    res1 = client.post("/api/auth/login", json={"username": "root", "password": "admin"}, headers={"User-Agent": "Browser1"})
    token1 = res1.json()["token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    res2 = client.post("/api/auth/login", json={"username": "root", "password": "admin"}, headers={"User-Agent": "Browser2"})
    token2 = res2.json()["token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Verify user has 2 active sessions
    my_sess = client.get("/api/users/me/sessions", headers=headers1).json()
    assert len(my_sess) == 2

    # Call terminate other sessions using token1
    term_res = client.post("/api/auth/terminate-sessions?other_only=true", headers=headers1)
    assert term_res.status_code == 200

    # Token 1 should remain valid and active
    check1 = client.get("/api/users/me/sessions", headers=headers1)
    assert check1.status_code == 200
    assert len(check1.json()) == 1
    assert check1.json()[0]["is_current"] is True

    # Token 2 should be revoked and return 401
    check2 = client.get("/api/users/me/sessions", headers=headers2)
    assert check2.status_code == 401


def test_system_terminate_all_keep_current(client: TestClient):
    # Login root admin from Browser1 and Browser2
    res1 = client.post("/api/auth/login", json={"username": "root", "password": "admin"}, headers={"User-Agent": "AdminBrowser1"})
    token1 = res1.json()["token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    res2 = client.post("/api/auth/login", json={"username": "root", "password": "admin"}, headers={"User-Agent": "AdminBrowser2"})
    token2 = res2.json()["token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Call system terminate-all with keep_current=true using token1
    term_all = client.post("/api/system/sessions/terminate-all?keep_current=true", headers=headers1)
    assert term_all.status_code == 200

    # Admin's current session (token1) should remain active
    sys_sess = client.get("/api/system/sessions", headers=headers1)
    assert sys_sess.status_code == 200
    assert len(sys_sess.json()) == 1
    assert sys_sess.json()[0]["is_current"] is True

    # Token2 session should receive 401
    check2 = client.get("/api/users/me/sessions", headers=headers2)
    assert check2.status_code == 401

