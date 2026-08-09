import asyncio
import hashlib
import json
import logging
import socket
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

import httpx

from backend.core.database import get_db_connection

_log = logging.getLogger("nms.alerting")

SEVERITY_LEVELS = {
    "resolved": 0,
    "info": 1,
    "success": 2,
    "warning": 3,
    "error": 4,
}

DEDUPLICATION_WINDOW_SEC = 60
FLAPPING_THRESHOLD_COUNT = 4
FLAPPING_WINDOW_SEC = 60
CIRCUIT_BREAKER_MAX_FAILURES = 3
CIRCUIT_BREAKER_COOLDOWN_SEC = 180  # 3 минуты


# ── Персистентные кэши и предохранители (SQLite-backed) ───────────

def is_flapping(fingerprint: str, conn=None) -> bool:
    """Проверить, не является ли алерт дребезжащим (flapping), через персистентную таблицу."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        now_ts = datetime.now()
        now_str = now_ts.strftime("%Y-%m-%d %H:%M:%S")
        cutoff = (now_ts - timedelta(seconds=FLAPPING_WINDOW_SEC)).strftime("%Y-%m-%d %H:%M:%S")

        with conn:
            conn.execute(
                "INSERT INTO alert_flapping_cache (fingerprint, triggered_at) VALUES (?, ?)",
                (fingerprint, now_str),
            )
            conn.execute("DELETE FROM alert_flapping_cache WHERE triggered_at < ?", (cutoff,))
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM alert_flapping_cache WHERE fingerprint = ? AND triggered_at >= ?",
                (fingerprint, cutoff),
            ).fetchone()
            cnt = row["cnt"] if row else 1
        return cnt >= FLAPPING_THRESHOLD_COUNT
    except Exception as exc:
        _log.warning("Error checking flapping: %s", exc)
        return False
    finally:
        if close_conn:
            conn.close()


def is_channel_in_cooldown(channel_id: str, conn=None) -> bool:
    """Проверить, находится ли канал в режиме Circuit Breaker (cooldown)."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        row = conn.execute(
            "SELECT consecutive_failures, cooldown_until FROM alert_circuit_breaker WHERE channel_id = ?",
            (channel_id,),
        ).fetchone()

        if not row:
            return False

        failures = row["consecutive_failures"]
        cooldown_until_str = row["cooldown_until"]

        if failures >= CIRCUIT_BREAKER_MAX_FAILURES and cooldown_until_str:
            try:
                cooldown_dt = datetime.strptime(cooldown_until_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
                if datetime.now() < cooldown_dt:
                    return True
                else:
                    with conn:
                        conn.execute("DELETE FROM alert_circuit_breaker WHERE channel_id = ?", (channel_id,))
                    return False
            except Exception:
                pass
        return False
    except Exception as exc:
        _log.warning("Error checking circuit breaker: %s", exc)
        return False
    finally:
        if close_conn:
            conn.close()


def record_channel_result(channel_id: str, success: bool, conn=None):
    """Зафиксировать результат отправки в канал для Circuit Breaker в БД."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        with conn:
            if success:
                conn.execute("DELETE FROM alert_circuit_breaker WHERE channel_id = ?", (channel_id,))
            else:
                row = conn.execute(
                    "SELECT consecutive_failures FROM alert_circuit_breaker WHERE channel_id = ?",
                    (channel_id,),
                ).fetchone()
                failures = (row["consecutive_failures"] if row else 0) + 1

                cooldown_until = None
                if failures >= CIRCUIT_BREAKER_MAX_FAILURES:
                    cooldown_dt = datetime.now() + timedelta(seconds=CIRCUIT_BREAKER_COOLDOWN_SEC)
                    cooldown_until = cooldown_dt.strftime("%Y-%m-%d %H:%M:%S")

                conn.execute(
                    """
                    INSERT INTO alert_circuit_breaker (channel_id, consecutive_failures, cooldown_until, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(channel_id) DO UPDATE SET
                        consecutive_failures = excluded.consecutive_failures,
                        cooldown_until = excluded.cooldown_until,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (channel_id, failures, cooldown_until),
                )
    except Exception as exc:
        _log.warning("Error updating circuit breaker: %s", exc)
    finally:
        if close_conn:
            conn.close()


def calculate_fingerprint(title: str, category: str, severity: str) -> str:
    """Вычислить MD5-хэш сообщения для дедупликации."""
    raw = f"{category.strip().lower()}:{severity.strip().lower()}:{title.strip().lower()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def should_deduplicate(fingerprint: str, window_sec: int = DEDUPLICATION_WINDOW_SEC, conn=None) -> Tuple[bool, int]:
    """Проверить, попадает ли алерт в окно дедупликации, через персистентную таблицу."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        now_dt = datetime.now()
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

        row = conn.execute(
            "SELECT first_seen, last_seen, count FROM alert_dedup_cache WHERE fingerprint = ?",
            (fingerprint,),
        ).fetchone()

        if row:
            last_seen_str = str(row["last_seen"])
            try:
                last_seen_dt = datetime.strptime(last_seen_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
                elapsed = (now_dt - last_seen_dt).total_seconds()
            except Exception:
                elapsed = window_sec + 1

            if elapsed < window_sec:
                new_count = row["count"] + 1
                with conn:
                    conn.execute(
                        "UPDATE alert_dedup_cache SET last_seen = ?, count = ? WHERE fingerprint = ?",
                        (now_str, new_count, fingerprint),
                    )
                return True, new_count

        with conn:
            conn.execute(
                """
                INSERT INTO alert_dedup_cache (fingerprint, first_seen, last_seen, count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    first_seen = excluded.first_seen,
                    last_seen = excluded.last_seen,
                    count = 1
                """,
                (fingerprint, now_str, now_str),
            )
        return False, 1
    except Exception as exc:
        _log.warning("Error checking deduplication: %s", exc)
        return False, 1
    finally:
        if close_conn:
            conn.close()


def reset_dedup_cache(conn=None):
    """Очистить кэш дедупликации и предохранителей в БД (для тестов/сброса)."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        with conn:
            conn.execute("DELETE FROM alert_dedup_cache;")
            conn.execute("DELETE FROM alert_flapping_cache;")
            conn.execute("DELETE FROM alert_circuit_breaker;")
    except Exception as exc:
        _log.warning("Error resetting dedup cache: %s", exc)
    finally:
        if close_conn:
            conn.close()


def prune_alert_caches(dedup_window: int = DEDUPLICATION_WINDOW_SEC, flapping_window: int = FLAPPING_WINDOW_SEC, conn=None):
    """Очистить устаревшие записи из таблиц дедупликации и дребезга."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        now_dt = datetime.now()
        dedup_cutoff = (now_dt - timedelta(seconds=dedup_window)).strftime("%Y-%m-%d %H:%M:%S")
        flapping_cutoff = (now_dt - timedelta(seconds=flapping_window)).strftime("%Y-%m-%d %H:%M:%S")

        with conn:
            conn.execute("DELETE FROM alert_dedup_cache WHERE last_seen < ?", (dedup_cutoff,))
            conn.execute("DELETE FROM alert_flapping_cache WHERE triggered_at < ?", (flapping_cutoff,))
    except Exception as exc:
        _log.warning("Error pruning alert caches: %s", exc)
    finally:
        if close_conn:
            conn.close()


def is_in_quiet_hours(category: str, severity: str = "info", conn=None) -> bool:
    """Проверить, попадает ли алерт в активный интервал тишины (Quiet Hours)."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        rows = conn.execute(
            "SELECT name, days_of_week, start_time, end_time, min_severity FROM quiet_hours WHERE enabled = 1"
        ).fetchall()
        if not rows:
            return False

        now = datetime.now()
        curr_weekday = str(now.isoweekday())
        curr_time_str = now.strftime("%H:%M")
        curr_lvl = SEVERITY_LEVELS.get(severity.lower(), 1)

        for row in rows:
            min_lvl = SEVERITY_LEVELS.get((row["min_severity"] or "info").lower(), 1)
            if curr_lvl > min_lvl:
                continue
            days = [d.strip() for d in (row["days_of_week"] or "*").split(",") if d.strip()]
            if "*" not in days and curr_weekday not in days:
                continue
            start_t = str(row["start_time"])
            end_t = str(row["end_time"])
            if start_t <= end_t:
                if start_t <= curr_time_str <= end_t:
                    return True
            else:
                if curr_time_str >= start_t or curr_time_str <= end_t:
                    return True
        return False
    except Exception as exc:
        _log.warning("Error checking quiet hours: %s", exc)
        return False
    finally:
        if close_conn:
            conn.close()


def is_in_maintenance(category: str, conn=None) -> bool:
    """Проверить, находится ли категория в активном окне технического обслуживания."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        rows = conn.execute(
            "SELECT target_category, starts_at, ends_at FROM maintenance_windows WHERE enabled = 1"
        ).fetchall()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for row in rows:
            tgt = (row["target_category"] or "*").strip().lower()
            starts = str(row["starts_at"])
            ends = str(row["ends_at"])
            if starts <= now_str <= ends:
                if tgt == "*" or tgt == category.strip().lower():
                    return True
        return False
    except Exception as exc:
        _log.warning("Error checking maintenance windows: %s", exc)
        return False
    finally:
        if close_conn:
            conn.close()


def _format_message_with_template(config: dict, alert: dict) -> dict:
    """Если в конфиге канала задан шаблон `template`, отформатировать сообщение с Rich Context."""
    template = config.get("template")
    if not template or not isinstance(template, str):
        return alert

    formatted = dict(alert)
    icon = "🔴" if alert.get("severity") == "error" else ("🟡" if alert.get("severity") == "warning" else "ℹ️")
    context = {
        "title": alert.get("title", ""),
        "message": alert.get("message", ""),
        "severity": str(alert.get("severity", "info")),
        "category": str(alert.get("category", "system")),
        "icon": icon,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "device_ip": str(alert.get("device_ip", alert.get("ip", "—"))),
        "location": str(alert.get("location", "N/A")),
        "graph_link": str(alert.get("graph_link", alert.get("link", "#"))),
    }

    msg = template
    for k, v in context.items():
        msg = msg.replace(f"{{{k}}}", str(v)).replace(f"{{ {k} }}", str(v))

    formatted["message"] = msg
    return formatted


def _should_send(min_type: str, notif_type: str, categories: str, notif_cat: str) -> bool:
    """Проверить, подходит ли алерт по уровню критичности и категории."""
    min_lvl = SEVERITY_LEVELS.get(min_type.lower(), 1)
    current_lvl = SEVERITY_LEVELS.get(notif_type.lower(), 1)
    if current_lvl < min_lvl:
        return False

    if categories and categories.strip() != "*":
        allowed = [c.strip().lower() for c in categories.split(",") if c.strip()]
        if notif_cat.lower() not in allowed:
            return False

    return True


# ── Асинхронные и Синхронные HTTP Провайдеры ───────────────────────────

async def _make_http_post_async(
    url: str,
    json_data: dict = None,
    headers: dict = None,
    timeout: float = 8.0,
    max_retries: int = 3,
) -> Tuple[bool, int]:
    """Неблокирующий асинхронный HTTP POST запрос через httpx.AsyncClient."""
    backoff = [0.1, 0.3, 0.5]
    retries_done = 0
    req_headers = {"Content-Type": "application/json", "User-Agent": "NMS-WebUI-AlertEngine/1.0"}
    if headers:
        req_headers.update(headers)

    async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
        for attempt in range(max_retries):
            retries_done = attempt
            try:
                resp = await client.post(url, json=json_data, headers=req_headers)
                if 200 <= resp.status_code < 300:
                    return True, retries_done
                if resp.status_code == 429 and attempt < max_retries - 1:
                    retry_after = resp.headers.get("Retry-After")
                    sleep_time = float(retry_after) if retry_after else backoff[min(attempt, len(backoff) - 1)]
                    await asyncio.sleep(sleep_time)
                    continue
            except Exception as exc:
                _log.warning("Async HTTP POST attempt %d to %s failed: %s", attempt + 1, url, exc)
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff[min(attempt, len(backoff) - 1)])

    return False, retries_done


def _make_http_post(url: str, json_data: dict = None, headers: dict = None, timeout: float = 8.0, max_retries: int = 3) -> Tuple[bool, int]:
    """Синхронная обертка для отправки HTTP POST запроса."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Если находимся внутри event loop, выполняем синхронный urllib во избежание блокировки корутины
        backoff = [0.1, 0.3, 0.5]
        data_bytes = json.dumps(json_data).encode("utf-8") if json_data else b""
        retries_done = 0
        for attempt in range(max_retries):
            retries_done = attempt
            try:
                req = urllib.request.Request(url, data=data_bytes, method="POST")
                req.add_header("Content-Type", "application/json")
                req.add_header("User-Agent", "NMS-WebUI-AlertEngine/1.0")
                if headers:
                    for k, v in headers.items():
                        req.add_header(k, v)

                with urllib.request.urlopen(req, timeout=timeout) as response:
                    if 200 <= response.status < 300:
                        return True, retries_done
                    if response.status == 429 and attempt < max_retries - 1:
                        retry_after = response.headers.get("Retry-After")
                        sleep_time = float(retry_after) if retry_after else backoff[min(attempt, len(backoff) - 1)]
                        time.sleep(sleep_time)
                        continue
            except Exception as exc:
                _log.warning("HTTP POST attempt %d to %s failed: %s", attempt + 1, url, exc)
                if attempt < max_retries - 1:
                    time.sleep(backoff[min(attempt, len(backoff) - 1)])
        return False, retries_done
    else:
        return asyncio.run(_make_http_post_async(url, json_data, headers, timeout, max_retries))


async def send_telegram_async(config: dict, alert: dict) -> Tuple[bool, int]:
    """Асинхронная отправка алерта через Telegram Bot API."""
    bot_token = config.get("bot_token")
    chat_id = config.get("chat_id")
    if not bot_token or not chat_id:
        return False, 0

    icon = "🔴" if alert.get("severity") == "error" else ("🟡" if alert.get("severity") == "warning" else "ℹ️")
    text = (
        f"{icon} <b>NMS Alert: {alert.get('title', '')}</b>\n\n"
        f"{alert.get('message', '')}\n\n"
        f"<b>Тип:</b> {alert.get('severity', 'info').upper()} | <b>Категория:</b> {alert.get('category', 'system')}"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    return await _make_http_post_async(url, payload)


def send_telegram(config: dict, alert: dict) -> Union[bool, Tuple[bool, int]]:
    """Синхронная отправка алерта через Telegram Bot API."""
    bot_token = config.get("bot_token")
    chat_id = config.get("chat_id")
    if not bot_token or not chat_id:
        return False, 0

    icon = "🔴" if alert.get("severity") == "error" else ("🟡" if alert.get("severity") == "warning" else "ℹ️")
    text = (
        f"{icon} <b>NMS Alert: {alert.get('title', '')}</b>\n\n"
        f"{alert.get('message', '')}\n\n"
        f"<b>Тип:</b> {alert.get('severity', 'info').upper()} | <b>Категория:</b> {alert.get('category', 'system')}"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    return _make_http_post(url, payload)


async def send_discord_async(config: dict, alert: dict) -> Tuple[bool, int]:
    """Асинхронная отправка Rich Embed карточки в Discord Webhook."""
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        return False, 0

    severity = alert.get("severity", "info")
    color = 15158332 if severity == "error" else (15844367 if severity == "warning" else 3447003)
    icon = "🔴" if severity == "error" else ("🟡" if severity == "warning" else "ℹ️")

    payload = {
        "username": "NMS AlertBot",
        "embeds": [
            {
                "title": f"{icon} {alert.get('title', '')}",
                "description": alert.get("message", ""),
                "color": color,
                "fields": [
                    {"name": "Категория", "value": alert.get("category", "system"), "inline": True},
                    {"name": "Критичность", "value": severity.upper(), "inline": True},
                ],
                "footer": {"text": "NMS WebUI Monitoring"},
            }
        ],
    }
    return await _make_http_post_async(webhook_url, payload)


def send_discord(config: dict, alert: dict) -> Union[bool, Tuple[bool, int]]:
    """Синхронная отправка Rich Embed карточки в Discord Webhook."""
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        return False, 0

    severity = alert.get("severity", "info")
    color = 15158332 if severity == "error" else (15844367 if severity == "warning" else 3447003)
    icon = "🔴" if severity == "error" else ("🟡" if severity == "warning" else "ℹ️")

    payload = {
        "username": "NMS AlertBot",
        "embeds": [
            {
                "title": f"{icon} {alert.get('title', '')}",
                "description": alert.get("message", ""),
                "color": color,
                "fields": [
                    {"name": "Категория", "value": alert.get("category", "system"), "inline": True},
                    {"name": "Критичность", "value": severity.upper(), "inline": True},
                ],
                "footer": {"text": "NMS WebUI Monitoring"},
            }
        ],
    }
    return _make_http_post(webhook_url, payload)


async def send_viber_async(config: dict, alert: dict) -> Tuple[bool, int]:
    """Асинхронная отправка сообщения через Viber Bot REST API."""
    auth_token = config.get("auth_token")
    receiver = config.get("receiver_id")
    if not auth_token or not receiver:
        return False, 0

    icon = "🔴" if alert.get("severity") == "error" else ("🟡" if alert.get("severity") == "warning" else "ℹ️")
    text = f"{icon} NMS Alert: {alert.get('title')}\n{alert.get('message')}\nCategory: {alert.get('category')}"

    url = "https://chatapi.viber.com/pa/send_message"
    headers = {"X-Viber-Auth-Token": auth_token}
    payload = {
        "receiver": receiver,
        "min_api_version": 1,
        "sender": {"name": "NMS Monitoring"},
        "type": "text",
        "text": text,
    }
    return await _make_http_post_async(url, payload, headers=headers)


def send_viber(config: dict, alert: dict) -> Union[bool, Tuple[bool, int]]:
    """Синхронная отправка сообщения через Viber Bot REST API."""
    auth_token = config.get("auth_token")
    receiver = config.get("receiver_id")
    if not auth_token or not receiver:
        return False, 0

    icon = "🔴" if alert.get("severity") == "error" else ("🟡" if alert.get("severity") == "warning" else "ℹ️")
    text = f"{icon} NMS Alert: {alert.get('title')}\n{alert.get('message')}\nCategory: {alert.get('category')}"

    url = "https://chatapi.viber.com/pa/send_message"
    headers = {"X-Viber-Auth-Token": auth_token}
    payload = {
        "receiver": receiver,
        "min_api_version": 1,
        "sender": {"name": "NMS Monitoring"},
        "type": "text",
        "text": text,
    }
    return _make_http_post(url, payload, headers=headers)


def send_email(config: dict, alert: dict) -> bool:
    """Отправка email сообщения через SMTP."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_host = config.get("smtp_host")
    smtp_port = int(config.get("smtp_port", 25))
    username = config.get("username")
    password = config.get("password")
    from_email = config.get("from_email", username or "nms@local")
    to_emails = config.get("to_emails", [])

    if isinstance(to_emails, str):
        to_emails = [e.strip() for e in to_emails.split(",") if e.strip()]

    if not smtp_host or not to_emails:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[NMS {alert.get('severity', 'info').upper()}] {alert.get('title')}"
        msg["From"] = from_email
        msg["To"] = ", ".join(to_emails)

        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: {'#e11d48' if alert.get('severity')=='error' else '#d97706'};">
              {alert.get('title')}
            </h2>
            <p>{alert.get('message')}</p>
            <hr />
            <p style="font-size: 12px; color: #666;">
              Категория: {alert.get('category')}
            </p>
          </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if config.get("use_tls", True):
                try:
                    server.starttls()
                except Exception:
                    pass
            if username and password:
                server.login(username, password)
            server.sendmail(from_email, to_emails, msg.as_string())
        return True
    except Exception as exc:
        _log.warning("Failed to send SMTP email: %s", exc)
        return False


async def send_webhook_async(config: dict, alert: dict) -> Tuple[bool, int]:
    """Асинхронная отправка произвольного HTTP Webhook (JSON Payload)."""
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        return False, 0

    headers = {}
    if config.get("secret_token"):
        headers["X-NMS-Secret"] = config.get("secret_token")

    payload = {
        "event": "alert_triggered",
        "alert": alert,
    }
    return await _make_http_post_async(webhook_url, payload, headers=headers)


def send_webhook(config: dict, alert: dict) -> Union[bool, Tuple[bool, int]]:
    """Синхронная отправка произвольного HTTP Webhook (JSON Payload)."""
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        return False, 0

    headers = {}
    if config.get("secret_token"):
        headers["X-NMS-Secret"] = config.get("secret_token")

    payload = {
        "event": "alert_triggered",
        "alert": alert,
    }
    return _make_http_post(webhook_url, payload, headers=headers)


def send_syslog(config: dict, alert: dict) -> bool:
    """Отправка события по UDP/TCP в Syslog/SIEM сервер (RFC 5424)."""
    syslog_host = config.get("syslog_host")
    syslog_port = int(config.get("syslog_port", 514))
    protocol = config.get("protocol", "udp").lower()

    if not syslog_host:
        return False

    try:
        msg_str = f"<134>1 NMSWebUI {alert.get('category')} - - - {alert.get('severity').upper()}: {alert.get('title')} - {alert.get('message')}\n"
        data = msg_str.encode("utf-8")

        if protocol == "tcp":
            with socket.create_connection((syslog_host, syslog_port), timeout=5) as sock:
                sock.sendall(data)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.sendto(data, (syslog_host, syslog_port))
            sock.close()
        return True
    except Exception as exc:
        _log.warning("Syslog send to %s:%d failed: %s", syslog_host, syslog_port, exc)
        return False


PROVIDERS = {
    "telegram": send_telegram,
    "discord": send_discord,
    "viber": send_viber,
    "email": send_email,
    "webhook": send_webhook,
    "syslog": send_syslog,
}

ASYNC_PROVIDERS = {
    "telegram": send_telegram_async,
    "discord": send_discord_async,
    "viber": send_viber_async,
    "webhook": send_webhook_async,
}


# ── Воркер гарантированной очереди отправок (Transactional Outbox) ───

async def process_alert_outbox_async(batch_size: int = 20) -> int:
    """Извлечь задачи со статусом pending/retry из alert_outbox и параллельно отправить их."""
    conn = get_db_connection()
    processed_count = 0
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = conn.execute(
            """
            SELECT id, channel_id, channel_type, title, message, severity, category, config_json, attempts, max_attempts
            FROM alert_outbox
            WHERE status IN ('pending', 'failed') 
              AND (next_retry_at IS NULL OR next_retry_at <= ?)
              AND attempts < max_attempts
            ORDER BY id ASC
            LIMIT ?
            """,
            (now_str, batch_size),
        ).fetchall()

        if not rows:
            return 0

        # Переводим статус в 'processing'
        ids = [r["id"] for r in rows]
        placeholders = ",".join(["?"] * len(ids))
        with conn:
            conn.execute(f"UPDATE alert_outbox SET status = 'processing' WHERE id IN ({placeholders})", ids)

        async def _dispatch_one(row):
            c_type = row["channel_type"].lower()
            c_id = row["channel_id"]
            try:
                cfg = json.loads(row["config_json"]) if row["config_json"] else {}
            except Exception:
                cfg = {}

            alert_payload = _format_message_with_template(cfg, {
                "title": row["title"],
                "message": row["message"],
                "severity": row["severity"],
                "category": row["category"],
            })

            # Проверка Circuit Breaker для канала
            if is_channel_in_cooldown(c_id, conn=conn):
                return row["id"], c_id, c_type, False, "Suppressed by Circuit Breaker (Channel Cooldown)", 0, True

            async_prov = ASYNC_PROVIDERS.get(c_type)
            sync_prov = PROVIDERS.get(c_type)
            success = False
            err_msg = None
            retries_done = 0

            try:
                if async_prov:
                    res = await async_prov(cfg, alert_payload)
                elif sync_prov:
                    res = await asyncio.to_thread(sync_prov, cfg, alert_payload)
                else:
                    res = False
                    err_msg = f"Unknown provider type: {c_type}"

                if isinstance(res, tuple):
                    success, retries_done = res
                else:
                    success = bool(res)
                if not success and not err_msg:
                    err_msg = "Provider failed to send alert"
            except Exception as exc:
                success = False
                err_msg = str(exc)

            record_channel_result(c_id, success, conn=conn)
            return row["id"], c_id, c_type, success, err_msg, retries_done, False

        results = await asyncio.gather(*[_dispatch_one(r) for r in rows], return_exceptions=True)

        with conn:
            for r, row in zip(results, rows):
                if isinstance(r, Exception):
                    err_str = str(r)
                    attempts = row["attempts"] + 1
                    backoff_sec = min(300, 10 * (2 ** (attempts - 1)))
                    next_retry = (datetime.now() + timedelta(seconds=backoff_sec)).strftime("%Y-%m-%d %H:%M:%S")
                    status = "failed" if attempts >= row["max_attempts"] else "pending"
                    conn.execute(
                        "UPDATE alert_outbox SET status = ?, attempts = ?, next_retry_at = ?, last_error = ? WHERE id = ?",
                        (status, attempts, next_retry, err_str, row["id"]),
                    )
                    continue

                outbox_id, c_id, c_type, success, err_msg, retries_done, is_cb_suppressed = r
                attempts = row["attempts"] + 1

                if is_cb_suppressed:
                    conn.execute("UPDATE alert_outbox SET status = 'failed', last_error = ? WHERE id = ?", (err_msg, outbox_id))
                    conn.execute(
                        """
                        INSERT INTO alert_log (channel_id, channel_type, title, message, severity, category, success, error_message, retry_count, suppressed)
                        VALUES (?, ?, ?, ?, ?, ?, 0, ?, 0, 1)
                        """,
                        (c_id, c_type, row["title"], row["message"], row["severity"], row["category"], err_msg),
                    )
                elif success:
                    conn.execute("UPDATE alert_outbox SET status = 'sent', attempts = ?, last_error = NULL WHERE id = ?", (attempts, outbox_id))
                    conn.execute(
                        """
                        INSERT INTO alert_log (channel_id, channel_type, title, message, severity, category, success, error_message, retry_count, suppressed)
                        VALUES (?, ?, ?, ?, ?, ?, 1, NULL, ?, 0)
                        """,
                        (c_id, c_type, row["title"], row["message"], row["severity"], row["category"], retries_done),
                    )
                    processed_count += 1
                else:
                    backoff_sec = min(300, 10 * (2 ** (attempts - 1)))
                    next_retry = (datetime.now() + timedelta(seconds=backoff_sec)).strftime("%Y-%m-%d %H:%M:%S")
                    status = "failed" if attempts >= row["max_attempts"] else "pending"
                    conn.execute(
                        "UPDATE alert_outbox SET status = ?, attempts = ?, next_retry_at = ?, last_error = ? WHERE id = ?",
                        (status, attempts, next_retry, err_msg, outbox_id),
                    )
                    if status == "failed":
                        conn.execute(
                            """
                            INSERT INTO alert_log (channel_id, channel_type, title, message, severity, category, success, error_message, retry_count, suppressed)
                            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, 0)
                            """,
                            (c_id, c_type, row["title"], row["message"], row["severity"], row["category"], err_msg, retries_done),
                        )
    except Exception as exc:
        _log.error("Error processing alert outbox: %s", exc)
    finally:
        conn.close()

    return processed_count


def process_alert_outbox(batch_size: int = 20) -> int:
    """Синхронная обертка для обработки очереди alert_outbox."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Если находимся внутри циклического контекста, создаем задачу в фоне
        task = loop.create_task(process_alert_outbox_async(batch_size))
        return 0
    else:
        return asyncio.run(process_alert_outbox_async(batch_size))


_outbox_loop_task: Optional[asyncio.Task] = None


async def start_outbox_loop(poll_interval: float = 3.0):
    """Запустить фоновую корутину регулярного вызова process_alert_outbox_async."""
    _log.info("Starting Alert Outbox Worker loop (interval: %.1fs)...", poll_interval)
    while True:
        try:
            await process_alert_outbox_async()
        except asyncio.CancelledError:
            _log.info("Alert Outbox Worker loop cancelled.")
            break
        except Exception as exc:
            _log.error("Error in Alert Outbox Worker loop: %s", exc)
        await asyncio.sleep(poll_interval)


def stop_outbox_loop():
    """Остановить фоновый воркер очереди."""
    global _outbox_loop_task
    if _outbox_loop_task and not _outbox_loop_task.done():
        _outbox_loop_task.cancel()
        _outbox_loop_task = None


def process_unacked_escalations() -> int:
    """Проверить неотвеченные алерты и выпустить эскалацию по правилам."""
    conn = get_db_connection()
    escalated_count = 0
    try:
        rules = conn.execute(
            "SELECT id, name, min_severity, unack_timeout_sec, target_channel_id FROM escalation_rules WHERE enabled = 1"
        ).fetchall()
        if not rules:
            return 0

        now_dt = datetime.now()
        unacked = conn.execute(
            """
            SELECT id, title, message, type as severity, category, created_at, escalated 
            FROM notifications 
            WHERE acknowledged = 0 AND (escalated IS NULL OR escalated = 0)
            """
        ).fetchall()

        for notif in unacked:
            n_id = notif["id"]
            n_sev = notif["severity"]
            n_cat = notif["category"]
            n_created = notif["created_at"]

            try:
                if isinstance(n_created, str):
                    dt = datetime.strptime(n_created.split(".")[0], "%Y-%m-%d %H:%M:%S")
                else:
                    dt = n_created
                elapsed = (now_dt - dt).total_seconds()
            except Exception:
                continue

            for rule in rules:
                min_lvl = SEVERITY_LEVELS.get(rule["min_severity"].lower(), 3)
                curr_lvl = SEVERITY_LEVELS.get(n_sev.lower(), 1)
                if curr_lvl >= min_lvl and elapsed >= rule["unack_timeout_sec"]:
                    c_id = rule["target_channel_id"]
                    chan = conn.execute(
                        "SELECT id, type, config FROM alert_channels WHERE id = ? AND enabled = 1", (c_id,)
                    ).fetchone()
                    if chan:
                        provider = PROVIDERS.get(chan["type"].lower())
                        if provider:
                            esc_alert = {
                                "title": f"🚨 [ESCALATION] {notif['title']}",
                                "message": f"Алерт не принят в работу за {int(elapsed // 60)} мин!\n{notif['message']}",
                                "severity": n_sev,
                                "category": n_cat,
                            }
                            try:
                                cfg = json.loads(chan["config"]) if chan["config"] else {}
                            except Exception:
                                cfg = {}

                            res = provider(cfg, esc_alert)
                            conn.execute("UPDATE notifications SET escalated = 1 WHERE id = ?", (n_id,))
                            conn.commit()
                            escalated_count += 1
    except Exception as exc:
        _log.error("Error processing escalations: %s", exc)
    finally:
        conn.close()

    return escalated_count


def send_alert(
    title: str,
    message: str,
    severity: str = "warning",
    category: str = "system",
    force_send: bool = False,
) -> Dict[str, bool]:
    """Отправка алерта во все активные каналы рассылки.

    Сохраняет алерты в очередь `alert_outbox` для гарантированной асинхронной доставки.
    """
    results = {}
    conn = get_db_connection()
    try:
        prune_alert_caches(conn=conn)
        fingerprint = calculate_fingerprint(title, category, severity)
        is_dedup, repeat_cnt = should_deduplicate(fingerprint, conn=conn)
        if force_send:
            is_dedup = False

        in_maint = is_in_maintenance(category, conn=conn)
        in_quiet = is_in_quiet_hours(category, severity, conn=conn)

        # 1. Запись/Обновление в таблице notifications
        if is_dedup:
            conn.execute(
                """
                UPDATE notifications 
                SET repeat_count = repeat_count + 1, last_seen = CURRENT_TIMESTAMP 
                WHERE fingerprint = ? AND read = 0
                """,
                (fingerprint,),
            )
            conn.commit()
        else:
            conn.execute(
                """
                INSERT INTO notifications (title, message, type, category, fingerprint, repeat_count)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (title, message, severity, category, fingerprint),
            )
            conn.commit()

        # 2. Постановка внешних каналов в очередь alert_outbox
        rows = conn.execute(
            "SELECT id, name, type, enabled, min_type, categories, config FROM alert_channels WHERE enabled = 1"
        ).fetchall()

        with conn:
            for row in rows:
                channel_id = row["id"]
                c_type = row["type"].lower()
                min_type = row["min_type"] or "warning"
                categories = row["categories"] or "*"
                config_str = row["config"] or "{}"

                if not _should_send(min_type, severity, categories, category):
                    continue

                # Проверка Circuit Breaker для канала
                if is_channel_in_cooldown(channel_id, conn=conn):
                    suppress_reason = "Suppressed by Circuit Breaker (Channel Cooldown)"
                    results[channel_id] = False
                    conn.execute(
                        """
                        INSERT INTO alert_log (channel_id, channel_type, title, message, severity, category, success, error_message, retry_count, suppressed)
                        VALUES (?, ?, ?, ?, ?, ?, 0, ?, 0, 1)
                        """,
                        (channel_id, c_type, title, message, severity, category, suppress_reason),
                    )
                    continue

                # Проверка глушения (Maintenance, Quiet Hours, Deduplication или Flapping)
                flapping_active = is_flapping(fingerprint, conn=conn)
                if in_maint or in_quiet or is_dedup or flapping_active:
                    if in_maint:
                        suppress_reason = "Suppressed by Maintenance Window"
                    elif in_quiet:
                        suppress_reason = "Suppressed by Quiet Hours"
                    elif flapping_active:
                        suppress_reason = "Suppressed by Flapping Protection"
                    else:
                        suppress_reason = "Suppressed by Deduplication"
                    results[channel_id] = True
                    conn.execute(
                        """
                        INSERT INTO alert_log (channel_id, channel_type, title, message, severity, category, success, error_message, retry_count, suppressed)
                        VALUES (?, ?, ?, ?, ?, ?, 1, ?, 0, 1)
                        """,
                        (channel_id, c_type, title, message, severity, category, suppress_reason),
                    )
                    continue

                # Добавляем задачу в очередь alert_outbox для гарантированной асинхронной доставки
                payload_str = json.dumps({"title": title, "message": message, "severity": severity, "category": category})
                conn.execute(
                    """
                    INSERT INTO alert_outbox (channel_id, channel_type, title, message, severity, category, config_json, payload_json, status, attempts, next_retry_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, CURRENT_TIMESTAMP)
                    """,
                    (channel_id, c_type, title, message, severity, category, config_str, payload_str),
                )
                results[channel_id] = True

    except Exception as exc:
        _log.error("Failed to process send_alert: %s", exc)
    finally:
        conn.close()

    # Запускаем обработку очереди, если доступен активный event loop
    try:
        loop = asyncio.get_running_loop()
        if loop and loop.is_running():
            loop.create_task(process_alert_outbox_async())
    except RuntimeError:
        pass

    return results


async def send_alert_async(
    title: str,
    message: str,
    severity: str = "warning",
    category: str = "system",
    force_send: bool = False,
):
    """Асинхронный запуск рассылки алерта."""
    send_alert(title, message, severity, category, force_send)
    await process_alert_outbox_async()

