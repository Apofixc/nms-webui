import asyncio
import unittest
from pathlib import Path

from backend.modules.stream.core.loader import ModuleLoader
from backend.modules.stream.core.router import choose_backend, find_candidates
from backend.modules.stream.core.types import StreamTask


class LoaderRouterTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        base = Path(__file__).resolve().parent.parent
        cls.loader = ModuleLoader(base_dir=base)
        cls.loader.invalidate_cache()

    def test_loader_finds_echo(self):
        registry = self.loader.load()
        self.assertIn("echo", registry)

    async def test_choose_backend_echo(self):
        task = StreamTask(
            id="t1",
            type="preview",
            source_url="http://example",
            input_protocol="http",
            output_format="http_ts",
            created_at=0.0,
            config={},
        )
        candidates = find_candidates(task, loader=self.loader)
        self.assertTrue(any(c.name == "echo" for c in candidates))
        backend_cls = choose_backend(task, loader=self.loader)
        backend = backend_cls()
        res = await backend.process(task)
        self.assertTrue(res.success)
        self.assertIn(res.backend_name, [c.name for c in candidates])


if __name__ == "__main__":
    unittest.main()
