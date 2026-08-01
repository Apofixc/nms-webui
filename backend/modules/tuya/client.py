"""Клиенты взаимодействия с устройствами Tuya (Cloud OpenAPI и Local LAN)."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import struct
import time
from typing import Any
import httpx

_log = logging.getLogger("nms.module.tuya.client")

# Безопасный импорт AES шифрования (Crypto или cryptography)
try:
    from Crypto.Cipher import AES as _PyCryptoAES

    def _aes_encrypt(key: bytes, raw: bytes) -> bytes:
        cipher = _PyCryptoAES.new(key, _PyCryptoAES.MODE_CBC, key)
        pad_len = 16 - (len(raw) % 16)
        padded = raw + bytes([pad_len] * pad_len)
        return cipher.encrypt(padded)

    def _aes_decrypt(key: bytes, enc: bytes) -> bytes:
        cipher = _PyCryptoAES.new(key, _PyCryptoAES.MODE_CBC, key)
        decrypted = cipher.decrypt(enc)
        if not decrypted:
            return decrypted
        pad_len = decrypted[-1]
        if pad_len > 16 or pad_len == 0:
            return decrypted
        return decrypted[:-pad_len]

except ImportError:
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        def _aes_encrypt(key: bytes, raw: bytes) -> bytes:
            cipher = Cipher(algorithms.AES(key), modes.CBC(key), backend=default_backend())
            encryptor = cipher.encryptor()
            pad_len = 16 - (len(raw) % 16)
            padded = raw + bytes([pad_len] * pad_len)
            return encryptor.update(padded) + encryptor.finalize()

        def _aes_decrypt(key: bytes, enc: bytes) -> bytes:
            cipher = Cipher(algorithms.AES(key), modes.CBC(key), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(enc) + decryptor.finalize()
            if not decrypted:
                return decrypted
            pad_len = decrypted[-1]
            if pad_len > 16 or pad_len == 0:
                return decrypted
            return decrypted[:-pad_len]

    except ImportError:
        def _aes_encrypt(key: bytes, raw: bytes) -> bytes:
            return raw

        def _aes_decrypt(key: bytes, enc: bytes) -> bytes:
            return enc


# Региональные URL для Tuya OpenAPI v1.0
TUYA_ENDPOINTS = {
    "eu": "https://openapi.tuyaeu.com",
    "us": "https://openapi.tuyaus.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}


class TuyaCloudClient:
    """Асинхронный клиент Tuya Cloud OpenAPI v1.0."""

    def __init__(self, client_id: str, client_secret: str, region: str = "eu"):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.endpoint = TUYA_ENDPOINTS.get(region.lower(), TUYA_ENDPOINTS["eu"])
        self.access_token: str | None = None
        self.token_expire_time: float = 0

    def _calc_sign(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        t: str | None = None,
        access_token: str | None = None,
    ) -> tuple[str, str]:
        """Расчёт HMAC-SHA256 подписи запроса к Tuya Cloud OpenAPI."""
        if t is None:
            t = str(int(time.time() * 1000))

        # Формирование URL строки с параметрами
        url = path
        if params:
            sorted_params = sorted(params.items())
            query_str = "&".join(f"{k}={v}" for k, v in sorted_params)
            url += f"?{query_str}"

        # SHA256 от тела запроса
        body_bytes = json.dumps(body).encode("utf-8") if body else b""
        content_hash = hashlib.sha256(body_bytes).hexdigest()

        # Строка для подписи (stringToSign)
        string_to_sign = f"{method.upper()}\n{content_hash}\n\n{url}"

        # Конкатенация для генерации подписи
        token_str = access_token or ""
        sign_str = f"{self.client_id}{token_str}{t}{string_to_sign}"

        sign = hmac.new(
            self.client_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()

        return sign, t

    async def get_access_token(self) -> str | None:
        """Получить или обновить OAuth2 Access Token."""
        if self.access_token and time.time() < self.token_expire_time - 60:
            return self.access_token

        path = "/v1.0/token?grant_type=1"
        sign, t = self._calc_sign("GET", path)

        headers = {
            "client_id": self.client_id,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256",
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.endpoint}{path}", headers=headers, timeout=10.0)
                data = resp.json()
                if data.get("success"):
                    result = data.get("result", {})
                    self.access_token = result.get("access_token")
                    expire_in = result.get("expire_time", 7200)
                    self.token_expire_time = time.time() + expire_in
                    _log.info("Successfully obtained Tuya Cloud Access Token")
                    return self.access_token
                else:
                    _log.warning("Failed to obtain Tuya Access Token: %s", data)
            except Exception as exc:
                _log.error("Exception during Tuya Access Token request: %s", exc)
        return None

    async def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Выполнить подписанный запрос к Tuya Cloud."""
        token = await self.get_access_token()
        if not token:
            return None

        sign, t = self._calc_sign(method, path, params=params, body=body, access_token=token)
        headers = {
            "client_id": self.client_id,
            "access_token": token,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.endpoint}{path}"
                resp = await client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=body,
                    timeout=10.0,
                )
                return resp.json()
            except Exception as exc:
                _log.error("Cloud request failed %s %s: %s", method, path, exc)
                return None

    async def get_device_status(self, device_id: str) -> list[dict[str, Any]] | None:
        """Получить текущие статусы (DPS) устройства из Tuya Cloud."""
        res = await self.request("GET", f"/v1.0/devices/{device_id}/status")
        if res and res.get("success"):
            return res.get("result", [])
        return None

    async def send_command(self, device_id: str, commands: list[dict[str, Any]]) -> bool:
        """Отправить команды управления устройству через Tuya Cloud."""
        body = {"commands": commands}
        res = await self.request("POST", f"/v1.0/devices/{device_id}/commands", body=body)
        if res and res.get("success"):
            return True
        _log.warning("Failed to send command via Cloud for %s: %s", device_id, res)
        return False


class TuyaLocalClient:
    """Асинхронный клиент прямого управления по локальной сети (Tuya LAN Protocol)."""

    PREFIX = 0x000055AA
    SUFFIX = 0x0000AA55

    # Основные типы сообщений Tuya LAN
    CMD_CONTROL = 7
    CMD_STATUS = 10
    CMD_HEARTBEAT = 9

    def __init__(self, ip: str, device_id: str, local_key: str, protocol_version: str = "3.3", port: int = 6668):
        self.ip = ip
        self.device_id = device_id
        self.local_key = local_key.encode("utf-8")
        self.protocol_version = protocol_version
        self.port = port

    def _pad(self, data: bytes) -> bytes:
        """PKCS7 дополнение данных для AES шифрования."""
        pad_len = 16 - (len(data) % 16)
        return data + bytes([pad_len] * pad_len)

    def _unpad(self, data: bytes) -> bytes:
        """Снятие PKCS7 дополнения."""
        if not data:
            return data
        pad_len = data[-1]
        if pad_len > 16 or pad_len == 0:
            return data
        return data[:-pad_len]

    def _encrypt(self, raw: bytes) -> bytes:
        """AES-128-CBC шифрование с использованием local_key."""
        return _aes_encrypt(self.local_key, raw)

    def _decrypt(self, enc: bytes) -> bytes:
        """AES-128-CBC расшифровка с использованием local_key."""
        return _aes_decrypt(self.local_key, enc)


    def _pack_message(self, command: int, payload: bytes) -> bytes:
        """Сборка бинарного фрейма Tuya 0x000055AA ... 0x0000AA55."""
        seq = 0
        header = struct.pack(">IIII", self.PREFIX, seq, command, len(payload) + 8)
        crc = hashlib.crc32(header + payload) & 0xFFFFFFFF
        footer = struct.pack(">II", crc, self.SUFFIX)
        return header + payload + footer

    def create_control_payload(self, dps: dict[str, Any]) -> bytes:
        """Создание зашифрованного payload для отправки DPS команд."""
        now = int(time.time())
        data = {
            "devId": self.device_id,
            "uid": self.device_id,
            "t": str(now),
            "dps": dps,
        }
        json_data = json.dumps(data).encode("utf-8")

        if self.protocol_version in ("3.3", "3.4", "3.5"):
            # Для 3.3 префикс версии перед зашифрованными данными
            enc = self._encrypt(json_data)
            ver_prefix = self.protocol_version.encode("utf-8") + (b"\x00" * 12)
            return ver_prefix + enc
        else:
            # Для 3.1
            return self._encrypt(json_data)

    async def send_command(self, dps: dict[str, Any], timeout: float = 3.0) -> bool:
        """Отправить команды управления по локальной сети."""
        try:
            payload = self.create_control_payload(dps)
            msg = self._pack_message(self.CMD_CONTROL, payload)

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.port),
                timeout=timeout,
            )
            writer.write(msg)
            await writer.drain()

            # Чтение ответа устройства
            _ = await asyncio.wait_for(reader.read(1024), timeout=timeout)
            writer.close()
            await writer.wait_closed()
            _log.info("Successfully sent local command for device %s to IP %s", self.device_id, self.ip)
            return True
        except Exception as exc:
            _log.warning("Failed to send local command for %s to IP %s: %s", self.device_id, self.ip, exc)
            return False


class TuyaDeviceController:
    """Универсальный контроллер с поддержкой гибридного режима (`auto`/`local`/`cloud`)."""

    def __init__(self, cloud_client: TuyaCloudClient | None = None):
        self.cloud_client = cloud_client

    async def send_command(
        self,
        device_id: str,
        commands: list[dict[str, Any]] | dict[str, Any],
        mode: str = "auto",
        ip: str | None = None,
        local_key: str | None = None,
        protocol_version: str = "3.3",
    ) -> bool:
        """Отправка команды устройству с автоматическим fallback при выборе `auto`."""
        dps_dict: dict[str, Any] = {}
        cloud_commands: list[dict[str, Any]] = []

        if isinstance(commands, dict):
            dps_dict = commands
            cloud_commands = [{"code": str(k), "value": v} for k, v in commands.items()]
        elif isinstance(commands, list):
            cloud_commands = commands
            for cmd in commands:
                if "code" in cmd and "value" in cmd:
                    dps_dict[str(cmd["code"])] = cmd["value"]

        # 1. Попытка локального отправления
        if mode in ("local", "auto") and ip and local_key:
            local_client = TuyaLocalClient(ip, device_id, local_key, protocol_version)
            success = await local_client.send_command(dps_dict)
            if success:
                return True
            if mode == "local":
                return False

        # 2. Попытка отправки через облако (при cloud или fallback в auto)
        if mode in ("cloud", "auto") and self.cloud_client:
            return await self.cloud_client.send_command(device_id, cloud_commands)

        _log.error("Failed to execute command for %s (mode=%s): no suitable transport available", device_id, mode)
        return False
