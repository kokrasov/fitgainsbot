from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.inline import back_keyboard, main_menu_keyboard
from app.utils.db import get_session

router = Router()


@router.message(Command("help"))
async def command_help(message: Message):
    """
    Обработчик команды /help
    """
    text = (
        "<b>❓ Помощь и поддержка</b>\n\n"
        "Привет! Я FitGains Bot — твой персональный помощник по набору мышечной массы! "
        "Вот что я умею:\n\n"
        "📝 <b>Основные команды:</b>\n"
        "/start — Начать работу с ботом\n"
        "/help — Показать справку\n"
        "/profile — Управление профилем\n"
        "/workout — Управление тренировками\n"
        "/nutrition — Управление питанием\n"
        "/progress — Отслеживание прогресса\n\n"
        "❓ <b>Часто задаваемые вопросы:</b>\n"
        "• Как изменить свои параметры? — В разделе «Профиль»\n"
        "• Как создать программу тренировок? — В разделе «Тренировки»\n"
        "• Как создать план питания? — В разделе «Питание»\n"
        "• Как отслеживать прогресс? — В разделе «Прогресс»\n\n"
        "⚙️ <b>Дополнительно:</b>\n"
        "Для связи с поддержкой используй команду /support"
    )
    
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📚 FAQ", callback_data="show_faq"))
    builder.row(InlineKeyboardButton(text="📞 Поддержка", callback_data="support"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"))
    
    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "help")
async def process_help(callback: CallbackQuery):
    """
    Обработчик кнопки "Помощь"
    """
    text = (
        "<b>❓ Помощь и поддержка</b>\n\n"
        "Привет! Я FitGains Bot — твой персональный помощник по набору мышечной массы! "
        "Вот что я умею:\n\n"
        "📝 <b>Основные команды:</b>\n"
        "/start — Начать работу с ботом\n"
        "/help — Показать справку\n"
        "/profile — Управление профилем\n"
        "/workout — Управление тренировками\n"
        "/nutrition — Управление питанием\n"
        "/progress — Отслеживание прогресса\n\n"
        "❓ <b>Часто задаваемые вопросы:</b>\n"
        "• Как изменить свои параметры? — В разделе «Профиль»\n"
        "• Как создать программу тренировок? — В разделе «Тренировки»\n"
        "• Как создать план питания? — В разделе «Питание»\n"
        "• Как отслеживать прогресс? — В разделе «Прогресс»\n\n"
        "⚙️ <b>Дополнительно:</b>\n"
        "Для связи с поддержкой используй команду /support"
    )
    
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📚 FAQ", callback_data="show_faq"))
    builder.row(InlineKeyboardButton(text="📞 Поддержка", callback_data="support"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "show_faq")
async def process_show_faq(callback: CallbackQuery):
    """
    Обработчик кнопки "FAQ"
    """
    text = (
        "<b>📚 Часто задаваемые вопросы</b>\n\n"
        "<b>1. Как настроить профиль?</b>\n"
        "Перейди в раздел «Профиль», нажми на «Редактировать данные» и заполни все параметры.\n\n"
        "<b>2. Как создать программу тренировок?</b>\n"
        "Перейди в раздел «Тренировки», выбери «Новая тренировка» и следуй инструкциям.\n\n"
        "<b>3. Как создать план питания?</b>\n"
        "Перейди в раздел «Питание», выбери «Обновить план» и создай персонализированный план.\n\n"
        "<b>4. Как отслеживать прогресс?</b>\n"
        "Регулярно заходи в раздел «Прогресс» и вноси свои текущие замеры.\n\n"
        "<b>5. Почему я не набираю вес?</b>\n"
        "Возможно, ты не потребляешь достаточно калорий. Убедись, что ты в профиците калорий.\n\n"
        "<b>6. Почему я набираю слишком много жира?</b>\n"
        "Возможно, твой профицит калорий слишком большой или недостаточно тренировок.\n\n"
        "<b>7. Как правильно выполнять упражнения?</b>\n"
        "К каждому упражнению прикреплена инструкция и видео (если доступно).\n\n"
        "<b>8. Что такое макронутриенты?</b>\n"
        "Это основные питательные вещества: белки, жиры и углеводы.\n\n"
        "<b>9. Сколько белка мне нужно?</b>\n"
        "Для набора мышечной массы рекомендуется 1.6-2.2 г белка на кг веса тела.\n\n"
        "<b>10. Зачем нужны кардиотренировки при наборе массы?</b>\n"
        "Они улучшают работу сердечно-сосудистой системы и помогают контролировать жировые отложения."
    )
    
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="help"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "support")
async def process_support(callback: CallbackQuery):
    """
    Обработчик кнопки "Поддержка"
    """
    text = (
        "<b>📞 Поддержка</b>\n\n"
        "Если у тебя возникли вопросы или проблемы, ты можешь связаться с нашей поддержкой:\n\n"
        "1. Напиши свой вопрос прямо сюда, и мы ответим в ближайшее время.\n\n"
        "2. Или напиши на email: support@fitgains.com\n\n"
        "3. Также ты можешь посетить наш сайт: fitgains.com\n\n"
        "Мы обычно отвечаем в течение 24 часов."
    )
    
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="help"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.message(Command("support"))
async def command_support(message: Message):
    """
    Обработчик команды /support
    """
    text = (
        "<b>📞 Поддержка</b>\n\n"
        "Если у тебя возникли вопросы или проблемы, ты можешь связаться с нашей поддержкой:\n\n"
        "1. Напиши свой вопрос прямо сюда, и мы ответим в ближайшее время.\n\n"
        "2. Или напиши на email: support@fitgains.com\n\n"
        "3. Также ты можешь посетить наш сайт: fitgains.com\n\n"
        "Мы обычно отвечаем в течение 24 часов."
    )
    
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"))
    
    await message.answer(text, reply_markup=builder.as_markup())


from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
