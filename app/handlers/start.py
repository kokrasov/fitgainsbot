from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.keyboards.inline import main_menu_keyboard
from app.utils.db import get_session

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    """
    Обработчик команды /start
    """
    # Проверяем, существует ли пользователь в базе данных
    user = await get_or_create_user(session, message)
    
    # Приветственное сообщение
    welcome_text = (
        f"👋 <b>Привет, {user.first_name}!</b>\n\n"
        f"Добро пожаловать в <b>FitGains Bot</b> — твой персональный помощник по набору мышечной массы! 💪\n\n"
        f"С моей помощью ты сможешь:\n"
        f"• Получить индивидуальную программу тренировок 🏋️‍♂️\n"
        f"• Создать персональный план питания 🍽️\n"
        f"• Отслеживать свой прогресс 📊\n"
        f"• Получать уведомления и мотивацию 🔔\n\n"
    )
    
    # Если пользователь новый, предлагаем ему зарегистрироваться
    if not user.height or not user.weight:
        welcome_text += (
            "Для начала работы, давай заполним твой профиль с базовыми данными, "
            "чтобы я мог подобрать оптимальную программу именно для тебя."
        )
        await message.answer(welcome_text, reply_markup=main_menu_keyboard(new_user=True))
    else:
        welcome_text += (
            "Чем я могу помочь тебе сегодня?"
        )
        await message.answer(welcome_text, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Главное меню"
    """
    user = await get_user(session, callback.from_user.id)
    
    menu_text = (
        f"<b>Главное меню</b>\n\n"
        f"Выбери раздел, который тебя интересует:"
    )
    
    # Проверяем, заполнен ли профиль пользователя
    new_user = not user.height or not user.weight
    
    await callback.message.edit_text(menu_text, reply_markup=main_menu_keyboard(new_user=new_user))
    await callback.answer()


async def get_or_create_user(session: AsyncSession, message: Message) -> User:
    """
    Получить или создать пользователя
    """
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    
    if not user:
        # Создаем нового пользователя
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    return user


async def get_user(session: AsyncSession, telegram_id: int) -> User:
    """
    Получить пользователя по telegram_id
    """
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    return user
