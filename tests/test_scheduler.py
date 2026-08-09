"""tests/test_scheduler.py — модульные тесты для AsyncScheduler и ctx.scheduler."""
import asyncio
from datetime import datetime
from pathlib import Path
import pytest

from backend.core.scheduler import AsyncScheduler, get_next_cron_time
from backend.core.plugin.context import ModuleContext, cleanup_module_scheduler


@pytest.mark.anyio
async def test_every_periodic_execution():
    scheduler = AsyncScheduler()
    scheduler.start()

    counter = 0

    async def increment():
        nonlocal counter
        counter += 1

    job_id = scheduler.every(0.05, increment, module_id="test_every")
    assert job_id.startswith("job_")

    await asyncio.sleep(0.18)
    assert counter >= 3

    scheduler.cancel_job(job_id)
    await scheduler.stop()


@pytest.mark.anyio
async def test_once_execution():
    scheduler = AsyncScheduler()
    scheduler.start()

    executed = False

    def flag():
        nonlocal executed
        executed = True

    job_id = scheduler.once(0.05, flag, module_id="test_once")
    assert job_id in [j["job_id"] for j in scheduler.get_jobs("test_once")]

    await asyncio.sleep(0.15)
    assert executed is True
    # Задача должна быть автоматически удалена после исполнения
    assert len(scheduler.get_jobs("test_once")) == 0

    await scheduler.stop()


def test_cron_parsing_and_validation():
    now = datetime(2026, 8, 9, 12, 0, 0)
    next_t = get_next_cron_time("* * * * *", base_time=now)
    assert next_t == datetime(2026, 8, 9, 12, 1, 0)

    next_hourly = get_next_cron_time("@hourly", base_time=now)
    assert next_hourly == datetime(2026, 8, 9, 13, 0, 0)

    with pytest.raises(ValueError):
        get_next_cron_time("invalid cron expression")


def test_cron_rejects_out_of_range_values():
    with pytest.raises(ValueError):
        get_next_cron_time("99 * * * *")
    with pytest.raises(ValueError):
        get_next_cron_time("* 25 * * *")
    with pytest.raises(ValueError):
        get_next_cron_time("*/0 * * * *")
    with pytest.raises(ValueError):
        get_next_cron_time("10-5 * * * *")


def test_cron_never_matching_raises():
    with pytest.raises(ValueError):
        get_next_cron_time("0 0 30 2 *")


def test_cron_dom_dow_or_semantics():
    # Если ограничены и день месяца, и день недели — срабатывание по любому из них
    base = datetime(2026, 8, 9, 12, 0, 0)  # воскресенье
    next_t = get_next_cron_time("0 0 13 * 5", base_time=base)
    # 13-е число (четверг 2026-08-13) наступает раньше ближайшей пятницы 14-го
    assert next_t == datetime(2026, 8, 13, 0, 0, 0)


@pytest.mark.anyio
async def test_cancel_module_jobs():
    scheduler = AsyncScheduler()
    scheduler.start()

    scheduler.every(10, lambda: None, module_id="mod1", name="j1")
    scheduler.every(10, lambda: None, module_id="mod1", name="j2")
    scheduler.every(10, lambda: None, module_id="mod2", name="j3")

    assert len(scheduler.get_jobs("mod1")) == 2
    assert len(scheduler.get_jobs("mod2")) == 1

    cancelled_count = scheduler.cancel_module_jobs("mod1")
    assert cancelled_count == 2
    assert len(scheduler.get_jobs("mod1")) == 0
    assert len(scheduler.get_jobs("mod2")) == 1

    await scheduler.stop()


@pytest.mark.anyio
async def test_error_isolation():
    scheduler = AsyncScheduler()
    scheduler.start()

    healthy_count = 0

    def faulty_job():
        raise RuntimeError("Fatal error inside task")

    def healthy_job():
        nonlocal healthy_count
        healthy_count += 1

    job_faulty = scheduler.every(0.04, faulty_job, module_id="err_mod")
    job_healthy = scheduler.every(0.04, healthy_job, module_id="err_mod")

    await asyncio.sleep(0.15)

    jobs = scheduler.get_jobs("err_mod")
    faulty_meta = next(j for j in jobs if j["job_id"] == job_faulty)

    # Ошибка должна быть зафиксирована в метаданных, но планировщик и вторая задача работают
    assert faulty_meta["error_count"] > 0
    assert "Fatal error inside task" in faulty_meta["last_error"]
    assert healthy_count >= 2

    await scheduler.stop()


@pytest.mark.anyio
async def test_module_context_scheduler_integration():
    from backend.core.scheduler import scheduler as global_scheduler

    global_scheduler.start()

    ctx = ModuleContext(module_id="test_ctx_mod", root=Path("/tmp"))
    run_count = 0

    def task_fn():
        nonlocal run_count
        run_count += 1

    job_id = ctx.scheduler.every(0.05, task_fn)
    assert job_id.startswith("job_")

    await asyncio.sleep(0.12)
    assert run_count >= 2

    # При выгрузке модуля задачи отменяются
    cancelled = cleanup_module_scheduler("test_ctx_mod")
    assert cancelled == 1
    assert len(global_scheduler.get_jobs("test_ctx_mod")) == 0

    await global_scheduler.stop()


def test_cron_range_with_step():
    now = datetime(2026, 8, 9, 12, 0, 0)
    # Минуты 0-10 с шагом 2
    next_t = get_next_cron_time("0-10/2 * * * *", base_time=now)
    assert next_t == datetime(2026, 8, 9, 12, 2, 0)


@pytest.mark.anyio
async def test_partial_async_function_execution():
    from functools import partial

    scheduler = AsyncScheduler()
    scheduler.start()

    executed = False

    async def worker(param: str):
        nonlocal executed
        if param == "ok":
            executed = True

    partial_fn = partial(worker, "ok")
    job_id = scheduler.once(0.01, partial_fn)

    await asyncio.sleep(0.05)
    assert executed is True
    await scheduler.stop()


def test_cron_single_val_with_step():
    now = datetime(2026, 8, 9, 12, 0, 0)
    # Начиная с 5-й минуты каждые 15 минут (5, 20, 35, 50)
    next_t = get_next_cron_time("5/15 * * * *", base_time=now)
    assert next_t == datetime(2026, 8, 9, 12, 5, 0)

    now_at_5 = datetime(2026, 8, 9, 12, 5, 0)
    next_t2 = get_next_cron_time("5/15 * * * *", base_time=now_at_5)
    assert next_t2 == datetime(2026, 8, 9, 12, 20, 0)


@pytest.mark.anyio
async def test_lambda_returning_coroutine():
    scheduler = AsyncScheduler()
    scheduler.start()

    executed = False

    async def async_worker():
        await asyncio.sleep(0.001)
        nonlocal executed
        executed = True

    # Синхронная лямбда, возвращающая сопрограмму
    job_id = scheduler.once(0.01, lambda: async_worker())

    await asyncio.sleep(0.05)
    assert executed is True
    await scheduler.stop()



