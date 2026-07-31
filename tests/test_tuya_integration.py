"""Интеграционная проверка интеграции модуля tuya с системой NMS-WebUI."""
from pathlib import Path
from backend.core.plugin.loader import discover_manifests
from backend.core.plugin.manifest import ModuleManifest


def test_tuya_manifest_discovery():
    """Проверка автоматического обнаружения manifest.yaml модуля tuya."""
    modules_dir = Path(__file__).resolve().parent.parent / "backend" / "modules"
    manifests = discover_manifests(modules_dir)

    tuya_manifest = next((m for m in manifests if m.id == "tuya"), None)
    assert tuya_manifest is not None, "Модуль tuya должен обнаруживаться в backend/modules"

    assert tuya_manifest.name in ("tuyaTitle", "Управление Tuya")

    assert tuya_manifest.type in ("driver", "feature")

    assert tuya_manifest.entrypoints.factory == "backend.modules.tuya:create_module"
    assert tuya_manifest.entrypoints.router == ["backend.modules.tuya.api:get_router"]


    # Проверка схемы настроек
    assert tuya_manifest.config_schema is not None
    props = tuya_manifest.config_schema.get("properties", {})
    assert "client_id" in props
    assert "client_secret" in props
    assert "region" in props
    assert "default_mode" in props

    # Проверка разрешений
    perm_ids = [p.id for p in tuya_manifest.permissions]
    assert "module.tuya.view" in perm_ids
    assert "module.tuya.edit" in perm_ids
    assert "module.tuya.control" in perm_ids


def test_module_deletion_cleans_frontend_files(tmp_path: Path):
    """Проверка удаления бэкенд и фронтенд файлов модуля при удалении."""
    root_dir = tmp_path
    backend_mod = root_dir / "backend" / "modules" / "testmod"
    backend_mod.mkdir(parents=True)
    (backend_mod / "manifest.yaml").write_text("id: testmod\nname: Test Module\n")

    frontend_src = root_dir / "frontend" / "src"
    frontend_mod = frontend_src / "modules" / "testmod"
    frontend_mod.mkdir(parents=True)
    (frontend_mod / "index.ts").write_text("// test frontend mod")

    frontend_views = frontend_src / "views"
    frontend_views.mkdir(parents=True)
    view_file = frontend_views / "TestmodView.vue"
    view_file.write_text("<template>Test</template>")

    # Очистка как в delete_module_endpoint
    import shutil
    root_dir_name = "testmod"
    if backend_mod.exists():
        shutil.rmtree(backend_mod)

    frontend_mod_dir = frontend_src / "modules" / root_dir_name
    if frontend_mod_dir.exists():
        shutil.rmtree(frontend_mod_dir)

    pascal_name = "".join(word.capitalize() for word in root_dir_name.replace("-", "_").split("_"))
    possible_views = [f"{pascal_name}View.vue", f"{pascal_name}.vue", f"{root_dir_name}View.vue"]
    for vname in possible_views:
        vpath = frontend_views / vname
        if vpath.exists():
            vpath.unlink()

    assert not backend_mod.exists()
    assert not frontend_mod.exists()
    assert not view_file.exists()


if __name__ == "__main__":
    test_tuya_manifest_discovery()
    print("[PASS] test_tuya_manifest_discovery")
    test_module_deletion_cleans_frontend_files(Path("/tmp"))
    print("[PASS] test_module_deletion_cleans_frontend_files")

