"""Диспетчер рассылки уведомлений во внешние сервисы (Telegram, Discord, Viber, Email, Webhooks, Syslog)."""

import asyncio
import json
import logging
import socket
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from backend.core.database import get_db_connection

_log = logging.getLogger("nms.notifications.dispatcher")

SEVERITY_LEVELS = {
    "info": 1,
    "success": 2,
    "warning": 3,
    "error": 4,
}


def _should_send(min_type: str, notif_type: str, categories: str, notif_cat: str) -> bool:
    """Проверить, подходит ли уведомление по типу критичности и категории."""
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
        req.add_header("User-Agent", "NMS-WebUI-NotificationDispatcher/1.0")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)

        with urllib.request.urlopen(req, timeout=timeout) as response:
            return 200 <= response.status < 300
    except Exception as exc:
        _log.warning("HTTP POST to %s failed: %s", url, exc)
        return False


# ── Провайдеры отправки ─────────────────────────────────────────

def send_telegram(config: dict, notif: dict) -> bool:
    """Отправка уведомления через Telegram Bot API."""
    bot_token = config.get("bot_token")
    chat_id = config.get("chat_id")
    if not bot_token or not chat_id:
        return False

    icon = "🔴" if notif.get("type") == "error" else ("🟡" if notif.get("type") == "warning" else "ℹ️")
    text = (
        f"{icon} <b>NMS Alert: {notif.get('title', '')}</b>\n\n"
        f"{notif.get('message', '')}\n\n"
        f"<b>Тип:</b> {notif.get('type', 'info').upper()} | <b>Категория:</b> {notif.get('category', 'system')}"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    return _make_http_post(url, payload)


def send_discord(config: dict, notif: dict) -> bool:
    """Отправка Rich Embed карточки в Discord Webhook."""
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        return False

    notif_type = notif.get("type", "info")
    color = 15158332 if notif_type == "error" else (15844367 if notif_type == "warning" else 3447003)
    icon = "🔴" if notif_type == "error" else ("🟡" if notif_type == "warning" else "ℹ️")

    payload = {
        "username": "NMS AlertBot",
        "embeds": [
            {
                "title": f"{icon} {notif.get('title', '')}",
                "description": notif.get("message", ""),
                "color": color,
                "fields": [
                    {"name": "Категория", "value": notif.get("category", "system"), "inline": True},
                    {"name": "Критичность", "value": notif_type.upper(), "inline": True},
                ],
                "footer": {"text": "NMS WebUI Monitoring"},
            }
        ],
    }
    return _make_http_post(webhook_url, payload)


def send_viber(config: dict, notif: dict) -> bool:
    """Отправка сообщения через Viber Bot REST API."""
    auth_token = config.get("auth_token")
    receiver = config.get("receiver_id")
    if not auth_token or not receiver:
        return False

    icon = "🔴" if notif.get("type") == "error" else ("🟡" if notif.get("type") == "warning" else "ℹ️")
    text = f"{icon} NMS Alert: {notif.get('title')}\n{notif.get('message')}\nCategory: {notif.get('category')}"

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


def send_email(config: dict, notif: dict) -> bool:
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
        msg["Subject"] = f"[NMS {notif.get('type', 'info').upper()}] {notif.get('title')}"
        msg["From"] = from_email
        msg["To"] = ", ".join(to_emails)

        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: {'#e11d48' if notif.get('type')=='error' else '#d97706'};">
              {notif.get('title')}
            </h2>
            <p>{notif.get('message')}</p>
            <hr />
            <p style="font-size: 12px; color: #666;">
              Категория: {notif.get('category')} | Время: {notif.get('created_at')}
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


def send_webhook(config: dict, notif: dict) -> bool:
    """Отправка произвольного HTTP Webhook (JSON Payload)."""
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        return False

    headers = {}
    if config.get("secret_token"):
        headers["X-NMS-Secret"] = config.get("secret_token")

    payload = {
        "event": "notification_created",
        "notification": notif,
    }
    return _make_http_post(webhook_url, payload, headers=headers)


def send_syslog(config: dict, notif: dict) -> bool:
    """Отправка события по UDP/TCP в Syslog/SIEM сервер (RFC 5424)."""
    syslog_host = config.get("syslog_host")
    syslog_port = int(config.get("syslog_port", 514))
    protocol = config.get("protocol", "udp").lower()

    if not syslog_host:
        return False

    try:
        msg_str = f"<134>1 NMSWebUI {notif.get('category')} - - - {notif.get('type').upper()}: {notif.get('title')} - {notif.get('message')}\n"
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


# ── Менеджер Диспетчера ────────────────────────────────────────

PROVIDERS = {
    "telegram": send_telegram,
    "discord": send_discord,
    "viber": send_viber,
    "email": send_email,
    "webhook": send_webhook,
    "syslog": send_syslog,
}


def dispatch_notification_sync(notif: dict) -> Dict[str, bool]:
    """Синхронно отправить уведомление во все активные каналы."""
    results = {}
    if not notif or not isinstance(notif, dict):
        return results

    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT id, name, type, enabled, min_type, categories, config FROM notification_integrations WHERE enabled = 1"
        ).fetchall()
        for row in rows:
            channel_id = row["id"]
            c_type = row["type"].lower()
            min_type = row["min_type"] or "warning"
            categories = row["categories"] or "*"
            
            try:
                from backend.core.crypto import decrypt_secret
                decrypted_raw = decrypt_secret(row["config"])
                config = json.loads(decrypted_raw) if decrypted_raw else {}
            except Exception:
                config = {}

            if not _should_send(min_type, notif.get("type", "info"), categories, notif.get("category", "system")):
                continue

            provider = PROVIDERS.get(c_type)
            if provider:
                try:
                    ok = provider(config, notif)
                    results[channel_id] = ok
                except Exception as exc:
                    _log.error("Provider %s error: %s", c_type, exc)
                    results[channel_id] = False
    except Exception as exc:
        _log.error("Failed to load notification integrations: %s", exc)
    finally:
        conn.close()

    return results


async def dispatch_notification_async(notif: dict):
    """Асинхронный запуск рассылки уведомлений во внешние сервисы."""
    if not notif:
        return
    await asyncio.to_thread(dispatch_notification_sync, notif)
