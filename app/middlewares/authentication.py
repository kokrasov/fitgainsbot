from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TelegramUser, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.utils.db import get_session


class AuthenticationMiddleware(BaseMiddleware):
    """
    Middleware для аутентификации пользователей и записи информации о них в базу данных
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Выполняет аутентификацию пользователя
        
        :param handler: Обработчик события
        :param event: Событие
        :param data: Данные события
        :return: Результат выполнения обработчика
        """
        # Получаем пользователя Telegram
        user = None
        
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if user:
            # Создаем или обновляем пользователя в базе данных
            async for session in get_session():
                data["session"] = session
                await self._get_or_create_user(session, user)
        
        # Вызываем следующий обработчик
        return await handler(event, data)
    
    async def _get_or_create_user(self, session: AsyncSession, tg_user: TelegramUser) -> User:
        """
        Получает или создает пользователя в базе данных
        
        :param session: Сессия базы данных
        :param tg_user: Пользователь Telegram
        :return: Модель пользователя
        """
        # Пытаемся найти пользователя в базе данных
        result = await session.execute(select(User).where(User.telegram_id == tg_user.id))
        user = result.scalar_one_or_none()
        
        if not user:
            # Создаем нового пользователя
            user = User(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # Обновляем информацию о пользователе, если она изменилась
            if (user.username != tg_user.username or
                user.first_name != tg_user.first_name or
                user.last_name != tg_user.last_name):
                
                user.username = tg_user.username
                user.first_name = tg_user.first_name
                user.last_name = tg_user.last_name
                
                await session.commit()
        
        return user
