"""backend/core/scheduler.py — asyncio-планировщик фоновых задач модулей и ядра."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Awaitable

_log = logging.getLogger("nms.scheduler")


def _parse_cron_field(field_str: str, min_val: int, max_val: int) -> set[int]:
    """Распарсить отдельное поле cron-выражения (*, */N, N, N-M, N,M) в множество допустимых значений."""
    result: set[int] = set()
    for sub in field_str.split(","):
        sub = sub.strip()
        if not sub:
            continue
        if sub == "*":
            result.update(range(min_val, max_val + 1))
        elif sub.startswith("*/"):
            try:
                step = int(sub[2:])
                if step > 0:
                    result.update(range(min_val, max_val + 1, step))
            except ValueError:
                pass
        elif "-" in sub:
            try:
                parts = sub.split("-")
                start, end = int(parts[0]), int(parts[1])
                if start <= end:
                    result.update(range(max(min_val, start), min(max_val, end) + 1))
            except (ValueError, IndexError):
                pass
        else:
            try:
                val = int(sub)
                if min_val <= val <= max_val:
                    result.add(val)
            except ValueError:
                pass
    return result or set(range(min_val, max_val + 1))


_CRON_MACROS = {
    "@hourly": "0 * * * *",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@weekly": "0 0 * * 0",
    "@monthly": "0 0 1 * *",
}


def get_next_cron_time(cron_expr: str, base_time: datetime | None = None) -> datetime:
    """Вычислить следующий datetime срабатывания 5-полевого cron-выражения (min hour dom month dow)."""
    cron_expr = _CRON_MACROS.get(cron_expr.strip().lower(), cron_expr.strip())
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression '{cron_expr}'. Expected 5 fields.")

    min_set = _parse_cron_field(parts[0], 0, 59)
    hour_set = _parse_cron_field(parts[1], 0, 23)
    dom_set = _parse_cron_field(parts[2], 1, 31)
    month_set = _parse_cron_field(parts[3], 1, 12)
    dow_set = _parse_cron_field(parts[4], 0, 7)
    # 0 и 7 в crontab означают воскресенье
    if 7 in dow_set:
        dow_set.add(0)
    if 0 in dow_set:
        dow_set.add(7)

    dt = base_time or datetime.now()
    # Сбрасываем секунды и микросекунды, переходим к следующей минуте
    dt = dt.replace(second=0, microsecond=0) + timedelta(minutes=1)

    # Ищем подходящую минуту (ограничение 1 год = 525,600 минут)
    for _ in range(525600):
        # В datetime weekday(): 0=Mon..6=Sun. В crontab: 0=Sun, 1=Mon..6=Sat, 7=Sun.
        # Перевод в cron dow: Mon=1..Sat=6, Sun=0/7
        cron_dow = (dt.weekday() + 1) % 7

        if (
            dt.minute in min_set
            and dt.hour in hour_set
            and dt.day in dom_set
            and dt.month in month_set
            and (cron_dow in dow_set or dt.isoweekday() in dow_set)
        ):
            return dt
        dt += timedelta(minutes=1)

    return dt


@dataclass
class ScheduledJob:
    """Метаданные запущенной задачи планировщика."""
    job_id: str
    job_type: str  # "every", "cron", "once"
    fn: Callable[[], Any | Awaitable[Any]]
    module_id: str | None = None
    name: str | None = None
    seconds: float | None = None
    cron_expr: str | None = None
    delay: float | None = None
    task: asyncio.Task | None = None
    is_cancelled: bool = False
    runs_count: int = 0
    error_count: int = 0
    last_run: float | None = None
    last_error: str | None = None


class AsyncScheduler:
    """Центральный asyncio-планировщик задач модулей и ядра."""

    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}
        self._module_jobs: dict[str, set[str]] = {}
        self._running: bool = False

    def start(self) -> None:
        """Запустить планировщик и активировать все зарегистрированные задачи."""
        self._running = True
        for job in list(self._jobs.values()):
            if not job.is_cancelled and (job.task is None or job.task.done()):
                self._start_job_task(job)
        _log.info("AsyncScheduler started.")

    async def stop(self) -> None:
        """Остановить планировщик и отменить все текущие задачи."""
        self._running = False
        job_ids = list(self._jobs.keys())
        for job_id in job_ids:
            self.cancel_job(job_id)
        _log.info("AsyncScheduler stopped.")

    def cancel_job(self, job_id: str) -> bool:
        """Отменить конкретную задачу по ее job_id."""
        job = self._jobs.pop(job_id, None)
        if not job:
            return False

        job.is_cancelled = True
        if job.module_id and job.module_id in self._module_jobs:
            self._module_jobs[job.module_id].discard(job_id)
            if not self._module_jobs[job.module_id]:
                del self._module_jobs[job.module_id]

        if job.task and not job.task.done():
            job.task.cancel()
        return True

    def cancel_module_jobs(self, module_id: str) -> int:
        """Отменить и удалить все задачи, принадлежащие данному module_id."""
        job_ids = list(self._module_jobs.get(module_id, set()))
        count = 0
        for job_id in job_ids:
            if self.cancel_job(job_id):
                count += 1
        _log.info("Cancelled %d scheduled jobs for module %s", count, module_id)
        return count

    def every(
        self,
        seconds: float,
        fn: Callable[[], Any | Awaitable[Any]],
        module_id: str | None = None,
        name: str | None = None,
    ) -> str:
        """Запланировать периодический запуск задачи каждые `seconds` секунд."""
        if seconds <= 0:
            raise ValueError("Interval `seconds` must be greater than 0.")
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        job = ScheduledJob(
            job_id=job_id,
            job_type="every",
            fn=fn,
            module_id=module_id,
            name=name or getattr(fn, "__name__", "every_job"),
            seconds=float(seconds),
        )
        self._register_job(job)
        return job_id

    def cron(
        self,
        expr: str,
        fn: Callable[[], Any | Awaitable[Any]],
        module_id: str | None = None,
        name: str | None = None,
    ) -> str:
        """Запланировать запуск задачи по 5-элементному cron-выражению."""
        # Валидация cron выражения на этапе регистрации
        get_next_cron_time(expr)
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        job = ScheduledJob(
            job_id=job_id,
            job_type="cron",
            fn=fn,
            module_id=module_id,
            name=name or getattr(fn, "__name__", "cron_job"),
            cron_expr=expr,
        )
        self._register_job(job)
        return job_id

    def once(
        self,
        delay: float,
        fn: Callable[[], Any | Awaitable[Any]],
        module_id: str | None = None,
        name: str | None = None,
    ) -> str:
        """Запланировать однократный запуск задачи через `delay` секунд."""
        if delay < 0:
            delay = 0
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        job = ScheduledJob(
            job_id=job_id,
            job_type="once",
            fn=fn,
            module_id=module_id,
            name=name or getattr(fn, "__name__", "once_job"),
            delay=float(delay),
        )
        self._register_job(job)
        return job_id

    def get_jobs(self, module_id: str | None = None) -> list[dict[str, Any]]:
        """Получить список зарегистрированных задач с состоянием."""
        result = []
        for job in self._jobs.values():
            if module_id is not None and job.module_id != module_id:
                continue
            result.append(
                {
                    "job_id": job.job_id,
                    "job_type": job.job_type,
                    "name": job.name,
                    "module_id": job.module_id,
                    "seconds": job.seconds,
                    "cron_expr": job.cron_expr,
                    "delay": job.delay,
                    "runs_count": job.runs_count,
                    "error_count": job.error_count,
                    "last_run": job.last_run,
                    "last_error": job.last_error,
                    "is_running": job.task is not None and not job.task.done(),
                }
            )
        return result

    def _register_job(self, job: ScheduledJob) -> None:
        self._jobs[job.job_id] = job
        if job.module_id:
            if job.module_id not in self._module_jobs:
                self._module_jobs[job.module_id] = set()
            self._module_jobs[job.module_id].add(job.job_id)

        if self._running:
            self._start_job_task(job)

    def _start_job_task(self, job: ScheduledJob) -> None:
        try:
            loop = asyncio.get_running_loop()
            if job.job_type == "every":
                job.task = loop.create_task(self._run_every_loop(job))
            elif job.job_type == "cron":
                job.task = loop.create_task(self._run_cron_loop(job))
            elif job.job_type == "once":
                job.task = loop.create_task(self._run_once_loop(job))
        except RuntimeError:
            # Event loop еще не запущен; таска запустится при вызове start()
            pass

    async def _safe_execute(self, job: ScheduledJob) -> None:
        """Изолированное выполнение функции задачи с обработкой ошибок."""
        try:
            job.last_run = time.time()
            job.runs_count += 1
            if asyncio.iscoroutinefunction(job.fn):
                await job.fn()
            else:
                job.fn()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            job.error_count += 1
            job.last_error = str(exc)
            _log.error(
                "Error executing scheduled job '%s' (id=%s, module=%s): %s",
                job.name,
                job.job_id,
                job.module_id,
                exc,
                exc_info=True,
            )

    async def _run_every_loop(self, job: ScheduledJob) -> None:
        try:
            while self._running and not job.is_cancelled:
                await asyncio.sleep(job.seconds or 1.0)
                if self._running and not job.is_cancelled:
                    await self._safe_execute(job)
        except asyncio.CancelledError:
            pass

    async def _run_cron_loop(self, job: ScheduledJob) -> None:
        try:
            while self._running and not job.is_cancelled:
                if not job.cron_expr:
                    break
                next_time = get_next_cron_time(job.cron_expr)
                now = datetime.now()
                sleep_sec = (next_time - now).total_seconds()
                if sleep_sec > 0:
                    await asyncio.sleep(sleep_sec)
                if self._running and not job.is_cancelled:
                    await self._safe_execute(job)
        except asyncio.CancelledError:
            pass

    async def _run_once_loop(self, job: ScheduledJob) -> None:
        try:
            if job.delay and job.delay > 0:
                await asyncio.sleep(job.delay)
            if self._running and not job.is_cancelled:
                await self._safe_execute(job)
        except asyncio.CancelledError:
            pass
        finally:
            self.cancel_job(job.job_id)


# Глобальный экземпляр планировщика для использования в приложении
scheduler = AsyncScheduler()
