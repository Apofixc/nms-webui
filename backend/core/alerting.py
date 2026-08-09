import asyncio
import hashlib
import json
import logging
import socket
import time
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from backend.core.database import get_db_connection

_log = logging.getLogger("nms.alerting")

SEVERITY_LEVELS = {
    "info": 1,
    "success": 2,
    "warning": 3,
    "error": 4,
}

# Кэш дедупликации: { fingerprint: (first_seen, last_seen, count) }
_dedup_cache: Dict[str, Tuple[float, float, int]] = {}
DEDUPLICATION_WINDOW_SEC = 60

# Кэш защиты от дребезга (flapping): { fingerprint: [timestamps] }
_flapping_cache: Dict[str, List[float]] = {}
FLAPPING_THRESHOLD_COUNT = 4
FLAPPING_WINDOW_SEC = 60

# Circuit Breaker для внешних каналов: { channel_id: (consecutive_failures, cooldown_until) }
_circuit_breaker: Dict[str, Tuple[int, float]] = {}
CIRCUIT_BREAKER_MAX_FAILURES = 3
CIRCUIT_BREAKER_COOLDOWN_SEC = 180  # 3 минуты


def is_flapping(fingerprint: str) -> bool:
    """Проверить, не является ли алерт дребезжащим (flapping)."""
    now = time.time()
    history = [t for t in _flapping_cache.get(fingerprint, []) if now - t <= FLAPPING_WINDOW_SEC]
    history.append(now)
    _flapping_cache[fingerprint] = history
    return len(history) >= FLAPPING_THRESHOLD_COUNT


def is_channel_in_cooldown(channel_id: str) -> bool:
    """Проверить, находится ли канал в режиме Circuit Breaker (cooldown)."""
    if channel_id not in _circuit_breaker:
        return False
    failures, cooldown_until = _circuit_breaker[channel_id]
    if failures >= CIRCUIT_BREAKER_MAX_FAILURES:
        if time.time() < cooldown_until:
            return True
        else:
            _circuit_breaker.pop(channel_id, None)
    return False


def record_channel_result(channel_id: str, success: bool):
    """Зафиксировать результат отправки в канал для Circuit Breaker."""
    now = time.time()
    failures, _ = _circuit_breaker.get(channel_id, (0, 0.0))
    if success:
        _circuit_breaker.pop(channel_id, None)
    else:
        new_failures = failures + 1
        cooldown_until = now + CIRCUIT_BREAKER_COOLDOWN_SEC if new_failures >= CIRCUIT_BREAKER_MAX_FAILURES else 0.0
        _circuit_breaker[channel_id] = (new_failures, cooldown_until)



def calculate_fingerprint(title: str, category: str, severity: str) -> str:
    """Вычислить MD5-хэш сообщения для дедупликации."""
    raw = f"{category.strip().lower()}:{severity.strip().lower()}:{title.strip().lower()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def should_deduplicate(fingerprint: str, window_sec: int = DEDUPLICATION_WINDOW_SEC) -> Tuple[bool, int]:
    """Проверить, попадает ли алерт в окно дедупликации."""
    now = time.time()
    if fingerprint in _dedup_cache:
        first_seen, last_seen, count = _dedup_cache[fingerprint]
        if now - last_seen < window_sec:
            new_count = count + 1
            _dedup_cache[fingerprint] = (first_seen, now, new_count)
            return True, new_count
    _dedup_cache[fingerprint] = (now, now, 1)
    return False, 1


def reset_dedup_cache():
    """Очистить кэш дедупликации (для тестов/сброса)."""
    _dedup_cache.clear()


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


def _make_http_post(url: str, json_data: dict = None, headers: dict = None, timeout: float = 8.0, max_retries: int = 3) -> Tuple[bool, int]:
    """Вспомогательный метод для отправки HTTP POST запроса с повторными попытками.
    Возвращает (success, retries_done).
    """
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


# ── Провайдеры отправки ─────────────────────────────────────────

def send_telegram(config: dict, alert: dict) -> Union[bool, Tuple[bool, int]]:
    """Отправка алерта через Telegram Bot API."""
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


def send_discord(config: dict, alert: dict) -> Union[bool, Tuple[bool, int]]:
    """Отправка Rich Embed карточки в Discord Webhook."""
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


def send_viber(config: dict, alert: dict) -> Union[bool, Tuple[bool, int]]:
    """Отправка сообщения через Viber Bot REST API."""
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


def send_webhook(config: dict, alert: dict) -> Union[bool, Tuple[bool, int]]:
    """Отправка произвольного HTTP Webhook (JSON Payload)."""
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
    """Синхронная отправка алерта во все активные каналы рассылки.

    Учитывает дедупликацию, шаблонизацию, окна технического обслуживания и retry-логику.
    """
    results = {}
    fingerprint = calculate_fingerprint(title, category, severity)
    is_dedup, repeat_cnt = should_deduplicate(fingerprint)
    if force_send:
        is_dedup = False

    conn = get_db_connection()
    try:
        in_maint = is_in_maintenance(category, conn=conn)

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

        # 2. Обработка внешних каналов
        rows = conn.execute(
            "SELECT id, name, type, enabled, min_type, categories, config FROM alert_channels WHERE enabled = 1"
        ).fetchall()

        for row in rows:
            channel_id = row["id"]
            c_type = row["type"].lower()
            min_type = row["min_type"] or "warning"
            categories = row["categories"] or "*"

            try:
                config = json.loads(row["config"])
            except Exception:
                config = {}

            if not _should_send(min_type, severity, categories, category):
                continue

            # Проверка Circuit Breaker для канала
            if is_channel_in_cooldown(channel_id):
                suppress_reason = "Suppressed by Circuit Breaker (Channel Cooldown)"
                results[channel_id] = False
                try:
                    with conn:
                        conn.execute(
                            """
                            INSERT INTO alert_log (channel_id, channel_type, title, message, severity, category, success, error_message, retry_count, suppressed)
                            VALUES (?, ?, ?, ?, ?, ?, 0, ?, 0, 1)
                            """,
                            (channel_id, c_type, title, message, severity, category, suppress_reason),
                        )
                except Exception as log_exc:
                    _log.warning("Failed to log circuit breaker alert: %s", log_exc)
                continue

            # Проверка глушения (Maintenance, Deduplication или Flapping)
            flapping_active = is_flapping(fingerprint)
            if in_maint or is_dedup or flapping_active:
                if in_maint:
                    suppress_reason = "Suppressed by Maintenance Window"
                elif flapping_active:
                    suppress_reason = "Suppressed by Flapping Protection"
                else:
                    suppress_reason = "Suppressed by Deduplication"
                results[channel_id] = True
                try:
                    with conn:
                        conn.execute(
                            """
                            INSERT INTO alert_log (channel_id, channel_type, title, message, severity, category, success, error_message, retry_count, suppressed)
                            VALUES (?, ?, ?, ?, ?, ?, 1, ?, 0, 1)
                            """,
                            (channel_id, c_type, title, message, severity, category, suppress_reason),
                        )
                except Exception as log_exc:
                    _log.warning("Failed to log suppressed alert: %s", log_exc)
                continue

            # Подготовка сообщения с возможной шаблонизацией (Rich Context)
            raw_payload = {
                "title": title,
                "message": message,
                "severity": severity,
                "category": category,
            }
            alert_payload = _format_message_with_template(config, raw_payload)

            provider = PROVIDERS.get(c_type)
            success = False
            err_msg = None
            retries_done = 0

            if provider:
                try:
                    p_res = provider(config, alert_payload)
                    if isinstance(p_res, tuple):
                        success, retries_done = p_res
                    else:
                        success = bool(p_res)
                    if not success:
                        err_msg = "Provider failed to send alert"
                except Exception as exc:
                    _log.error("Provider %s error: %s", c_type, exc)
                    success = False
                    err_msg = str(exc)
            else:
                err_msg = f"Unknown provider type: {c_type}"

            record_channel_result(channel_id, success)
            results[channel_id] = success

            # Логирование в alert_log
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO alert_log (channel_id, channel_type, title, message, severity, category, success, error_message, retry_count, suppressed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                        """,
                        (channel_id, c_type, title, message, severity, category, 1 if success else 0, err_msg, retries_done),
                    )
            except Exception as log_exc:
                _log.warning("Failed to insert into alert_log: %s", log_exc)

    except Exception as exc:
        _log.error("Failed to process send_alert: %s", exc)
    finally:
        conn.close()

    return results


async def send_alert_async(
    title: str,
    message: str,
    severity: str = "warning",
    category: str = "system",
    force_send: bool = False,
):
    """Асинхронный запуск рассылки алерта."""
    await asyncio.to_thread(send_alert, title, message, severity, category, force_send)

