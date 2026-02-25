"""Unit-тесты AstraClient (новый путь backend.modules.astra.utils)."""
from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    from backend.modules.astra.utils.astra_client import AstraClient
except Exception:  # pragma: no cover - depends on env deps
    AstraClient = None


class _FakeResponse:
    def __init__(self, status_code: int, data=None, content: bytes = b"x"):
        self.status_code = status_code
        self._data = data
        self.content = content

    def json(self):
        return self._data


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self._response = kwargs.pop("_response")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def request(self, method, url, headers=None, params=None, json=None):
        return self._response


class TestAstraClient(unittest.IsolatedAsyncioTestCase):
    @unittest.skipIf(AstraClient is None, "httpx is not installed in current env")
    async def test_request_json_success(self):
        response = _FakeResponse(200, {"ok": True}, b"{}")

        def _factory(*args, **kwargs):
            return _FakeAsyncClient(_response=response)

        with patch("backend.modules.astra.utils.astra_client.httpx.AsyncClient", new=_factory):
            client = AstraClient("http://127.0.0.1:8000", api_key="k", timeout=1.0)
            code, data = await client.health()

        self.assertEqual(code, 200)
        self.assertEqual(data, {"ok": True})

    @unittest.skipIf(AstraClient is None, "httpx is not installed in current env")
    async def test_request_connect_error(self):
        from backend.modules.astra.utils import astra_client as astra_client_module

        class _FailingClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def request(self, method, url, headers=None, params=None, json=None):
                raise astra_client_module.httpx.ConnectError("boom")

        def _factory(*args, **kwargs):
            return _FailingClient()

        with patch("backend.modules.astra.utils.astra_client.httpx.AsyncClient", new=_factory):
            client = AstraClient("http://127.0.0.1:8000")
            code, data = await client.get_channels()

        self.assertEqual(code, 0)
        self.assertIn("_error", data)


if __name__ == "__main__":
    unittest.main()
