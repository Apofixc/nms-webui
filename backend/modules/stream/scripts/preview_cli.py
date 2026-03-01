import sys
import os
import argparse
import asyncio
import logging
import importlib
from pathlib import Path

# Добавляем корень проекта в путь поиска модулей
sys.path.append(os.getcwd())

from backend.modules.stream.core.types import StreamProtocol, PreviewFormat

# Настройка логирования в stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("preview_cli")

async def run_capture(args):
    """
    Загружает бэкенд и выполняет генерацию превью.
    """
    try:
        # 1. Определяем путь к бэкенду
        sub_dir = Path("backend/modules/stream/submodules") / args.backend
        if not sub_dir.is_dir():
             logger.error(f"Директория бэкенда не найдена: {sub_dir}")
             return 1
        
        # 2. Импортируем фабрику
        module_path = f"backend.modules.stream.submodules.{args.backend}"
        try:
            module = importlib.import_module(module_path)
        except Exception as e:
            logger.error(f"Не удалось импортировать модуль {module_path}: {e}")
            return 1
            
        if not hasattr(module, "create_backend"):
            logger.error(f"Модуль {module_path} не имеет create_backend")
            return 1
            
        # 3. Инициализация (передаем таймаут в настройки)
        settings = {
            "timeout": args.timeout,
            f"{args.backend}_timeout": args.timeout
        }
        backend = module.create_backend(settings)
        
        # 4. Генерация
        protocol = StreamProtocol(args.protocol)
        fmt = PreviewFormat(args.format)
        
        logger.info(f"Запуск генерации превью: backend={args.backend}, url={args.url}, timeout={args.timeout}")
        
        data = await backend.generate_preview(
            url=args.url,
            protocol=protocol,
            fmt=fmt,
            width=args.width,
            quality=args.quality
        )
        
        if data:
            # Вывод бинарных данных в stdout
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
            logger.info(f"Превью успешно сгенерировано ({len(data)} байт)")
            return 0
        else:
            logger.error("Бэкенд вернул пустой результат")
            return 1
            
    except Exception as e:
        logger.error(f"Критическая ошибка в preview_cli: {e}", exc_info=True)
        return 1

def main():
    parser = argparse.ArgumentParser(description="Универсальный захват превью в изолированном процессе")
    parser.add_argument("--backend", required=True, help="ID бэкенда (ffmpeg, builtin_preview и т.д.)")
    parser.add_argument("--url", required=True, help="URL источника")
    parser.add_argument("--protocol", required=True, help="Протокол (http, rtsp, udp...)")
    parser.add_argument("--format", default="jpeg", help="Формат (jpeg, png, webp)")
    parser.add_argument("--width", type=int, default=640, help="Ширина")
    parser.add_argument("--quality", type=int, default=75, help="Качество")
    parser.add_argument("--timeout", type=int, default=15, help="Таймаут захвата (сек)")
    
    args = parser.parse_args()
    
    try:
        exit_code = asyncio.run(run_capture(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        sys.exit(130)

if __name__ == "__main__":
    main()
