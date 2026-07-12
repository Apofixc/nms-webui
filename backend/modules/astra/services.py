import logging
from typing import Any
import httpx

_log = logging.getLogger("nms.astra.services")


class AstraClient:
    """Асинхронный клиент для взаимодействия с API astra-monitor на конкретном инстансе."""

    def __init__(self, host: str, port: int, api_key: str, timeout: float = 5.0):
        self.base_url = f"http://{host}:{port}"
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {"X-API-Key": api_key}

    async def _request(
        self, method: str, path: str, json_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=self.headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=self.headers, json=json_data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                # astra-monitor может возвращать невалидный JSON в случае ошибок,
                # поэтому обрабатываем аккуратно
                return response.json()
            except httpx.HTTPStatusError as exc:
                _log.warning(
                    "HTTP error %d calling %s: %s",
                    exc.response.status_code,
                    path,
                    exc.response.text,
                )
                raise
            except Exception as exc:
                _log.warning("Connection error calling %s: %s", path, exc)
                raise

    async def get_snapshot(self) -> dict[str, Any]:
        """Получить полный снимок состояния ( snapshot включает каналы, адаптеры, логи)."""
        return await self._request("GET", "/api/snapshot")

    async def get_health(self) -> dict[str, Any]:
        """Получить статус здоровья системы."""
        return await self._request("GET", "/api/system/health")

    async def reload_config(self, delay: int = 1) -> dict[str, Any]:
        """Перезагрузить конфигурацию Astra."""
        return await self._request("POST", "/api/system/reload", {"delay": delay})

    async def restart_channel(self, channel_name: str, delay: int = 1) -> dict[str, Any]:
        """Перезапустить ТВ-канал."""
        return await self._request(
            "POST", "/api/channels/restart", {"name": channel_name, "delay": delay}
        )

    async def stop_channel(self, channel_name: str) -> dict[str, Any]:
        """Остановить ТВ-канал."""
        return await self._request("POST", "/api/channels/stop", {"name": channel_name})

    async def delete_channel(self, channel_name: str) -> dict[str, Any]:
        """Удалить ТВ-канал."""
        return await self._request("POST", "/api/channels/delete", {"name": channel_name})

    async def scan_adapter_channels(self, adapter_name: str) -> dict[str, Any]:
        """Запустить сканирование каналов на DVB-адаптере."""
        return await self._request("POST", "/api/adapters/scan-channels", {"name": adapter_name})

    async def get_adapter_scan_result(self, adapter_name: str) -> dict[str, Any]:
        """Получить результаты сканирования каналов на DVB-адаптере."""
        return await self._request("GET", f"/api/adapters/scan-result?name={adapter_name}")
