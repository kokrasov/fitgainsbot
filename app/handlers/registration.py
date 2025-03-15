from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.models.user import User, ActivityLevel, ExperienceLevel, DietType
from app.keyboards.inline import profile_setup_keyboard, main_menu_keyboard
from app.utils.db import get_session

router = Router()


class ProfileSetup(StatesGroup):
    """
    Состояния для настройки профиля
    """
    gender = State()
    birthdate = State()
    height = State()
    weight = State()
    target_weight = State()
    activity_level = State()
    experience_level = State()
    diet_type = State()
    allergies = State()
    has_gym = State()
    training_days = State()


@router.callback_query(F.data == "profile_setup")
async def process_profile_setup(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Заполнить профиль"
    """
    # Начинаем настройку профиля с указания пола
    await state.set_state(ProfileSetup.gender)
    
    await callback.message.edit_text(
        "<b>Настройка профиля (1/9)</b>\n\n"
        "Укажи свой пол:",
        reply_markup=profile_setup_keyboard("gender")
    )
    await callback.answer()


# Обработчики для выбора пола
@router.callback_query(ProfileSetup.gender, F.data.startswith("gender_"))
async def process_gender(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик выбора пола
    """
    gender = callback.data.split("_")[1]  # male или female
    
    # Сохраняем пол в состоянии
    await state.update_data(gender=gender)
    
    # Обновляем пользователя в базе данных
    user = await get_user(session, callback.from_user.id)
    user.gender = gender
    await session.commit()
    
    # Переходим к следующему шагу - дата рождения
    await state.set_state(ProfileSetup.birthdate)
    
    await callback.message.edit_text(
        "<b>Настройка профиля (2/9)</b>\n\n"
        "Введи свою дату рождения в формате ДД.ММ.ГГГГ (например, 15.06.1990):",
        reply_markup=profile_setup_keyboard("birthdate")
    )
    await callback.answer()


# Обработчик ввода даты рождения
@router.message(ProfileSetup.birthdate)
async def process_birthdate(message: Message, state: FSMContext, session: AsyncSession):
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
        
        # Сохраняем дату рождения в состоянии
        await state.update_data(birthdate=birthdate.isoformat())
        
        # Обновляем пользователя в базе данных
        user = await get_user(session, message.from_user.id)
        user.birthdate = birthdate
        await session.commit()
        
        # Переходим к следующему шагу - рост
        await state.set_state(ProfileSetup.height)
        
        await message.answer(
            "<b>Настройка профиля (3/9)</b>\n\n"
            "Введи свой рост в сантиметрах (например, 178):",
            reply_markup=profile_setup_keyboard("height")
        )
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат даты. Пожалуйста, введи дату рождения в формате ДД.ММ.ГГГГ (например, 15.06.1990)."
        )


# Обработчик ввода роста
@router.message(ProfileSetup.height)
async def process_height(message: Message, state: FSMContext, session: AsyncSession):
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
        
        # Сохраняем рост в состоянии
        await state.update_data(height=height)
        
        # Обновляем пользователя в базе данных
        user = await get_user(session, message.from_user.id)
        user.height = height
        await session.commit()
        
        # Переходим к следующему шагу - вес
        await state.set_state(ProfileSetup.weight)
        
        await message.answer(
            "<b>Настройка профиля (4/9)</b>\n\n"
            "Введи свой текущий вес в килограммах (например, 75.5):",
            reply_markup=profile_setup_keyboard("weight")
        )
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат. Пожалуйста, введи свой рост в сантиметрах числом (например, 178)."
        )


# Обработчик ввода веса
@router.message(ProfileSetup.weight)
async def process_weight(message: Message, state: FSMContext, session: AsyncSession):
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
        
        # Сохраняем вес в состоянии
        await state.update_data(weight=weight)
        
        # Обновляем пользователя в базе данных
        user = await get_user(session, message.from_user.id)
        user.weight = weight
        await session.commit()
        
        # Переходим к следующему шагу - целевой вес
        await state.set_state(ProfileSetup.target_weight)
        
        await message.answer(
            "<b>Настройка профиля (5/9)</b>\n\n"
            f"Твой текущий вес: {weight} кг.\n\n"
            "Введи свой целевой вес в килограммах (например, 80):",
            reply_markup=profile_setup_keyboard("target_weight")
        )
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат. Пожалуйста, введи свой вес в килограммах числом (например, 75.5)."
        )


# Обработчик ввода целевого веса
@router.message(ProfileSetup.target_weight)
async def process_target_weight(message: Message, state: FSMContext, session: AsyncSession):
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
        
        # Сохраняем целевой вес в состоянии
        await state.update_data(target_weight=target_weight)
        
        # Обновляем пользователя в базе данных
        user = await get_user(session, message.from_user.id)
        user.target_weight = target_weight
        await session.commit()
        
        # Переходим к следующему шагу - уровень активности
        await state.set_state(ProfileSetup.activity_level)
        
        await message.answer(
            "<b>Настройка профиля (6/9)</b>\n\n"
            "Выбери свой уровень физической активности:",
            reply_markup=profile_setup_keyboard("activity_level")
        )
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат. Пожалуйста, введи свой целевой вес в килограммах числом (например, 80)."
        )


# Обработчик выбора уровня активности
@router.callback_query(ProfileSetup.activity_level, F.data.startswith("activity_"))
async def process_activity_level(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик выбора уровня активности
    """
    activity_level = callback.data.split("_", 1)[1]  # sedentary, lightly_active и т.д.
    
    # Сохраняем уровень активности в состоянии
    await state.update_data(activity_level=activity_level)
    
    # Обновляем пользователя в базе данных
    user = await get_user(session, callback.from_user.id)
    user.activity_level = ActivityLevel(activity_level)
    await session.commit()
    
    # Переходим к следующему шагу - уровень опыта
    await state.set_state(ProfileSetup.experience_level)
    
    await callback.message.edit_text(
        "<b>Настройка профиля (7/9)</b>\n\n"
        "Выбери свой уровень опыта в тренировках:",
        reply_markup=profile_setup_keyboard("experience_level")
    )
    await callback.answer()


# Обработчик выбора уровня опыта
@router.callback_query(ProfileSetup.experience_level, F.data.startswith("experience_"))
async def process_experience_level(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик выбора уровня опыта
    """
    experience_level = callback.data.split("_", 1)[1]  # beginner, intermediate, advanced
    
    # Сохраняем уровень опыта в состоянии
    await state.update_data(experience_level=experience_level)
    
    # Обновляем пользователя в базе данных
    user = await get_user(session, callback.from_user.id)
    user.experience_level = ExperienceLevel(experience_level)
    await session.commit()
    
    # Переходим к следующему шагу - тип диеты
    await state.set_state(ProfileSetup.diet_type)
    
    await callback.message.edit_text(
        "<b>Настройка профиля (8/9)</b>\n\n"
        "Выбери свой тип питания:",
        reply_markup=profile_setup_keyboard("diet_type")
    )
    await callback.answer()


# Обработчик выбора типа диеты
@router.callback_query(ProfileSetup.diet_type, F.data.startswith("diet_"))
async def process_diet_type(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик выбора типа диеты
    """
    diet_type = callback.data.split("_", 1)[1]  # regular, vegetarian, vegan и т.д.
    
    # Сохраняем тип диеты в состоянии
    await state.update_data(diet_type=diet_type)
    
    # Обновляем пользователя в базе данных
    user = await get_user(session, callback.from_user.id)
    user.diet_type = DietType(diet_type)
    await session.commit()
    
    # Пропускаем шаг с аллергиями и переходим к наличию доступа к залу
    await state.set_state(ProfileSetup.has_gym)
    
    await callback.message.edit_text(
        "<b>Настройка профиля (9/9)</b>\n\n"
        "У тебя есть доступ к тренажерному залу?",
        reply_markup=profile_setup_keyboard("has_gym")
    )
    await callback.answer()


# Обработчик выбора наличия доступа к тренажерному залу
@router.callback_query(ProfileSetup.has_gym, F.data.startswith("gym_"))
async def process_has_gym(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик выбора наличия доступа к тренажерному залу
    """
    has_gym = callback.data.split("_")[1] == "yes"  # yes или no
    
    # Сохраняем наличие доступа к тренажерному залу в состоянии
    await state.update_data(has_gym=has_gym)
    
    # Обновляем пользователя в базе данных
    user = await get_user(session, callback.from_user.id)
    user.has_gym_access = has_gym
    await session.commit()
    
    # Переходим к следующему шагу - количество тренировочных дней
    await state.set_state(ProfileSetup.training_days)
    
    await callback.message.edit_text(
        "<b>Настройка профиля (10/10)</b>\n\n"
        "Сколько дней в неделю ты готов тренироваться?",
        reply_markup=profile_setup_keyboard("training_days")
    )
    await callback.answer()


# Обработчик выбора количества тренировочных дней
@router.callback_query(ProfileSetup.training_days, F.data.startswith("training_days_"))
async def process_training_days(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик выбора количества тренировочных дней
    """
    training_days = int(callback.data.split("_")[-1])  # 2, 3, 4, 5 или 6
    
    # Сохраняем количество тренировочных дней в состоянии
    await state.update_data(training_days=training_days)
    
    # Обновляем пользователя в базе данных
    user = await get_user(session, callback.from_user.id)
    user.training_days_per_week = training_days
    await session.commit()
    
    # Завершаем настройку профиля
    await state.clear()
    
    await callback.message.edit_text(
        "<b>Профиль успешно настроен! 🎉</b>\n\n"
        "Теперь я могу предложить тебе персонализированную программу тренировок и питания.\n\n"
        "Выбери, что ты хочешь сделать дальше:",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


# Обработчики для кнопок "Назад"
@router.callback_query(F.data.startswith("back_from_"))
async def process_back(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопок "Назад"
    """
    current_step = callback.data.split("_")[-1]
    
    # Определяем предыдущий шаг в зависимости от текущего
    prev_states = {
        "birthdate": ProfileSetup.gender,
        "height": ProfileSetup.birthdate,
        "weight": ProfileSetup.height,
        "target_weight": ProfileSetup.weight,
        "activity_level": ProfileSetup.target_weight,
        "experience_level": ProfileSetup.activity_level,
        "diet_type": ProfileSetup.experience_level,
        "allergies": ProfileSetup.diet_type,
        "has_gym": ProfileSetup.allergies,
        "training_days": ProfileSetup.has_gym,
    }
    
    # Получаем предыдущий шаг
    prev_state = prev_states.get(current_step)
    
    if prev_state:
        # Устанавливаем предыдущий шаг
        await state.set_state(prev_state)
        
        # Определяем заголовок и клавиатуру для предыдущего шага
        step_titles = {
            ProfileSetup.gender: ("Настройка профиля (1/9)", "Укажи свой пол:", "gender"),
            ProfileSetup.birthdate: ("Настройка профиля (2/9)", "Введи свою дату рождения в формате ДД.ММ.ГГГГ (например, 15.06.1990):", "birthdate"),
            ProfileSetup.height: ("Настройка профиля (3/9)", "Введи свой рост в сантиметрах (например, 178):", "height"),
            ProfileSetup.weight: ("Настройка профиля (4/9)", "Введи свой текущий вес в килограммах (например, 75.5):", "weight"),
            ProfileSetup.target_weight: ("Настройка профиля (5/9)", "Введи свой целевой вес в килограммах (например, 80):", "target_weight"),
            ProfileSetup.activity_level: ("Настройка профиля (6/9)", "Выбери свой уровень физической активности:", "activity_level"),
            ProfileSetup.experience_level: ("Настройка профиля (7/9)", "Выбери свой уровень опыта в тренировках:", "experience_level"),
            ProfileSetup.diet_type: ("Настройка профиля (8/9)", "Выбери свой тип питания:", "diet_type"),
            ProfileSetup.allergies: ("Настройка профиля (9/10)", "Укажи продукты, на которые у тебя аллергия (через запятую, или нажми 'Пропустить'):", "allergies"),
            ProfileSetup.has_gym: ("Настройка профиля (9/9)", "У тебя есть доступ к тренажерному залу?", "has_gym"),
        }
        
        title, text, keyboard = step_titles[prev_state]
        
        await callback.message.edit_text(
            f"<b>{title}</b>\n\n{text}",
            reply_markup=profile_setup_keyboard(keyboard)
        )
    
    await callback.answer()


async def get_user(session: AsyncSession, telegram_id: int) -> User:
    """
    Получить пользователя по telegram_id
    """
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    return user
