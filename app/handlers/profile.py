from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, date

from app.models.user import User, ActivityLevel, ExperienceLevel, DietType
from app.keyboards.inline import profile_menu_keyboard, back_keyboard, confirmation_keyboard, main_menu_keyboard, profile_setup_keyboard
from app.utils.db import get_session

router = Router()


class ProfileEditStates(StatesGroup):
    """
    Состояния для редактирования профиля
    """
    waiting_for_height = State()
    waiting_for_weight = State()
    waiting_for_target_weight = State()
    waiting_for_birthdate = State()
    waiting_for_training_days = State()


@router.callback_query(F.data == "profile_menu")
async def process_profile_menu(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Профиль"
    """
    await callback.message.edit_text(
        "<b>👤 Профиль</b>\n\n"
        "Здесь ты можешь просмотреть и изменить свои данные.\n\n"
        "Выбери действие:",
        reply_markup=profile_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "view_profile")
async def process_view_profile(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Мой профиль"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Формируем текст с информацией о пользователе
    text = "<b>👤 Мой профиль</b>\n\n"
    
    # Основная информация
    text += f"<b>Имя:</b> {user.first_name or 'Не указано'}"
    if user.last_name:
        text += f" {user.last_name}"
    text += "\n"
    
    if user.username:
        text += f"<b>Username:</b> @{user.username}\n"
    
    # Параметры пользователя
    if user.gender:
        text += f"<b>Пол:</b> {'Мужской' if user.gender == 'male' else 'Женский'}\n"
    
    if user.birthdate:
        text += f"<b>Возраст:</b> {user.age} лет\n"
    
    if user.height:
        text += f"<b>Рост:</b> {user.height} см\n"
    
    if user.weight:
        text += f"<b>Вес:</b> {user.weight} кг\n"
    
    if user.target_weight:
        text += f"<b>Целевой вес:</b> {user.target_weight} кг\n"
    
    if user.bmi:
        text += f"<b>ИМТ (Индекс массы тела):</b> {user.bmi:.1f}\n"
    
    # Уровень активности и опыта
    if user.activity_level:
        text += f"<b>Уровень активности:</b> {get_activity_level_name(user.activity_level)}\n"
    
    if user.experience_level:
        text += f"<b>Уровень опыта:</b> {get_experience_level_name(user.experience_level)}\n"
    
    # Параметры питания
    if user.diet_type:
        text += f"\n<b>Тип питания:</b> {get_diet_type_name(user.diet_type)}\n"
    
    if user.allergies:
        text += f"<b>Аллергии:</b> {user.allergies}\n"
    
    if user.calories_goal:
        text += f"<b>Целевые калории:</b> {user.calories_goal} ккал\n"
    
    if user.protein_goal and user.fat_goal and user.carbs_goal:
        text += f"<b>Макронутриенты:</b> Б {user.protein_goal}г / Ж {user.fat_goal}г / У {user.carbs_goal}г\n"
    
    # Параметры тренировок
    text += f"\n<b>Доступ к тренажерному залу:</b> {'Да' if user.has_gym_access else 'Нет'}\n"
    text += f"<b>Дней тренировок в неделю:</b> {user.training_days_per_week}\n"
    
    # Статус подписки
    text += f"\n<b>Статус подписки:</b> {'Премиум' if user.is_premium else 'Базовый'}\n"
    
    # Создаем клавиатуру с действиями
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✏️ Редактировать данные", callback_data="edit_profile"))
    builder.row(InlineKeyboardButton(text="🎯 Изменить цели", callback_data="edit_goals"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data == "edit_profile")
async def process_edit_profile(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Редактировать данные"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Формируем текст сообщения
    text = "<b>✏️ Редактирование профиля</b>\n\n"
    text += "Выбери, какие данные ты хочешь изменить:"
    
    # Создаем клавиатуру с параметрами для редактирования
    builder = InlineKeyboardBuilder()
    
    # Основные параметры
    builder.row(InlineKeyboardButton(text="♂️♀️ Пол", callback_data="edit_gender"))
    builder.row(InlineKeyboardButton(text="📏 Рост", callback_data="edit_height"))
    builder.row(InlineKeyboardButton(text="⚖️ Вес", callback_data="edit_weight"))
    builder.row(InlineKeyboardButton(text="🎯 Целевой вес", callback_data="edit_target_weight"))
    builder.row(InlineKeyboardButton(text="🎂 Дата рождения", callback_data="edit_birthdate"))
    
    # Уровень активности и опыта
    builder.row(InlineKeyboardButton(text="🏃 Уровень активности", callback_data="edit_activity_level"))
    builder.row(InlineKeyboardButton(text="🏋️ Уровень опыта", callback_data="edit_experience_level"))
    
    # Параметры тренировок
    builder.row(InlineKeyboardButton(text="🏢 Доступ к залу", callback_data="edit_gym_access"))
    builder.row(InlineKeyboardButton(text="📆 Дней тренировок", callback_data="edit_training_days"))
    
    # Параметры питания
    builder.row(InlineKeyboardButton(text="🍽️ Тип питания", callback_data="edit_diet_type"))
    
    # Кнопка "Назад"
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="view_profile"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data == "edit_gender")
async def process_edit_gender(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик редактирования пола
    """
    # Формируем клавиатуру для выбора пола
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="♂️ Мужской", callback_data="set_gender_male"),
        InlineKeyboardButton(text="♀️ Женский", callback_data="set_gender_female")
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="edit_profile"))
    
    await callback.message.edit_text(
        "<b>✏️ Редактирование пола</b>\n\n"
        "Выбери свой пол:",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("set_gender_"))
async def process_set_gender(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик выбора пола
    """
    # Получаем пол
    gender = callback.data.split("_")[-1]  # male или female
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Обновляем пол пользователя
    user.gender = gender
    await session.commit()
    
    await callback.message.edit_text(
        "<b>✅ Пол успешно обновлен!</b>\n\n"
        f"Твой пол: {'Мужской' if gender == 'male' else 'Женский'}",
        reply_markup=back_keyboard("edit_profile")
    )
    
    await callback.answer()


@router.callback_query(F.data == "edit_height")
async def process_edit_height(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик редактирования роста
    """
    # Устанавливаем состояние ожидания ввода роста
    await state.set_state(ProfileEditStates.waiting_for_height)
    
    await callback.message.edit_text(
        "<b>✏️ Редактирование роста</b>\n\n"
        "Введи свой рост в сантиметрах (например, 178):",
        reply_markup=back_keyboard("edit_profile")
    )
    
    await callback.answer()


@router.message(ProfileEditStates.waiting_for_height)
async def process_height_input(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик ввода роста
    """
    try:
        # Парсим рост
        height = float(message.text.strip())
        
        # Проверяем, что рост в пределах разумного (от 100 до 250 см)
        if height < 100 or height > 250:
            await message.answer(
                "⚠️ Ты указал некорректный рост. Пожалуйста, введи свой рост в сантиметрах (от 100 до 250)."
            )
            return
        
        # Получаем пользователя
        user = await get_user(session, message.from_user.id)
        
        # Обновляем рост пользователя
        user.height = height
        await session.commit()
        
        # Очищаем состояние
        await state.clear()
        
        await message.answer(
            "<b>✅ Рост успешно обновлен!</b>\n\n"
            f"Твой рост: {height} см",
            reply_markup=back_keyboard("edit_profile")
        )
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат. Пожалуйста, введи свой рост в сантиметрах числом (например, 178)."
        )


@router.callback_query(F.data == "edit_weight")
async def process_edit_weight(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик редактирования веса
    """
    # Устанавливаем состояние ожидания ввода веса
    await state.set_state(ProfileEditStates.waiting_for_weight)
    
    await callback.message.edit_text(
        "<b>✏️ Редактирование веса</b>\n\n"
        "Введи свой текущий вес в килограммах (например, 75.5):",
        reply_markup=back_keyboard("edit_profile")
    )
    
    await callback.answer()


@router.message(ProfileEditStates.waiting_for_weight)
async def process_weight_input(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик ввода веса
    """
    try:
        # Парсим вес
        weight = float(message.text.strip())
        
        # Проверяем, что вес в пределах разумного (от 30 до 300 кг)
        if weight < 30 or weight > 300:
            await message.answer(
                "⚠️ Ты указал некорректный вес. Пожалуйста, введи свой вес в килограммах (от 30 до 300)."
            )
            return
        
        # Получаем пользователя
        user = await get_user(session, message.from_user.id)
        
        # Обновляем вес пользователя
        user.weight = weight
        await session.commit()
        
        # Очищаем состояние
        await state.clear()
        
        await message.answer(
            "<b>✅ Вес успешно обновлен!</b>\n\n"
            f"Твой вес: {weight} кг",
            reply_markup=back_keyboard("edit_profile")
        )
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат. Пожалуйста, введи свой вес в килограммах числом (например, 75.5)."
        )


@router.callback_query(F.data == "edit_target_weight")
async def process_edit_target_weight(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик редактирования целевого веса
    """
    # Устанавливаем состояние ожидания ввода целевого веса
    await state.set_state(ProfileEditStates.waiting_for_target_weight)
    
    await callback.message.edit_text(
        "<b>✏️ Редактирование целевого веса</b>\n\n"
        "Введи свой целевой вес в килограммах (например, 80):",
        reply_markup=back_keyboard("edit_profile")
    )
    
    await callback.answer()


@router.message(ProfileEditStates.waiting_for_target_weight)
async def process_target_weight_input(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик ввода целевого веса
    """
    try:
        # Парсим целевой вес
        target_weight = float(message.text.strip())
        
        # Проверяем, что целевой вес в пределах разумного (от 30 до 300 кг)
        if target_weight < 30 or target_weight > 300:
            await message.answer(
                "⚠️ Ты указал некорректный целевой вес. Пожалуйста, введи свой целевой вес в килограммах (от 30 до 300)."
            )
            return
        
        # Получаем пользователя
        user = await get_user(session, message.from_user.id)
        
        # Обновляем целевой вес пользователя
        user.target_weight = target_weight
        await session.commit()
        
        # Очищаем состояние
        await state.clear()
        
        await message.answer(
            "<b>✅ Целевой вес успешно обновлен!</b>\n\n"
            f"Твой целевой вес: {target_weight} кг",
            reply_markup=back_keyboard("edit_profile")
        )
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат. Пожалуйста, введи свой целевой вес в килограммах числом (например, 80)."
        )


@router.callback_query(F.data == "edit_birthdate")
async def process_edit_birthdate(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик редактирования даты рождения
    """
    # Устанавливаем состояние ожидания ввода даты рождения
    await state.set_state(ProfileEditStates.waiting_for_birthdate)
    
    await callback.message.edit_text(
        "<b>✏️ Редактирование даты рождения</b>\n\n"
        "Введи свою дату рождения в формате ДД.ММ.ГГГГ (например, 15.06.1990):",
        reply_markup=back_keyboard("edit_profile")
    )
    
    await callback.answer()


@router.message(ProfileEditStates.waiting_for_birthdate)
async def process_birthdate_input(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик ввода даты рождения
    """
    try:
        # Парсим дату рождения
        birthdate = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        
        # Проверяем, что дата корректна и пользователю не меньше 14 и не больше 100 лет
        today = datetime.now().date()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        
        if age < 14 or age > 100:
            await message.answer(
                "⚠️ Ты указал некорректный возраст. Пожалуйста, введи дату рождения в формате ДД.ММ.ГГГГ."
            )
            return
        
        # Получаем пользователя
        user = await get_user(session, message.from_user.id)
        
        # Обновляем дату рождения пользователя
        user.birthdate = birthdate
        await session.commit()
        
        # Очищаем состояние
        await state.clear()
        
        await message.answer(
            "<b>✅ Дата рождения успешно обновлена!</b>\n\n"
            f"Твоя дата рождения: {birthdate.strftime('%d.%m.%Y')}\n"
            f"Возраст: {age} лет",
            reply_markup=back_keyboard("edit_profile")
        )
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат. Пожалуйста, введи свою дату рождения в формате ДД.ММ.ГГГГ (например, 15.06.1990)."
        )


@router.callback_query(F.data == "edit_activity_level")
async def process_edit_activity_level(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик редактирования уровня активности
    """
    # Создаем клавиатуру для выбора уровня активности
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📱 Сидячий образ жизни", callback_data="set_activity_sedentary"))
    builder.row(InlineKeyboardButton(text="🚶 Легкая активность (1-2 раза в неделю)", callback_data="set_activity_lightly_active"))
    builder.row(InlineKeyboardButton(text="🏃 Умеренная активность (3-5 раз в неделю)", callback_data="set_activity_moderately_active"))
    builder.row(InlineKeyboardButton(text="🏋️ Высокая активность (6-7 раз в неделю)", callback_data="set_activity_very_active"))
    builder.row(InlineKeyboardButton(text="🏅 Профессиональный спорт", callback_data="set_activity_extremely_active"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="edit_profile"))
    
    await callback.message.edit_text(
        "<b>✏️ Редактирование уровня активности</b>\n\n"
        "Выбери свой уровень физической активности:",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("set_activity_"))
async def process_set_activity(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик выбора уровня активности
    """
    # Получаем уровень активности
    activity_level = callback.data.split("_", 2)[-1]  # sedentary, lightly_active и т.д.
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Обновляем уровень активности пользователя
    user.activity_level = ActivityLevel(activity_level)
    await session.commit()
    
    await callback.message.edit_text(
        "<b>✅ Уровень активности успешно обновлен!</b>\n\n"
        f"Твой уровень активности: {get_activity_level_name(ActivityLevel(activity_level))}",
        reply_markup=back_keyboard("edit_profile")
    )
    
    await callback.answer()


@router.callback_query(F.data == "edit_experience_level")
async def process_edit_experience_level(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик редактирования уровня опыта
    """
    # Создаем клавиатуру для выбора уровня опыта
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔰 Новичок (0-6 месяцев)", callback_data="set_experience_beginner"))
    builder.row(InlineKeyboardButton(text="🥉 Средний (6 месяцев - 2 года)", callback_data="set_experience_intermediate"))
    builder.row(InlineKeyboardButton(text="🥇 Продвинутый (2+ лет)", callback_data="set_experience_advanced"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="edit_profile"))
    
    await callback.message.edit_text(
        "<b>✏️ Редактирование уровня опыта</b>\n\n"
        "Выбери свой уровень опыта в тренировках:",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("set_experience_"))
async def process_set_experience(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик выбора уровня опыта
    """
    # Получаем уровень опыта
    experience_level = callback.data.split("_", 2)[-1]  # beginner, intermediate, advanced
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Обновляем уровень опыта пользователя
    user.experience_level = ExperienceLevel(experience_level)
    await session.commit()
    
    await callback.message.edit_text(
        "<b>✅ Уровень опыта успешно обновлен!</b>\n\n"
        f"Твой уровень опыта: {get_experience_level_name(ExperienceLevel(experience_level))}",
        reply_markup=back_keyboard("edit_profile")
    )
    
    await callback.answer()


@router.callback_query(F.data == "edit_gym_access")
async def process_edit_gym_access(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик редактирования доступа к тренажерному залу
    """
    # Создаем клавиатуру для выбора наличия доступа к залу
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data="set_gym_yes"),
        InlineKeyboardButton(text="❌ Нет", callback_data="set_gym_no")
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="edit_profile"))
    
    await callback.message.edit_text(
        "<b>✏️ Редактирование доступа к залу</b>\n\n"
        "У тебя есть доступ к тренажерному залу?",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("set_gym_"))
async def process_set_gym(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик выбора наличия доступа к залу
    """
    # Получаем наличие доступа к залу
    has_gym = callback.data.split("_")[-1] == "yes"  # yes или no
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Обновляем наличие доступа к залу
    user.has_gym_access = has_gym
    await session.commit()
    
    await callback.message.edit_text(
        "<b>✅ Доступ к залу успешно обновлен!</b>\n\n"
        f"Доступ к тренажерному залу: {'Да' if has_gym else 'Нет'}",
        reply_markup=back_keyboard("edit_profile")
    )
    
    await callback.answer()


@router.callback_query(F.data == "edit_training_days")
async def process_edit_training_days(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик редактирования количества дней тренировок
    """
    # Создаем клавиатуру для выбора количества дней тренировок
    builder = InlineKeyboardBuilder()
    for days in [2, 3, 4, 5, 6]:
        builder.row(InlineKeyboardButton(text=f"{days} дня(ей) в неделю", callback_data=f"set_training_days_{days}"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="edit_profile"))
    
    await callback.message.edit_text(
        "<b>✏️ Редактирование дней тренировок</b>\n\n"
        "Сколько дней в неделю ты планируешь тренироваться?",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("set_training_days_"))
async def process_set_training_days(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик выбора количества дней тренировок
    """
    # Получаем количество дней тренировок
    training_days = int(callback.data.split("_")[-1])  # 2, 3, 4, 5 или 6
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Обновляем количество дней тренировок
    user.training_days_per_week = training_days
    await session.commit()
    
    await callback.message.edit_text(
        "<b>✅ Количество дней тренировок успешно обновлено!</b>\n\n"
        f"Дней тренировок в неделю: {training_days}",
        reply_markup=back_keyboard("edit_profile")
    )
    
    await callback.answer()


@router.callback_query(F.data == "edit_diet_type")
async def process_edit_diet_type(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик редактирования типа питания
    """
    # Создаем клавиатуру для выбора типа питания
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🍗 Обычная", callback_data="set_diet_regular"))
    builder.row(InlineKeyboardButton(text="🥗 Вегетарианская", callback_data="set_diet_vegetarian"))
    builder.row(InlineKeyboardButton(text="🥬 Веганская", callback_data="set_diet_vegan"))
    builder.row(InlineKeyboardButton(text="🥩 Кето", callback_data="set_diet_keto"))
    builder.row(InlineKeyboardButton(text="🍳 Палео", callback_data="set_diet_paleo"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="edit_profile"))
    
    await callback.message.edit_text(
        "<b>✏️ Редактирование типа питания</b>\n\n"
        "Выбери свой тип питания:",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("set_diet_"))
async def process_set_diet(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик выбора типа питания
    """
    # Получаем тип питания
    diet_type = callback.data.split("_", 2)[-1]  # regular, vegetarian, vegan и т.д.
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Обновляем тип питания пользователя
    user.diet_type = DietType(diet_type)
    await session.commit()
    
    await callback.message.edit_text(
        "<b>✅ Тип питания успешно обновлен!</b>\n\n"
        f"Твой тип питания: {get_diet_type_name(DietType(diet_type))}",
        reply_markup=back_keyboard("edit_profile")
    )
    
    await callback.answer()


@router.callback_query(F.data == "edit_goals")
async def process_edit_goals(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Изменить цели"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Формируем текст сообщения
    text = "<b>🎯 Изменение целей</b>\n\n"
    
    if user.weight and user.target_weight:
        weight_diff = user.target_weight - user.weight
        text += f"Текущий вес: {user.weight} кг\n"
        text += f"Целевой вес: {user.target_weight} кг\n"
        text += f"Разница: {weight_diff:+.1f} кг\n\n"
    
    text += "Выбери цель, которую хочешь изменить:"
    
    # Создаем клавиатуру с целями для редактирования
    builder = InlineKeyboardBuilder()
    
    # Основные цели
    builder.row(InlineKeyboardButton(text="⚖️ Целевой вес", callback_data="edit_target_weight"))
    builder.row(InlineKeyboardButton(text="🏋️ Дней тренировок", callback_data="edit_training_days"))
    
    # Цели по питанию
    builder.row(InlineKeyboardButton(text="🍽️ Целевые калории", callback_data="edit_calories_goal"))
    builder.row(InlineKeyboardButton(text="🥩 Макронутриенты", callback_data="edit_macros_goals"))
    
    # Кнопка "Назад"
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="view_profile"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data == "settings")
async def process_settings(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Настройки"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Формируем текст сообщения
    text = "<b>⚙️ Настройки</b>\n\n"
    text += "Выбери настройки, которые хочешь изменить:"
    
    # Создаем клавиатуру с настройками
    builder = InlineKeyboardBuilder()
    
    # Настройки уведомлений
    builder.row(InlineKeyboardButton(text="🔔 Уведомления", callback_data="notification_settings"))
    
    # Настройки языка (в будущем)
    # builder.row(InlineKeyboardButton(text="🌐 Язык", callback_data="language_settings"))
    
    # Настройки приватности
    builder.row(InlineKeyboardButton(text="🔒 Приватность", callback_data="privacy_settings"))
    
    # Кнопка "Назад"
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


async def get_user(session: AsyncSession, telegram_id: int) -> User:
    """
    Получить пользователя по telegram_id
    """
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    return user


def get_activity_level_name(activity_level: ActivityLevel) -> str:
    """
    Возвращает название уровня активности на русском
    
    :param activity_level: Уровень активности
    :return: Название на русском
    """
    activity_level_names = {
        ActivityLevel.SEDENTARY: "Сидячий образ жизни",
        ActivityLevel.LIGHTLY_ACTIVE: "Легкая активность (1-2 раза в неделю)",
        ActivityLevel.MODERATELY_ACTIVE: "Умеренная активность (3-5 раз в неделю)",
        ActivityLevel.VERY_ACTIVE: "Высокая активность (6-7 раз в неделю)",
        ActivityLevel.EXTREMELY_ACTIVE: "Профессиональный спорт"
    }
    
    return activity_level_names.get(activity_level, str(activity_level))


def get_experience_level_name(experience_level: ExperienceLevel) -> str:
    """
    Возвращает название уровня опыта на русском
    
    :param experience_level: Уровень опыта
    :return: Название на русском
    """
    experience_level_names = {
        ExperienceLevel.BEGINNER: "Новичок (0-6 месяцев)",
        ExperienceLevel.INTERMEDIATE: "Средний (6 месяцев - 2 года)",
        ExperienceLevel.ADVANCED: "Продвинутый (2+ лет)"
    }
    
    return experience_level_names.get(experience_level, str(experience_level))


def get_diet_type_name(diet_type: DietType) -> str:
    """
    Возвращает название типа питания на русском
    
    :param diet_type: Тип питания
    :return: Название на русском
    """
    diet_type_names = {
        DietType.REGULAR: "Обычная",
        DietType.VEGETARIAN: "Вегетарианская",
        DietType.VEGAN: "Веганская",
        DietType.KETO: "Кето",
        DietType.PALEO: "Палео",
        DietType.MEDITERRANEAN: "Средиземноморская"
    }
    
    return diet_type_names.get(diet_type, str(diet_type))


from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
