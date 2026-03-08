# Конвейер обработки потоков с fallback-логикой
import logging
import sys
import os
import asyncio
from typing import Optional, Any
from pathlib import Path

from .contract import IStreamBackend
from .router import StreamRouter
from .types import StreamTask, StreamResult, StreamProtocol, PreviewFormat, OutputType
from .exceptions import StreamPipelineError, NoSuitableBackendError

logger = logging.getLogger(__name__)


class StreamPipeline:
    """Конвейер обработки потоков.

    Координирует выполнение задач через роутер,
    обеспечивая fallback-переключение при сбоях.
    """

    def __init__(self, router: StreamRouter, max_retries: int = 2) -> None:
        self._router = router
        self._max_retries = max_retries

    async def execute_stream(self, task: StreamTask) -> StreamResult:
        """Запуск стриминга с автоматическим fallback.

        Если основной бэкенд падает, пробуем следующий по приоритету.
        """
        # --- 1. Прямой проброс (Direct Pass-through) ---
        # Если можно отдать ссылку напрямую и бэкенд не выбран принудительно
        if not task.forced_backend and self._router.can_direct_pass(task):
            # Если AUTO - резолвим в зависимости от протокола
            resolved_type = task.output_type
            if resolved_type == OutputType.AUTO:
                if task.input_protocol == StreamProtocol.HLS:
                    resolved_type = OutputType.HLS
                else:
                    resolved_type = OutputType.HTTP
                
            logger.info(f"Direct pass-through: {task.input_url} -> {resolved_type.name}")
            return StreamResult(
                task_id=f"direct-{task.task_id or 'none'}",
                success=True,
                backend_used="direct",
                output_type=resolved_type,
                output_url=task.input_url,
                metadata={"type": "direct_pass"}
            )

        # --- 2. Стандартный путь через бэкенды ---
        last_error: Optional[str] = None
        excluded_backends: set[str] = set()

        for attempt in range(self._max_retries + 1):
            try:
                backend = await self._router.select_stream_backend(task, excluded=excluded_backends)
                logger.info(
                    f"[Попытка {attempt + 1}] Стриминг через '{backend.backend_id}': "
                    f"{task.input_url}"
                )
                result = await backend.start_stream(task)
                if result.success:
                    # Проставляем реально используемый тип (он мог быть разрешен из AUTO)
                    if not result.output_type:
                        result.output_type = task.output_type
                    return result
                
                last_error = result.error
                excluded_backends.add(backend.backend_id)

            except NoSuitableBackendError as e:
                last_error = str(e)
                break

            except Exception as e:
                last_error = str(e)
                excluded_backends.add(backend.backend_id) if 'backend' in locals() else None
                logger.warning(
                    f"Бэкенд сбой (попытка {attempt + 1}): {e}",
                    exc_info=True
                )

            # Исключаем неудачный бэкенд для следующей попытки
            if task.forced_backend:
                break  # Ручной режим: повторов не делаем

        if last_error and "Нет доступного бэкенда" in last_error:
            raise NoSuitableBackendError(last_error)

        raise StreamPipelineError(
            f"Не удалось запустить стриминг после {self._max_retries + 1} попыток. "
            f"Последняя ошибка: {last_error}"
        )

    async def execute_preview(
        self,
        url: str,
        protocol: StreamProtocol,
        fmt: PreviewFormat = PreviewFormat.JPEG,
        width: int = 640,
        quality: int = 75,
        forced_backend: Optional[str] = None,
        max_retries_override: Optional[int] = None,
        timeout_override: int = 15,
    ) -> tuple[bytes, PreviewFormat]:
        """Генерация превью с опциональным fallback.
        
        Returns:
            Кортеж (бинарные_данные, результирующий_формат)
        """
        last_error: Optional[str] = None
        excluded_backends: set[str] = set()
        
        retries = max_retries_override if max_retries_override is not None else self._max_retries

        for attempt in range(retries + 1):
            try:
                backend, resolved_fmt = await self._router.select_preview_backend(
                    protocol=protocol,
                    fmt=fmt,
                    forced_backend=forced_backend,
                    excluded=excluded_backends,
                )
                logger.info(
                    f"[Попытка {attempt + 1}] Превью через '{backend.backend_id}' (изолированно, формат {resolved_fmt.value}): {url}"
                )
                # Выполняем генерацию в отдельном процессе через универсальный CLI
                data = await self._generate_isolated(
                    backend_id=backend.backend_id,
                    url=url,
                    protocol=protocol,
                    fmt=resolved_fmt,
                    width=width,
                    quality=quality,
                    timeout=timeout_override
                )
                if data:
                    return data, resolved_fmt
                
                last_error = "Бэкенд вернул пустой результат"
                excluded_backends.add(backend.backend_id)

            except NoSuitableBackendError as e:
                last_error = str(e)
                break

            except Exception as e:
                last_error = str(e)
                excluded_backends.add(backend.backend_id) if 'backend' in locals() else None
                logger.warning(
                    f"Ошибка генерации превью (попытка {attempt + 1}): {e}"
                )

            if forced_backend:
                break

        raise StreamPipelineError(
            f"Не удалось сгенерировать превью. Последняя ошибка: {last_error}"
        )

    async def _generate_isolated(
        self,
        backend_id: str,
        url: str,
        protocol: StreamProtocol,
        fmt: PreviewFormat,
        width: int,
        quality: int,
        timeout: int = 15
    ) -> Optional[bytes]:
        """Запуск генерации превью в изолированном процессе."""
        # Путь к скрипту в директории scripts/ относительно core/
        cli_path = Path(__file__).parent.parent / "scripts" / "preview_cli.py"
        
        cmd = [
            sys.executable,
            str(cli_path),
            "--backend", backend_id,
            "--url", url,
            "--protocol", protocol.value,
            "--format", fmt.value,
            "--width", str(width),
            "--quality", str(quality),
            "--timeout", str(timeout)
        ]

        process = None
        try:
            # Запускаем процесс
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONPATH": os.getcwd()}
            )

            # Ожидаем завершения с небольшим запасом по времени (таймаут реализован внутри бэкенда)
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout + 5)
            except asyncio.TimeoutError:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
                logger.warning(f"Процесс preview_cli ({backend_id}) был убит по системному таймауту")
                return None

            if stderr:
                # Передаем логи из подпроцесса в основной логгер
                for line in stderr.decode().splitlines():
                    if "INFO" in line:
                         logger.debug(f"[CLI:{backend_id}] {line}")
                    else:
                         logger.warning(f"[CLI:{backend_id}] {line}")

            if process.returncode == 0 and stdout:
                return stdout
                
        except asyncio.CancelledError:
            if process and process.returncode is None:
                process.kill()
                await process.wait()
            raise
        except Exception as e:
            logger.error(f"Ошибка при запуске изолированного превью: {e}")
        finally:
            if process and process.returncode is None:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
            
        return None
