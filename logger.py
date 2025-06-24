import sys
from pathlib import Path
from loguru import logger

# Импортируем синглтон конфигурации
from config import config

def setup_logger():
    """
    Настраивает логгер loguru на основе пути из файла конфигурации.
    """
    if not config or not config.env.LOG_FILE_PATH:
        # Базовая настройка, если конфиг не загрузился
        logger.add(sys.stderr, level="INFO")
        logger.warning("Конфигурация логгера не найдена, используется стандартный вывод.")
        return

    log_file_path = Path(config.env.LOG_FILE_PATH)
    # Директория уже создается в config.py, но на всякий случай можно оставить
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.add(
        log_file_path,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=True
    )
    logger.info(f"Логгер настроен. Файл логов: {log_file_path}")

# Настраиваем логгер при импорте модуля
setup_logger()

# Пример использования (для тестирования)
if __name__ == "__main__":
    logger.debug("Это сообщение для отладки.")
    logger.info("Это информационное сообщение.")
    logger.warning("Это предупреждение.")
    logger.error("Это сообщение об ошибке.")

    def faulty_function():
        try:
            1 / 0
        except ZeroDivisionError:
            logger.exception("Произошла ошибка!")

    faulty_function()
