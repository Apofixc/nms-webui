"""CLI Disaster Recovery script: resets default root account.

Usage:
    python3 -m backend.scripts.reset_root
    OR
    ./run_webui.sh reset-root
"""
from __future__ import annotations

import sys
from backend.core.database import get_db_connection, hash_password, init_db
from backend.core.audit import log_audit_event


def reset_root_account() -> bool:
    """Восстановление доступности и сброс пароля пользователя root в 'admin'."""
    init_db()
    conn = get_db_connection()
    try:
        pass_hash = hash_password("admin")
        root_user = conn.execute("SELECT id FROM users WHERE username = 'root' OR username = 'admin'").fetchone()

        if root_user:
            conn.execute(
                """
                UPDATE users
                SET username = 'root',
                    full_name = 'Главный администратор (Root)',
                    email = 'root@nms.local',
                    uid = 'ROOT-001',
                    hashed_password = ?,
                    is_active = 1,
                    role_id = '1'
                WHERE id = ?
                """,
                (pass_hash, root_user["id"]),
            )
            root_id = root_user["id"]
        else:
            root_id = "usr-root-01"
            conn.execute(
                """
                INSERT INTO users (id, username, full_name, email, uid, hashed_password, is_active, role_id)
                VALUES (?, 'root', 'Главный администратор (Root)', 'root@nms.local', 'ROOT-001', ?, 1, '1')
                """,
                (root_id, pass_hash),
            )

        conn.commit()

        log_audit_event(
            user_id=root_id,
            username="root",
            action="system.disaster_recovery",
            resource="system",
            details="CLI Disaster Recovery: Аккаунт root активирован, пароль сброшен на 'admin'",
            ip_address="console",
        )

        print("\n==========================================================")
        print(" [NMS RECOVERY] Аккаунт root успешно реанимирован!")
        print("   - Имя пользователя: root")
        print("   - Пароль по умолчанию: admin")
        print("   - Статус: Активен (is_active = 1)")
        print("   - Права: Superuser (role_id = 1)")
        print("==========================================================\n")
        return True
    except Exception as exc:
        print(f"FAILED to reset root account: {exc}", file=sys.stderr)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    reset_root_account()
