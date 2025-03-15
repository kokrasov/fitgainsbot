from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from cachetools import TTLCache
from datetime import datetime


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware для ограничения частоты запросов (анти-флуд)
    """
    
    def __init__(self, limit: float = 0.7):
        """
        Инициализирует middleware для ограничения частоты запросов
        
        :param limit: Минимальный интервал между запросами в секундах
        """
        self.limit = limit
        self.cache = TTLCache(maxsize=10000, ttl=60)  # Кэш запросов на 60 секунд
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Ограничивает частоту запросов от пользователя
        
        :param handler: Обработчик события
        :param event: Событие
        :param data: Данные события
        :return: Результат выполнения обработчика
        """
        # Получаем ID пользователя
        user_id = None
        
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        
        if user_id:
            # Проверяем кэш на наличие предыдущего запроса
            key = f"{user_id}"
            now = datetime.now().timestamp()
            
            if key in self.cache:
                last_request = self.cache[key]
                if now - last_request < self.limit:
                    # Если запрос слишком частый, пропускаем его
                    if isinstance(event, CallbackQuery):
                        # Для callback запросов отвечаем, чтобы кнопка не оставалась в состоянии загрузки
                        await event.answer("Слишком много запросов. Пожалуйста, подождите немного.", show_alert=True)
                    
                    return None
            
            # Сохраняем время текущего запроса
            self.cache[key] = now
        
        # Вызываем следующий обработчик
        return await handler(event, data)
