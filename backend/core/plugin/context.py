"""ModuleContext — минимальный контекст для инициализации модулей."""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from backend.core.exceptions import PermissionDeniedError


class ModuleEvents:
    """Управление подписками и публикацией событий для конкретного модуля."""

    def __init__(self, module_id: str) -> None:
        self.module_id = module_id
        self._subscriptions: list[tuple[str, Callable]] = []

    def publish(self, topic: str, payload: Any = None) -> int:
        """Опубликовать событие от имени модуля.

        Короткая форма (например, 'devices.down') разворачивается в '<module_id>.devices.down'.
        Публикация в топики 'core.*' строго запрещена.
        """
        if topic.startswith("core.") or topic == "core":
            raise PermissionDeniedError(f"Modules cannot publish to reserved 'core.*' topic: {topic}")

        if topic.startswith(f"{self.module_id}."):
            full_topic = topic
        else:
            full_topic = f"{self.module_id}.{topic}"

        from backend.core.bus import event_bus
        return event_bus.publish(full_topic, payload, is_core=False)

    def subscribe(self, pattern: str, handler: Callable) -> Callable:
        """Зарегистрировать обработчик событий для маски/топика."""
        from backend.core.bus import event_bus
        event_bus.subscribe(pattern, handler)
        sub = (pattern, handler)
        if sub not in self._subscriptions:
            self._subscriptions.append(sub)
        return handler

    def unsubscribe(self, pattern: str | Callable, handler: Callable | None = None) -> bool:
        """Снять конкретную подписку."""
        from backend.core.bus import event_bus
        removed = event_bus.unsubscribe(pattern, handler)
        if removed:
            if callable(pattern) and handler is None:
                self._subscriptions = [s for s in self._subscriptions if s[1] != pattern]
            elif isinstance(pattern, str) and handler is not None:
                sub = (pattern, handler)
                if sub in self._subscriptions:
                    self._subscriptions.remove(sub)
            elif isinstance(pattern, str) and handler is None:
                self._subscriptions = [s for s in self._subscriptions if s[0] != pattern]
        return removed

    def cleanup(self) -> None:
        """Автоматически снять все подписки, зарегистрированные модулем."""
        from backend.core.bus import event_bus
        for pattern, handler in list(self._subscriptions):
            event_bus.unsubscribe(pattern, handler)
        self._subscriptions.clear()


_MODULE_EVENTS: dict[str, ModuleEvents] = {}


def get_module_events(module_id: str) -> ModuleEvents:
    """Получить или создать экземпляр ModuleEvents для данного module_id."""
    if module_id not in _MODULE_EVENTS:
        _MODULE_EVENTS[module_id] = ModuleEvents(module_id)
    return _MODULE_EVENTS[module_id]


def cleanup_module_events(module_id: str) -> None:
    """Очистить подписки модуля при остановке/отключении/выгрузке."""
    if module_id in _MODULE_EVENTS:
        _MODULE_EVENTS[module_id].cleanup()
        del _MODULE_EVENTS[module_id]


class ModuleScheduler:
    """Управление планированием фоновых задач модуля."""

    def __init__(self, module_id: str) -> None:
        self.module_id = module_id

    def every(
        self,
        seconds: float,
        fn: Callable[[], Any | Awaitable[Any]],
        name: str | None = None,
    ) -> str:
        """Запланировать периодическую задачу модуля каждые `seconds` секунд."""
        from backend.core.scheduler import scheduler
        return scheduler.every(seconds, fn, module_id=self.module_id, name=name)

    def cron(
        self,
        expr: str,
        fn: Callable[[], Any | Awaitable[Any]],
        name: str | None = None,
    ) -> str:
        """Запланировать задачу по cron-выражению для модуля."""
        from backend.core.scheduler import scheduler
        return scheduler.cron(expr, fn, module_id=self.module_id, name=name)

    def once(
        self,
        delay: float,
        fn: Callable[[], Any | Awaitable[Any]],
        name: str | None = None,
    ) -> str:
        """Запланировать однократную задачу для модуля через `delay` секунд."""
        from backend.core.scheduler import scheduler
        return scheduler.once(delay, fn, module_id=self.module_id, name=name)

    def cancel(self, job_id: str) -> bool:
        """Отменить конкретную задачу модуля по ее job_id."""
        from backend.core.scheduler import scheduler
        return scheduler.cancel_job(job_id)

    def cancel_all(self) -> int:
        """Отменить все фоновые задачи данного модуля."""
        from backend.core.scheduler import scheduler
        return scheduler.cancel_module_jobs(self.module_id)


def cleanup_module_scheduler(module_id: str) -> int:
    """Снять все запланированные задачи модуля при его остановке/отключении/выгрузке."""
    from backend.core.scheduler import scheduler
    return scheduler.cancel_module_jobs(module_id)


@dataclass(frozen=True)
class ModuleContext:
    """Контекст, передаваемый модулю при инициализации.

    Содержит всё, что нужно модулю для регистрации роутеров,
    сервисов и доступа к своей конфигурации и изолированному хранилищу.
    """
    module_id: str
    root: Path
    manifest: dict[str, Any] = field(default_factory=dict)
    parent_module_id: str | None = None
    is_submodule: bool = False

    @property
    def events(self) -> ModuleEvents:
        """Получить шину событий для данного модуля."""
        return get_module_events(self.module_id)

    @property
    def scheduler(self) -> ModuleScheduler:
        """Получить планировщик фоновых задач для данного модуля."""
        return ModuleScheduler(self.module_id)

    @property
    def logger(self) -> logging.Logger:
        """Получить изолированный логгер для модуля."""
        return logging.getLogger(f"nms.plugin.{self.module_id}")

    def get_db(self) -> sqlite3.Connection:
        """Получить подключение к единой базе данных SQLite (nms.db)."""
        from backend.core.database import get_db_connection
        return get_db_connection()

    def get_table_prefix(self) -> str:
        """Получить стандартный префикс таблиц модуля (mod_<module_id>_)."""
        clean_id = self.module_id.replace("-", "_").replace(".", "_")
        return f"mod_{clean_id}_"

    def create_table(self, table_name: str, schema: dict[str, str] | str) -> None:
        """Создать таблицу модуля в nms.db с автоматической подстановкой префикса mod_<module_id>_.

        :param table_name: Имя таблицы без префикса (например, 'devices')
        :param schema: Словарь {колонка: тип_и_ограничения} или DDL-строка определения полей
        """
        full_name = f"{self.get_table_prefix()}{table_name}"
        if isinstance(schema, dict):
            cols_def = ", ".join(f"{col} {definition}" for col, definition in schema.items())
            sql = f"CREATE TABLE IF NOT EXISTS {full_name} ({cols_def});"
        else:
            sql = f"CREATE TABLE IF NOT EXISTS {full_name} ({schema.strip()});"

        with self.get_db() as conn:
            conn.execute(sql)

    async def create_table_async(self, table_name: str, schema: dict[str, str] | str) -> None:
        """Асинхронная обертка для создания таблицы без блокировки Event Loop."""
        import asyncio
        await asyncio.to_thread(self.create_table, table_name, schema)

    async def execute_sql_async(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Выполнить SQL-запрос асинхронно и вернуть список словарей строк."""
        import asyncio

        def _worker():
            with self.get_db() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(sql, params)
                if sql.strip().upper().startswith("SELECT"):
                    return [dict(row) for row in cursor.fetchall()]
                conn.commit()
                return []

        return await asyncio.to_thread(_worker)

    async def add_column_if_not_exists(self, table_name: str, column_name: str, column_type: str) -> None:
        """Легкая миграция: добавить колонку в таблицу модуля, если она еще не существует."""
        import asyncio

        def _worker():
            full_name = f"{self.get_table_prefix()}{table_name}"
            with self.get_db() as conn:
                cursor = conn.execute(f"PRAGMA table_info({full_name})")
                existing_cols = [row[1] for row in cursor.fetchall()]
                if column_name not in existing_cols:
                    conn.execute(f"ALTER TABLE {full_name} ADD COLUMN {column_name} {column_type};")
                    conn.commit()

        await asyncio.to_thread(_worker)



    def get_data_dir(self) -> Path:
        """Получить путь к изолированной директории данных модуля."""
        clean_id = self.module_id.replace("/", "_").replace("\\", "_")
        # project_root / backend / data / modules / <module_id>
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        data_dir = project_root / "backend" / "data" / "modules" / clean_id
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def get_cache_dir(self) -> Path:
        """Получить путь к изолированной директории кэша модуля."""
        clean_id = self.module_id.replace("/", "_").replace("\\", "_")
        # project_root / backend / cache / modules / <module_id>
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        cache_dir = project_root / "backend" / "cache" / "modules" / clean_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def ensure_safe_path(self, target_path: Path | str) -> Path:
        """Проверить, что целевой путь находится строго внутри дата-директории модуля (песочница)."""
        resolved = Path(target_path).resolve()
        data_dir = self.get_data_dir().resolve()
        cache_dir = self.get_cache_dir().resolve()
        root_dir = self.root.resolve()

        if not (resolved.is_relative_to(data_dir) or resolved.is_relative_to(cache_dir) or resolved.is_relative_to(root_dir)):
            raise PermissionDeniedError(f"Access denied: Path {resolved} is outside module sandbox directories.")
        return resolved

    def is_module_active(self, target_module_id: str) -> bool:
        """Проверить, зарегистрирован ли и включен ли указанный модуль."""
        from backend.core.plugin.registry import is_module_active
        return is_module_active(target_module_id)

    def get_module_instance(self, target_module_id: str) -> Any | None:
        """Получить экземпляр активного модуля (если он загружен)."""
        from backend.core.plugin.registry import get_instance
        return get_instance(target_module_id)

    def notify(
        self,
        user_id: str,
        title: str,
        body: str = "",
        severity: str = "info",
        entity_id: str | None = None,
    ) -> dict[str, Any]:
        """Отправить базовое уведомление пользователю от имени текущего модуля."""
        from backend.core.notify import notify as core_notify
        return core_notify(
            user_id=user_id,
            title=title,
            body=body,
            severity=severity,
            entity_id=entity_id,
            module_id=self.module_id,
        )


def cleanup_module_notifications(module_id: str) -> int:
    """Удалить все уведомления модуля при его uninstall/очистке."""
    from backend.core.notify import cleanup_module_notifications as core_cleanup
    return core_cleanup(module_id)







