"""backend/core/scheduler.py — asyncio-планировщик фоновых задач модулей и ядра."""
from __future__ import annotations

import asyncio
import inspect
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

_log = logging.getLogger("nms.scheduler")


def _parse_cron_field(field_str: str, min_val: int, max_val: int) -> set[int]:
    """Распарсить отдельное поле cron-выражения (*, */N, N, N-M, N-M/S, N,M) в множество допустимых значений."""
    result: set[int] = set()
    for sub in field_str.split(","):
        sub = sub.strip()
        if not sub:
            raise ValueError(f"Empty item in cron field '{field_str}'")

        step = 1
        if "/" in sub:
            parts = sub.split("/", 1)
            sub = parts[0]
            try:
                step = int(parts[1])
            except ValueError as exc:
                raise ValueError(f"Invalid step in cron field '{field_str}'") from exc
            if step <= 0:
                raise ValueError(f"Step must be positive in cron field '{field_str}'")

        if sub == "*":
            result.update(range(min_val, max_val + 1, step))
        elif "-" in sub:
            try:
                start_str, end_str = sub.split("-", 1)
                start, end = int(start_str), int(end_str)
            except ValueError as exc:
                raise ValueError(f"Invalid range in cron field '{sub}'") from exc
            if not (min_val <= start <= end <= max_val):
                raise ValueError(
                    f"Range '{sub}' out of bounds [{min_val}-{max_val}]"
                )
            result.update(range(start, end + 1, step))
        else:
            try:
                val = int(sub)
            except ValueError as exc:
                raise ValueError(f"Invalid value in cron field '{sub}'") from exc
            if not (min_val <= val <= max_val):
                raise ValueError(
                    f"Value '{val}' out of bounds [{min_val}-{max_val}] in cron field '{field_str}'"
                )
            if step > 1:
                result.update(range(val, max_val + 1, step))
            else:
                result.add(val)
    return result


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
    dom_restricted = parts[2] != "*"
    dow_restricted = parts[4] != "*"
    # 0 и 7 в crontab означают воскресенье
    if 7 in dow_set:
        dow_set.add(0)
    if 0 in dow_set:
        dow_set.add(7)

    dt = base_time or datetime.now()
    # Сбрасываем секунды и микросекунды, переходим к следующей минуте
    dt = dt.replace(second=0, microsecond=0) + timedelta(minutes=1)

    # Ищем подходящую минуту с оптимизированными прыжками по месяцам, дням, часам и минутам
    for _ in range(525600):
        if dt.month not in month_set:
            if dt.month == 12:
                dt = datetime(dt.year + 1, 1, 1, 0, 0)
            else:
                dt = datetime(dt.year, dt.month + 1, 1, 0, 0)
            continue

        cron_dow = (dt.weekday() + 1) % 7
        dom_match = dt.day in dom_set
        dow_match = cron_dow in dow_set or dt.isoweekday() in dow_set
        day_match = (dom_match or dow_match) if (dom_restricted and dow_restricted) else (dom_match and dow_match)

        if not day_match:
            dt = (dt + timedelta(days=1)).replace(hour=0, minute=0)
            continue

        if dt.hour not in hour_set:
            dt = (dt + timedelta(hours=1)).replace(minute=0)
            continue

        matching_mins = [m for m in min_set if m >= dt.minute]
        if matching_mins:
            return dt.replace(minute=min(matching_mins))

        dt = (dt + timedelta(hours=1)).replace(minute=0)

    raise ValueError(f"Cron expression '{cron_expr}' never matches within one year.")


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
        tasks = [job.task for job in self._jobs.values() if job.task and not job.task.done()]
        job_ids = list(self._jobs.keys())
        for job_id in job_ids:
            self.cancel_job(job_id)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
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
        delay = max(delay, 0)
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
            if inspect.iscoroutinefunction(job.fn) or inspect.iscoroutinefunction(
                getattr(job.fn, "__call__", None)
            ):
                await job.fn()
            else:
                res = await asyncio.to_thread(job.fn)
                if inspect.isawaitable(res):
                    await res
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
            interval = job.seconds or 1.0
            next_run = time.monotonic() + interval
            while self._running and not job.is_cancelled:
                sleep_sec = next_run - time.monotonic()
                if sleep_sec > 0:
                    await asyncio.sleep(sleep_sec)
                next_run = max(next_run + interval, time.monotonic())
                if self._running and not job.is_cancelled:
                    await self._safe_execute(job)
        except asyncio.CancelledError:
            pass

    async def _run_cron_loop(self, job: ScheduledJob) -> None:
        try:
            last_target: datetime | None = None
            while self._running and not job.is_cancelled:
                if not job.cron_expr:
                    break
                now = datetime.now()
                if last_target and last_target < now - timedelta(minutes=2):
                    last_target = None
                next_time = get_next_cron_time(job.cron_expr, base_time=last_target)
                last_target = next_time
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
