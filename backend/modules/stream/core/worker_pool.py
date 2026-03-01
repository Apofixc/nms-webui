# Пул воркеров для управления процессами стриминга
import asyncio
import logging
import uuid
import os
import shutil
import glob
from dataclasses import dataclass, field
from typing import Dict, Optional

from .types import StreamTask, StreamResult

logger = logging.getLogger(__name__)


@dataclass
class WorkerInfo:
    """Информация об активном воркере."""
    worker_id: str
    task: StreamTask
    backend_id: str
    process: Optional[asyncio.subprocess.Process] = None
    output_url: Optional[str] = None
    started_at: float = 0.0


class WorkerPool:
    """Пул воркеров для изоляции процессов стриминга.

    Контролирует количество одновременно запущенных процессов,
    управляет их жизненным циклом и обеспечивает корректное завершение.
    """

    def __init__(self, max_workers: int = 4, timeout: int = 30) -> None:
        self._max_workers = max_workers
        self._timeout = timeout
        self._workers: Dict[str, WorkerInfo] = {}
        self._semaphore = asyncio.Semaphore(max_workers)

    @property
    def active_count(self) -> int:
        """Количество активных воркеров."""
        return len(self._workers)

    @property
    def max_workers(self) -> int:
        """Максимальный размер пула."""
        return self._max_workers

    async def acquire(self, task: StreamTask, backend_id: str) -> str:
        """Захват слота в пуле для новой задачи.

        Ожидает освобождения семафора, если пул заполнен.

        Returns:
            worker_id: Уникальный идентификатор воркера.
        """
        await self._semaphore.acquire()
        worker_id = str(uuid.uuid4())[:8]
        task.task_id = worker_id

        self._workers[worker_id] = WorkerInfo(
            worker_id=worker_id,
            task=task,
            backend_id=backend_id,
            started_at=asyncio.get_event_loop().time(),
        )

        logger.info(
            f"Воркер '{worker_id}' захвачен для '{backend_id}' "
            f"({self.active_count}/{self._max_workers})"
        )
        return worker_id

    async def release(self, worker_id: str) -> None:
        """Освобождение слота в пуле с очисткой ресурсов и временных файлов."""
        worker = self._workers.pop(worker_id, None)
        if worker:
            # 1. Остановка процесса
            if worker.process and worker.process.returncode is None:
                worker.process.terminate()
                try:
                    await asyncio.wait_for(worker.process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    worker.process.kill()

            # 2. Очистка временных файлов
            self._cleanup_files(worker_id)
            
            self._semaphore.release()
            logger.info(
                f"Воркер '{worker_id}' освобожден "
                f"({self.active_count}/{self._max_workers})"
            )

    def _cleanup_files(self, worker_id: str):
        """Удаление всех временных файлов, связанных с ID воркера."""
        # Папки HLS в /tmp
        hls_dir = f"/tmp/stream_hls_{worker_id}"
        if os.path.exists(hls_dir):
            try:
                shutil.rmtree(hls_dir)
            except Exception as e:
                logger.warning(f"Ошибка удаления HLS директории {hls_dir}: {e}")

        # Файлы потоков в data/streams
        streams_base = "/opt/nms-webui/data/streams"
        
        # Обычные .ts файлы
        ts_file = os.path.join(streams_base, f"{worker_id}.ts")
        if os.path.exists(ts_file):
            try:
                os.remove(ts_file)
            except Exception as e:
                logger.warning(f"Ошибка удаления файла {ts_file}: {e}")

        # Директории pure_proxy
        proxy_dir = os.path.join(streams_base, f"proxy-{worker_id}")
        if os.path.exists(proxy_dir):
            try:
                shutil.rmtree(proxy_dir)
            except Exception as e:
                logger.warning(f"Ошибка удаления proxy директории {proxy_dir}: {e}")

        # Прочие файлы по маске (если бэкенды создают что-то еще с этим ID)
        for pattern in [f"{worker_id}*", f"*{worker_id}*"]:
            for f in glob.glob(os.path.join(streams_base, pattern)):
                try:
                    if os.path.isdir(f):
                        shutil.rmtree(f)
                    else:
                        os.remove(f)
                except:
                    pass

    async def stop_all(self) -> None:
        """Остановка всех активных воркеров."""
        worker_ids = list(self._workers.keys())
        for wid in worker_ids:
            await self.release(wid)
        logger.info("Все воркеры остановлены")

    def get_worker(self, worker_id: str) -> Optional[WorkerInfo]:
        """Получение информации о воркере по ID."""
        return self._workers.get(worker_id)

    def list_workers(self) -> list[dict]:
        """Список всех активных воркеров."""
        return [
            {
                "worker_id": w.worker_id,
                "backend": w.backend_id,
                "input_url": w.task.input_url,
                "started_at": w.started_at,
            }
            for w in self._workers.values()
        ]
