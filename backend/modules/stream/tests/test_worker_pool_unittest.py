import asyncio
import unittest
from pathlib import Path

from backend.modules.stream.core.loader import ModuleLoader
from backend.modules.stream.core.worker_pool import WorkerPool
from backend.modules.stream.core.types import StreamTask


class WorkerPoolTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        base = Path(__file__).resolve().parent.parent
        cls.loader = ModuleLoader(base_dir=base)
        cls.loader.invalidate_cache()

    async def test_submit_and_get_result(self):
        pool = WorkerPool(max_workers=1, queue_maxsize=10, pipeline=None)
        task = StreamTask(
            id="",
            type="preview",
            source_url="http://example",
            input_protocol="http",
            output_format="http_ts",
            created_at=0.0,
            config={},
        )
        task_id = await pool.submit(task)
        res = await pool.get_result(task_id, timeout=2.0)
        self.assertIsNotNone(res)
        self.assertTrue(res.success)
        await pool.shutdown()


if __name__ == "__main__":
    unittest.main()
