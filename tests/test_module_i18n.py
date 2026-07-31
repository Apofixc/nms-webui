"""Тесты динамической локализации модулей бэкенда."""
import json
from pathlib import Path
import tempfile
from backend.core.i18n import register_module_messages, load_module_locales, BACKEND_MESSAGES


def test_register_module_messages():
    register_module_messages({
        "custom_module.test_key": {"ru": "Тест", "en": "Test"}
    })
    assert "custom_module.test_key" in BACKEND_MESSAGES
    assert BACKEND_MESSAGES["custom_module.test_key"]["ru"] == "Тест"
    assert BACKEND_MESSAGES["custom_module.test_key"]["en"] == "Test"


def test_load_module_locales():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        locales_dir = tmp_path / "locales"
        locales_dir.mkdir()

        ru_file = locales_dir / "ru.json"
        ru_file.write_text(json.dumps({"loaded_key": "Загружено"}), encoding="utf-8")

        en_file = locales_dir / "en.json"
        en_file.write_text(json.dumps({"loaded_key": "Loaded"}), encoding="utf-8")

        load_module_locales(tmp_path)

        assert "loaded_key" in BACKEND_MESSAGES
        assert BACKEND_MESSAGES["loaded_key"]["ru"] == "Загружено"
        assert BACKEND_MESSAGES["loaded_key"]["en"] == "Loaded"
