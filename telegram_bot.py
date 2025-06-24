import asyncio
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

from loguru import logger
from config import config
from rag_engine import RagEngine

# --- Глобальные переменные ---
bot = Bot(token=config.env.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
# Создаем один экземпляр нашего движка
# Инициализация может занять время, т.к. может начаться синхронизация
logger.info("Идет инициализация RagEngine... Это может занять некоторое время.")
try:
    rag_engine = RagEngine()
    SYNC_IN_PROGRESS = False
except Exception as e:
    logger.critical(f"Не удалось инициализировать RagEngine: {e}")
    rag_engine = None
    # Если движок не запустился, бот не сможет работать.
    # В реальной системе здесь нужна более сложная обработка.


# --- Обработчики команд ---

@dp.message(Command("start", "help"))
async def send_welcome(message: Message):
    """Отправляет приветственное сообщение."""
    welcome_text = (
        "<b>Добро пожаловать в RAG-систему!</b>\n\n"
        "Я могу отвечать на ваши вопросы, основываясь на документах, "
        "загруженных в мою базу знаний из Google Drive.\n\n"
        "<b>Доступные команды:</b>\n"
        "/help - показать это сообщение\n"
        "/sync - принудительно синхронизировать базу знаний с Google Drive\n\n"
        "Просто задайте мне любой вопрос!"
    )
    await message.answer(welcome_text, parse_mode=ParseMode.HTML)


def sync_task():
    """Функция для выполнения синхронизации в отдельном потоке."""
    global SYNC_IN_PROGRESS
    SYNC_IN_PROGRESS = True
    logger.info("Запущена синхронизация в фоновом режиме...")
    try:
        rag_engine.sync_knowledge_base()
    except Exception as e:
        logger.error(f"Ошибка во время фоновой синхронизации: {e}")
    finally:
        SYNC_IN_PROGRESS = False
        logger.info("Фоновая синхронизация завершена.")

@dp.message(Command("sync"))
async def sync_database(message: Message):
    """Запускает синхронизацию базы знаний."""
    global SYNC_IN_PROGRESS
    if SYNC_IN_PROGRESS:
        await message.answer("Синхронизация уже выполняется. Пожалуйста, подождите.")
        return

    await message.answer("Начинаю синхронизацию с Google Drive... "
                         "Это может занять некоторое время. "
                         "Я сообщу, когда будет готово (в логах).")
    
    # Запускаем синхронизацию в отдельном потоке, чтобы не блокировать бота
    thread = threading.Thread(target=sync_task)
    thread.start()


@dp.message(F.text)
async def handle_query(message: Message):
    """Обрабатывает текстовый запрос пользователя к RAG-системе."""
    if not rag_engine:
        await message.answer("Извините, сервис временно недоступен из-за ошибки инициализации.")
        return

    question = message.text
    logger.info(f"Получен вопрос от @{message.from_user.username}: '{question}'")
    
    # Показываем, что бот "думает"
    thinking_message = await message.answer("Думаю...")

    try:
        answer = rag_engine.answer_query(question)
        await thinking_message.edit_text(answer)
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса '{question}': {e}")
        await thinking_message.edit_text("Произошла внутренняя ошибка. Попробуйте позже.")


# --- Главная функция запуска ---

async def main():
    """Главная функция для запуска бота."""
    if not rag_engine:
        logger.critical("Бот не может быть запущен, так как RagEngine не инициализирован.")
        return

    logger.info("Запуск Telegram-бота...")
    # Пропускаем старые обновления
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    if not config or not config.env.TELEGRAM_BOT_TOKEN or config.env.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        logger.critical("Токен Telegram-бота не найден. Пожалуйста, укажите TELEGRAM_BOT_TOKEN в .env файле.")
    else:
        try:
            asyncio.run(main())
        except (KeyboardInterrupt, SystemExit):
            logger.info("Бот остановлен.")
        except Exception as e:
            logger.critical(f"Критическая ошибка при работе бота: {e}")
