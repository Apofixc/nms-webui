---
description: NMS WebUI Backend Refactoring Completion Plan
---

# NMS WebUI Backend Refactoring Completion

## Статус: ✅ ЗАВЕРШЕНО

### ✅ Выполненные шаги

#### 1) Ядро выделено в `backend/core/`
- ✅ `backend/core/__init__.py`
- ✅ `backend/core/config.py`
- ✅ `backend/core/module_router.py`
- ✅ `backend/core/module_registry.py`
- ✅ `backend/core/module_state.py`
- ✅ `backend/core/webui_settings.py`
- ✅ `backend/core/utils.py`

#### 2) Доменная логика разнесена по `backend/modules/`
- ✅ `backend/modules/astra/` (aggregator, health_checker, utils/astra_client, submodules)
- ✅ `backend/modules/stream/` (services, submodules, backends, core, outputs, utils)
- ✅ `backend/modules/telegraf/` (submodules)
- ✅ `backend/modules/settings/` (api.py)
- ✅ `backend/modules/aggregates/` (api.py)

#### 3) Legacy shim-слой удалён (hard-cut)
- ✅ Все shim-файлы из корня `backend/` удалены
- ✅ Все импорты переведены на `backend.core.*` / `backend.modules.*`

#### 4) `backend/stream/*` перенесён в `backend/modules/stream/*`
- ✅ Перемещены `backends/`, `core/`, `outputs/`, `utils/`, `capture.py`, `playback.py`, `__init__.py`
- ✅ Импорты обновлены на `backend.modules.stream.*`

#### 5) Дублирующая зона `system` удалена
- ✅ Удалён `backend/modules/system/`, оставлен только `telegraf`

#### 6) Нестабильные backend'ы переписаны с нуля
- ✅ **VLC**: минималистичный pipeline, явные команды, stderr логирование
- ✅ **GStreamer**: только udp/http/file, корректный UDP source через `parse_udp_url`
- ✅ **TSDuck**: только udp_ts, явные команды, stderr логирование
- ✅ FFmpeg и Astra оставлены без изменений (работают)

#### 7) Приоритет бэкендов обновлён
- ✅ `STREAM_BACKEND_ORDER` → `["ffmpeg", "astra", "vlc", "gstreamer", "tsduck", "udp_proxy"]`

#### 8) Пути discovery модулей исправлены
- ✅ `backend/core/module_router.py` → `modules_dir = Path(__file__).resolve().parent.parent / "modules"`
- ✅ `backend/core/module_registry.py` → `modules_dir = Path(__file__).resolve().parent.parent / "modules"`

#### 9) Запуск через `run_webui.sh` работает
- ✅ `./run_webui.sh backend` — работает
- ✅ `./run_webui.sh all` — работает (backend + frontend)
- ✅ API эндпоинты отвечают 200 OK

---

## 📋 Что дальше делать (не относится к рефакторингу)

### Git LFS для больших бинарников
Текущая проблема: `bin_module/ffmpeg/bin/*` превышает 100MB лимит GitHub.

**Решение:**
```bash
# Установить Git LFS
git lfs install

# Добавить большие бинарники в LFS
git lfs track "bin_module/ffmpeg/bin/*"
git add .gitattributes
git add bin_module/ffmpeg/bin/*
git commit -m "Add FFmpeg binaries to Git LFS"

# Переписать историю без больших файлов
bfg --strip-blobs-bigger-than 100M .
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push --force
```

### Опциональные улучшения (не срочно)
- [ ] Добавить unit-тесты для новых stream backend'ов
- [ ] Оптимизировать Docker-образ для production
- [ ] Добавить health checks для модулей
- [ ] Обновить документацию API

---

**Итог: рефакторинг завершён. Backend полностью модуляризован и работает.**
