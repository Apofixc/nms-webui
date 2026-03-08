# Базовые классы сессий стриминга.
# Устраняют дублирование логики TS-синхронизации, рассылки чанков
# и дисковой буферизации между субмодулями (builtin_proxy, vlc, astra).

import asyncio
import logging
import os
import time
from typing import List, Optional

from .types import StreamTask, OutputType

logger = logging.getLogger(__name__)


class BaseStreamSession:
    """Базовая сессия стриминга: TS-синхронизация + pub/sub.

    Реализует общую логику, которая повторялась в ProxySession,
    VLCSession и AstraSession:
    - Подписка/отписка клиентов через asyncio.Queue
    - Рассылка чанков подписчикам (drop-oldest при переполнении)
    - Синхронизация по MPEG-TS маркеру (0x47)
    """

    def __init__(self, task_id: str, task: StreamTask):
        self.task_id = task_id
        self.task = task
        self._subscribers: List[asyncio.Queue] = []
        self._synced = False

    # --- Подписка / Отписка ---

    def subscribe(self) -> asyncio.Queue:
        """Создаёт персональную очередь для нового зрителя."""
        queue = asyncio.Queue(maxsize=500)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Убирает зрителя из рассылки."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    # --- Рассылка данных ---

    def dispatch(self, chunk: bytes):
        """Рассылает чанк всем подписчикам (drop-oldest при переполнении)."""
        for q in self._subscribers:
            try:
                if q.full():
                    q.get_nowait()
                q.put_nowait(chunk)
            except Exception:
                pass

    async def process_chunk(self, chunk: bytes):
        """Обработка чанка: TS-синхронизация + рассылка.

        Ищет маркер MPEG-TS (0x47) и пакет с PID 0 (PAT) для начала.
        Если PAT не найден в первых 2МБ, делает фоллбэк на обычный 0x47.
        """
        if not self._synced:
            # Ищем заголовок 0x47
            idx = chunk.find(b'\x47')
            while idx != -1:
                # Проверяем PID
                if len(chunk) > idx + 2:
                    pid = ((chunk[idx + 1] & 0x1F) << 8) | chunk[idx + 2]
                    
                    # Идеальный старт (PAT) или фоллбэк после 2МБ данных
                    if pid == 0 or getattr(self, "_sync_bytes_seen", 0) > 2 * 1024 * 1024:
                        if pid != 0:
                            logger.warning(f"Session {self.task_id}: PAT not found in 2MB, falling back to any 0x47")
                        
                        chunk = chunk[idx:]
                        self._synced = True
                        break
                
                idx = chunk.find(b'\x47', idx + 1)
            
            if not self._synced:
                # Накапливаем счетчик просмотренных байт для фоллбэка
                self._sync_bytes_seen = getattr(self, "_sync_bytes_seen", 0) + len(chunk)
                return
        
        self.dispatch(chunk)

    # --- Завершение ---

    def close(self):
        """Шлёт None (сигнал конца потока) и очищает список подписчиков."""
        for q in self._subscribers:
            try:
                q.put_nowait(None)
            except Exception:
                pass
        self._subscribers.clear()

    def get_temp_dirs(self) -> list[str]:
        """Список временных директорий сессии для очистки модулем.

        Базовая реализация возвращает пустой список.
        Переопределяется в BufferedSession и наследниках.
        """
        return []


class BufferedSession(BaseStreamSession):
    """Сессия с дисковой буферизацией для HLS/HTTP_TS.

    Расширяет BaseStreamSession сегментированной записью на диск.
    Используется builtin_proxy и vlc для хранения TS-сегментов.

    ВАЖНО: Метод close() НЕ удаляет файлы с диска.
    Очисткой временных файлов управляет модуль Stream через get_temp_dirs().
    """

    def __init__(
        self,
        task_id: str,
        task: StreamTask,
        buffer_dir: str = "",
        segment_duration: int = 5,
        max_segments: int = 24,
    ):
        super().__init__(task_id, task)
        self.buffer_dir = buffer_dir
        self.segment_duration = segment_duration
        self.max_segments = max_segments
        self.started_at = time.time()

        # Состояние буферизации
        self.segments: List[str] = []
        self.current_segment_name: Optional[str] = None
        self.buffering_enabled = (
            task.output_type in {OutputType.HTTP_TS, OutputType.HLS}
        )

        # Внутренние переменные записи
        self._current_file = None
        self._seg_idx = 1
        self._seg_start_time = 0.0

    # --- Буферизация ---

    def enable_buffering(self):
        """Включить запись на диск (если ещё не включена)."""
        if not self.buffering_enabled:
            logger.info(
                f"Сессия {self.task_id}: включена буферизация на диск"
            )
            os.makedirs(self.buffer_dir, exist_ok=True)
            self.buffering_enabled = True

    async def process_chunk(self, chunk: bytes):
        """Обработка чанка: TS-синхронизация + рассылка + запись на диск."""
        if not self._synced:
            idx = chunk.find(b'\x47')
            if idx != -1:
                chunk = chunk[idx:]
                self._synced = True
            else:
                return

        # 1. Рассылка подписчикам
        self.dispatch(chunk)

        # 2. Запись на диск (если включена)
        if self.buffering_enabled:
            await self._write_to_buffer(chunk)

    async def _write_to_buffer(self, chunk: bytes):
        """Запись чанка в текущий сегмент с ротацией по времени."""
        now = time.time()
        if (
            not self._current_file
            or (now - self._seg_start_time) >= self.segment_duration
        ):
            await self._rotate_segment(now)

        if self._current_file:
            await asyncio.to_thread(self._sync_write, chunk)

    def _sync_write(self, chunk: bytes):
        """Синхронная запись в файл (вызывается через to_thread)."""
        if self._current_file:
            try:
                self._current_file.write(chunk)
                self._current_file.flush()
            except Exception as e:
                logger.error(f"Ошибка записи сегмента: {e}")

    async def _rotate_segment(self, now: float):
        """Смена сегмента: закрываем старый, открываем новый."""
        old_file = self._current_file
        old_seg_name = self.current_segment_name

        await self._close_current_file()

        # Только после закрытия добавляем старый сегмент в список доступных
        if old_file and old_seg_name:
            self.segments.append(old_seg_name)
            if len(self.segments) > self.max_segments:
                old_to_del = self.segments.pop(0)
                old_path = os.path.join(self.buffer_dir, old_to_del)
                await asyncio.to_thread(self._sync_delete, old_path)

        try:
            if not os.path.exists(self.buffer_dir):
                os.makedirs(self.buffer_dir, exist_ok=True)

            new_seg_name = f"segment_{self._seg_idx}.ts"
            full_path = os.path.join(self.buffer_dir, new_seg_name)

            self._current_file = open(full_path, "wb")
            self.current_segment_name = new_seg_name
            self._seg_idx += 1
            self._seg_start_time = now
        except Exception as e:
            logger.error(f"Ошибка ротации сегмента: {e}")

    @staticmethod
    def _sync_delete(path: str):
        """Синхронное удаление файла (вызывается через to_thread)."""
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    async def _close_current_file(self):
        """Закрытие текущего файла сегмента."""
        if self._current_file:
            f = self._current_file
            self._current_file = None
            await asyncio.to_thread(f.close)

    # --- Завершение ---

    def close(self):
        """Закрывает подписчиков и файл, НЕ удаляет директории.

        Очисткой временных файлов управляет модуль Stream.
        """
        # Закрываем текущий файл синхронно (для использования в stop())
        if self._current_file:
            try:
                self._current_file.close()
            except Exception:
                pass
            self._current_file = None

        super().close()

    def get_temp_dirs(self) -> list[str]:
        """Возвращает директории, созданные сессией."""
        dirs = []
        if self.buffer_dir:
            dirs.append(self.buffer_dir)
        return dirs
