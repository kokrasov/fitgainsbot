import signal
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.utils.db import init_models, engine
from app.handlers import start, registration, profile, workout, nutrition, progress, gamification, subscription


# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)


async def register_handlers(dp: Dispatcher) -> None:
    """Регистрация обработчиков"""
    # Регистрация обработчиков команд и сообщений
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(profile.router)
    dp.include_router(workout.router)
    dp.include_router(nutrition.router)
    dp.include_router(progress.router)
    dp.include_router(gamification.router)
    dp.include_router(subscription.router)


async def register_middlewares(dp: Dispatcher) -> None:
    """Регистрация промежуточных обработчиков"""
    from app.middlewares.authentication import AuthenticationMiddleware
    from app.middlewares.throttling import ThrottlingMiddleware
    
    # Регистрация middleware
    dp.message.middleware(ThrottlingMiddleware(limit=0.5))
    dp.callback_query.middleware(ThrottlingMiddleware(limit=0.5))
    dp.message.middleware(AuthenticationMiddleware())
    dp.callback_query.middleware(AuthenticationMiddleware())


async def init_bot() -> Bot:
    """Инициализация бота"""
    # Инициализация бота с настройкой парсера сообщений
    bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
    return bot


async def main() -> None:
    """Основная функция запуска бота"""
    # Инициализация бота и диспетчера
    bot = await init_bot()
    dp = Dispatcher(storage=MemoryStorage())
    
    # Инициализация моделей базы данных
    await init_models()
    
    # Регистрация обработчиков и middleware
    await register_handlers(dp)
    await register_middlewares(dp)
    
    # Добавьте обработчик корректного завершения
    async def on_shutdown(sig):
        logging.info(f"Получен сигнал {sig.name}, завершение работы...")
        # Закрываем соединения с базой данных
        await engine.dispose()
        # Останавливаем polling
        await dp.stop_polling()
    
    # Регистрируем обработчики сигналов
    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_event_loop().add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(on_shutdown(s))
        )
    
    # Запуск бота
    logging.info("Starting FitGains Bot")
    await dp.start_polling(bot)




if __name__ == "__main__":
    asyncio.run(main())