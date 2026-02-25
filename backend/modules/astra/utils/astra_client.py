"""HTTP-клиент к API lib-monitor (Astra). Заголовок X-Api-Key."""
from __future__ import annotations

import json as _json
from typing import Any

import httpx


class AstraClient:
    def __init__(self, base_url: str, api_key: str = "test", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.headers = {"X-Api-Key": api_key}
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    async def request(
        self, method: str, path: str, *, params: dict | None = None, json: dict | None = None
    ) -> tuple[int, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                r = await client.request(
                    method, self._url(path), headers=self.headers, params=params, json=json
                )
                if not r.content:
                    return r.status_code, None
                try:
                    return r.status_code, r.json()
                except _json.JSONDecodeError:
                    return r.status_code, None
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                return 0, {"_error": str(e)}

    async def health(self) -> tuple[int, Any]:
        return await self.request("GET", "/api/system/health")

    async def system_reload(self, delay_sec: int | None = None) -> tuple[int, Any]:
        params = {"delay": delay_sec} if delay_sec is not None else None
        return await self.request("POST", "/api/system/reload", params=params)

    async def system_exit(self, delay_sec: int | None = None) -> tuple[int, Any]:
        params = {"delay": delay_sec} if delay_sec is not None else None
        return await self.request("POST", "/api/system/exit", params=params)

    async def system_clear_cache(self) -> tuple[int, Any]:
        return await self.request("POST", "/api/system/clear-cache")

    async def get_channels(self) -> tuple[int, Any]:
        return await self.request("GET", "/api/channels")

    async def get_channels_stats(self) -> tuple[int, Any]:
        return await self.request("GET", "/api/channels/stats")

    async def get_channel_info(self, name: str) -> tuple[int, Any]:
        return await self.request("GET", "/api/channels/info", params={"name": name})

    async def get_channel_inputs(self, name: str) -> tuple[int, Any]:
        return await self.request("GET", "/api/channels/inputs", params={"name": name})

    async def channel_kill(self, name: str, reboot: bool = False) -> tuple[int, Any]:
        return await self.request(
            "DELETE", "/api/channels/kill", params={"name": name, "reboot": str(reboot).lower()}
        )

    async def channel_create(self, body: dict) -> tuple[int, Any]:
        return await self.request("POST", "/api/channels", json=body)

    async def stream_create(self, body: dict) -> tuple[int, Any]:
        return await self.request("POST", "/api/streams", json=body)

    async def stream_kill(self, name: str, reboot: bool = False) -> tuple[int, Any]:
        return await self.request(
            "DELETE", "/api/streams/kill", params={"name": name, "reboot": str(reboot).lower()}
        )

    async def get_monitors(self) -> tuple[int, Any]:
        return await self.request("GET", "/api/monitors")

    async def get_monitors_status(self) -> tuple[int, Any]:
        return await self.request("GET", "/api/monitors/status")

    async def get_monitor_data(self, name: str) -> tuple[int, Any]:
        return await self.request("GET", "/api/monitors/data", params={"name": name})

    async def get_dvb_adapters(self) -> tuple[int, Any]:
        return await self.request("GET", "/api/dvb/adapters")

    async def get_dvb_adapter_data(self, name: str) -> tuple[int, Any]:
        return await self.request("GET", "/api/dvb/adapters/data", params={"name": name})

    async def get_subscribers(self) -> tuple[int, Any]:
        return await self.request("GET", "/api/subscribers")

    async def get_system_api_stats(self) -> tuple[int, Any]:
        return await self.request("GET", "/api/system/api-stats")

    async def get_system_network_interfaces(self) -> tuple[int, Any]:
        return await self.request("GET", "/api/system/network/interfaces")

    async def get_system_network_hostname(self) -> tuple[int, Any]:
        return await self.request("GET", "/api/system/network/hostname")

    async def get_utils_info(self) -> tuple[int, Any]:
        return await self.request("GET", "/api/utils/info")
