import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.enums.parse_mode import ParseMode
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

# Получите токен из .env или укажите напрямую для тестирования
BOT_TOKEN = "ВАШ_ТОКЕН_БОТА"  # Замените на ваш реальный токен


# Создаем обработчики
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    await message.answer(
        "👋 <b>Привет!</b>\n\n"
        "Добро пожаловать в <b>FitGains Bot</b> — твой персональный помощник по набору мышечной массы! 💪\n\n"
        "Бот в процессе разработки и тестирования. Скоро здесь будет больше функциональности!"
    )


async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    await message.answer(
        "<b>❓ Помощь</b>\n\n"
        "Это тестовая версия бота FitGains. Полная функциональность скоро будет доступна.\n\n"
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение"
    )


async def on_message(message: types.Message):
    """Обработчик всех текстовых сообщений"""
    await message.answer(
        "Я пока понимаю только команды /start и /help.\n"
        "Полная функциональность появится в ближайшее время!"
    )


async def main():
    """Основная функция запуска бота"""
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    
    # Регистрация обработчиков
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(on_message)
    
    # Запуск бота
    logging.info("Starting FitGains Bot (Simple Version)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())