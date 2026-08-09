import io
import pytest
from pathlib import Path
from backend.core.log_providers import (
    BaseLogProvider,
    LocalFileLogProvider,
    RemoteHTTPLogProvider,
    LogProviderRegistry,
    log_provider_registry,
    matches_log_level,
    clean_ansi,
)

def test_clean_ansi_codes():
    raw_ansi = "\x1b[38;5;40;1m[INFO]\x1b[0m Starting server"
    cleaned = clean_ansi(raw_ansi)
    assert cleaned == "[INFO] Starting server"

def test_matches_log_level_cases():
    assert matches_log_level("2026-07-30 | INFO | App started", "INFO") is True
    assert matches_log_level("2026-07-30 | ERROR | App error info", "INFO") is False
    assert matches_log_level("2026-07-30 | WARNING | App warning", "WARN") is True

@pytest.mark.anyio
async def test_local_file_log_provider(tmp_path):
    log_file = tmp_path / "test_module.log"
    log_file.write_text(
        "2026-07-30 | INFO | Line 1 info\n"
        "2026-07-30 | ERROR | Line 2 error\n"
        "2026-07-30 | WARNING | Line 3 warning\n",
        encoding="utf-8"
    )

    provider = LocalFileLogProvider("test.log", "Test Log", log_file, category="module")
    assert await provider.is_available() is True

    # Test ALL
    res_all = await provider.get_logs(lines=10, level="ALL")
    assert res_all["total_lines"] == 3
    assert len(res_all["content"]) == 3

    # Test ERROR
    res_err = await provider.get_logs(lines=10, level="ERROR")
    assert len(res_err["content"]) == 1
    assert "Line 2 error" in res_err["content"][0]

    # Test download
    content, filename, media_type = await provider.download_log()
    assert b"Line 1 info" in content
    assert filename == "test_module.log"

@pytest.mark.anyio
async def test_log_provider_registry():
    registry = LogProviderRegistry()
    dummy = LocalFileLogProvider("dummy.log", "Dummy", Path("/tmp/nonexistent.log"))
    registry.register(dummy)

    assert registry.get("dummy.log") == dummy
    providers = await registry.list_all()
    assert any(p["id"] == "dummy.log" for p in providers)

    registry.unregister("dummy.log")
    assert registry.get("dummy.log") is None
