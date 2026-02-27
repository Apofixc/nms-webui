import asyncio
import json
import unittest
from pathlib import Path

from backend.modules.stream.core.loader import ModuleLoader
from backend.modules.stream.core.types import StreamTask
from backend.modules.stream.submodules.pure_proxy.backend import PureProxyBackend
from backend.modules.stream.submodules.pure_preview.backend import PurePreviewBackend
from backend.modules.stream.submodules.pure_webrtc.backend import PureWebRTCBackend


class PureBackendsTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        base = Path(__file__).resolve().parent.parent
        cls.loader = ModuleLoader(base_dir=base)
        cls.loader.invalidate_cache()

    async def test_pure_proxy_http_passthrough(self):
        backend = PureProxyBackend()
        task = StreamTask(
            id="t_proxy",
            type="stream",
            source_url="https://httpbin.org/image/png",
            input_protocol="http",
            output_format="http_ts",
            config={},
            timeout_sec=5,
            created_at=0.0,
        )
        res = await backend.process(task)
        self.assertTrue(res.success)
        self.assertTrue(res.output_path.startswith("http://127.0.0.1"))
        await backend.shutdown()

    async def test_pure_preview_http_image(self):
        backend = PurePreviewBackend()
        task = StreamTask(
            id="t_preview",
            type="preview",
            source_url="https://httpbin.org/image/png",
            input_protocol="http",
            output_format="png",
            config={},
            timeout_sec=5,
            created_at=0.0,
        )
        res = await backend.process(task)
        self.assertTrue(res.success)
        self.assertTrue(Path(res.output_path).exists())
        await backend.shutdown()

    async def test_pure_webrtc_stub(self):
        backend = PureWebRTCBackend()
        task = StreamTask(
            id="t_webrtc",
            type="stream",
            source_url="http://example",
            input_protocol="http",
            output_format="webrtc",
            config={},
            timeout_sec=1,
            created_at=0.0,
        )
        res = await backend.process(task)
        self.assertTrue(res.success)
        payload = json.loads(res.output_path)
        self.assertIn("offer", payload)
        self.assertIn("answer", payload)
        await backend.shutdown()


if __name__ == "__main__":
    unittest.main()
