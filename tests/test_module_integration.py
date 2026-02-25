#!/usr/bin/env python3
"""Интеграционные проверки загрузки модулей и graceful degradation."""
from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from backend.core.module_registry import get_modules
from backend.core.module_router import load_module_routers


class _FakeApp:
    def __init__(self):
        self.routes: list[object] = []

    def include_router(self, router):
        self.routes.append(router)


class TestModuleIntegration(unittest.TestCase):
    def test_module_registry_discovers_nested_manifests(self):
        modules = get_modules(with_settings=False, only_enabled=False)
        ids = {m.get("id") for m in modules}
        self.assertIn("cesbo-astra", ids)
        self.assertIn("cesbo-astra.instances-api", ids)
        self.assertIn("stream", ids)
        self.assertIn("stream.playback", ids)
        self.assertIn("telegraf", ids)
        self.assertIn("telegraf.metrics-api", ids)

    def test_graceful_degradation_on_broken_module_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            modules_dir = Path(tmp)

            ok_mod = modules_dir / "ok_mod"
            ok_mod.mkdir(parents=True, exist_ok=True)
            (ok_mod / "manifest.yaml").write_text(
                textwrap.dedent(
                    """
                    id: ok-mod
                    name: Ok module
                    version: 1.0.0
                    enabled_by_default: true
                    deps: []
                    entrypoints: {}
                    hooks: {}
                    assets:
                      cache_dirs: []
                      data_dirs: []
                    config_schema: null
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            bad_mod = modules_dir / "bad_mod"
            bad_mod.mkdir(parents=True, exist_ok=True)
            (bad_mod / "manifest.yaml").write_text(
                textwrap.dedent(
                    """
                    id: bad-mod
                    name: Bad module
                    version: 1.0.0
                    enabled_by_default: true
                    deps: []
                    entrypoints:
                      router: backend.nope.module:router_factory
                    hooks: {}
                    assets:
                      cache_dirs: []
                      data_dirs: []
                    config_schema: null
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            app = _FakeApp()
            load_module_routers(app, modules_dir=modules_dir)
            # broken entrypoint не должен валить загрузку приложения
            self.assertIsInstance(app.routes, list)


if __name__ == "__main__":
    unittest.main()
