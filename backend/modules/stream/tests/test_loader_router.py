from pathlib import Path

import pytest

from backend.modules.stream.core.loader import ModuleLoader
from backend.modules.stream.core.router import choose_backend, find_candidates
from backend.modules.stream.core.types import StreamTask


@pytest.fixture(scope="module")
def loader() -> ModuleLoader:
    base = Path(__file__).resolve().parent.parent
    ld = ModuleLoader(base_dir=base)
    ld.invalidate_cache()
    return ld


def test_loader_finds_echo(loader: ModuleLoader):
    registry = loader.load()
    assert "echo" in registry


@pytest.mark.asyncio
async def test_choose_backend_echo(loader: ModuleLoader):
    task = StreamTask(
        id="t1",
        type="preview",
        source_url="http://example",
        input_protocol="http",
        output_format="http_ts",
        created_at=0.0,
        config={},
    )
    candidates = find_candidates(task, loader=loader)
    assert any(c.name == "echo" for c in candidates)
    backend_cls = choose_backend(task, loader=loader)
    backend = backend_cls()
    res = await backend.process(task)
    assert res.success is True
    assert res.backend_name == "echo"
