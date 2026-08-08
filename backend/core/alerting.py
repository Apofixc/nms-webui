"""Модуль подсистемы внешнего алертинга (Telegram, Discord, Viber, Email, Webhooks, Syslog)."""

import asyncio
import json
import logging
import socket
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

from backend.core.database import get_db_connection

_log = logging.getLogger("nms.alerting")

SEVERITY_LEVELS = {
    "info": 1,
    "success": 2,
    "warning": 3,
    "error": 4,
}


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


def _make_http_post(url: str, json_data: dict = None, headers: dict = None, timeout: float = 8.0) -> bool:
    """Вспомогательный метод для отправки HTTP POST запроса."""
    try:
        data_bytes = json.dumps(json_data).encode("utf-8") if json_data else b""
        req = urllib.request.Request(url, data=data_bytes, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "NMS-WebUI-AlertEngine/1.0")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)

        with urllib.request.urlopen(req, timeout=timeout) as response:
            return 200 <= response.status < 300
    except Exception as exc:
        _log.warning("HTTP POST to %s failed: %s", url, exc)
        return False


# ── Провайдеры отправки ─────────────────────────────────────────

def send_telegram(config: dict, alert: dict) -> bool:
    """Отправка алерта через Telegram Bot API."""
    bot_token = config.get("bot_token")
    chat_id = config.get("chat_id")
    if not bot_token or not chat_id:
        return False

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


def send_discord(config: dict, alert: dict) -> bool:
    """Отправка Rich Embed карточки в Discord Webhook."""
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        return False

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


def send_viber(config: dict, alert: dict) -> bool:
    """Отправка сообщения через Viber Bot REST API."""
    auth_token = config.get("auth_token")
    receiver = config.get("receiver_id")
    if not auth_token or not receiver:
        return False

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


def send_webhook(config: dict, alert: dict) -> bool:
    """Отправка произвольного HTTP Webhook (JSON Payload)."""
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        return False

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


def send_alert(
    title: str,
    message: str,
    severity: str = "warning",
    category: str = "system",
) -> Dict[str, bool]:
    """Синхронная отправка алерта во все активные каналы внешней рассылки.
    
    Читает таблицы alert_channels, проверяет правила фильтрации,
    вызывает соответствующего провайдера и записывает лог в alert_log.
    """
    results = {}
    alert_payload = {
        "title": title,
        "message": message,
        "severity": severity,
        "category": category,
    }

    conn = get_db_connection()
    try:
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

            provider = PROVIDERS.get(c_type)
            success = False
            err_msg = None

            if provider:
                try:
                    success = provider(config, alert_payload)
                    if not success:
                        err_msg = "Provider failed to send alert"
                except Exception as exc:
                    _log.error("Provider %s error: %s", c_type, exc)
                    success = False
                    err_msg = str(exc)
            else:
                err_msg = f"Unknown provider type: {c_type}"

            results[channel_id] = success

            # Фиксация попытки в alert_log
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO alert_log (channel_id, channel_type, title, message, severity, category, success, error_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (channel_id, c_type, title, message, severity, category, 1 if success else 0, err_msg),
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
):
    """Асинхронный запуск рассылки алерта."""
    await asyncio.to_thread(send_alert, title, message, severity, category)
