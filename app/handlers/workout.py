from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, date
import json

from app.models.user import User
from app.models.workout import Workout, WorkoutPlan, Exercise, MuscleGroup, ExerciseType, Equipment
from app.keyboards.inline import workout_menu_keyboard, back_keyboard, confirmation_keyboard, main_menu_keyboard
from app.utils.db import get_session
from app.services.workout_service import generate_workout_plan, get_exercises_for_user

router = Router()


class WorkoutStates(StatesGroup):
    """
    Состояния для работы с тренировками
    """
    waiting_for_workout_name = State()
    waiting_for_workout_description = State()
    waiting_for_workout_days = State()
    waiting_for_exercise_selection = State()
    waiting_for_workout_completion = State()
    waiting_for_workout_notes = State()


@router.callback_query(F.data == "workout_menu")
async def process_workout_menu(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Тренировки"
    """
    await callback.message.edit_text(
        "<b>🏋️‍♂️ Тренировки</b>\n\n"
        "Здесь ты можешь управлять своими тренировками, создавать новые планы и отслеживать прогресс.\n\n"
        "Выбери действие:",
        reply_markup=workout_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "my_workouts")
async def process_my_workouts(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Мои тренировки"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем активные планы тренировок пользователя
    result = await session.execute(
        select(WorkoutPlan)
        .where(WorkoutPlan.user_id == user.id, WorkoutPlan.is_active == True)
        .options(selectinload(WorkoutPlan.exercises))
    )
    
    workout_plans = result.scalars().all()
    
    if not workout_plans:
        # Если у пользователя нет активных планов тренировок
        await callback.message.edit_text(
            "<b>🏋️‍♂️ Мои тренировки</b>\n\n"
            "У тебя пока нет активных планов тренировок.\n\n"
            "Давай создадим новый план, который поможет тебе достичь твоих целей!",
            reply_markup=back_keyboard("workout_menu")
        )
        
        # Создаем кнопку для создания нового плана
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="➕ Создать план тренировок", callback_data="new_workout"))
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="workout_menu"))
        
        await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    else:
        # Если у пользователя есть активные планы тренировок
        text = "<b>🏋️‍♂️ Мои тренировки</b>\n\n"
        
        # Создаем клавиатуру с выбором планов тренировок
        builder = InlineKeyboardBuilder()
        
        for plan in workout_plans:
            text += f"<b>{plan.name}</b>\n"
            text += f"{plan.description or 'Без описания'}\n"
            text += f"Дней в неделю: {plan.days_per_week}\n"
            text += f"Количество упражнений: {len(plan.exercises)}\n\n"
            
            builder.row(InlineKeyboardButton(
                text=f"📝 {plan.name}",
                callback_data=f"view_workout_plan_{plan.id}"
            ))
        
        # Добавляем кнопку для создания нового плана
        builder.row(InlineKeyboardButton(text="➕ Создать новый план", callback_data="new_workout"))
        # Добавляем кнопку "Назад"
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="workout_menu"))
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data == "new_workout")
async def process_new_workout(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик кнопки "Новая тренировка"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Если у пользователя есть все необходимые данные для генерации плана
    if user.gender and user.height and user.weight and user.activity_level and user.experience_level and user.has_gym_access is not None:
        # Предлагаем два варианта: автоматическая генерация или ручное создание
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🤖 Автоматически", callback_data="generate_workout_plan"))
        builder.row(InlineKeyboardButton(text="✍️ Создать вручную", callback_data="create_workout_manual"))
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="workout_menu"))
        
        await callback.message.edit_text(
            "<b>➕ Новый план тренировок</b>\n\n"
            "Как ты хочешь создать план тренировок?",
            reply_markup=builder.as_markup()
        )
    else:
        # Если у пользователя не хватает данных для генерации плана
        await callback.message.edit_text(
            "<b>⚠️ Недостаточно данных</b>\n\n"
            "Для создания персонализированного плана тренировок мне нужна дополнительная информация о тебе.\n\n"
            "Пожалуйста, заполни свой профиль полностью, чтобы я мог предложить тебе оптимальный план.",
            reply_markup=back_keyboard("workout_menu")
        )
    
    await callback.answer()


@router.callback_query(F.data == "generate_workout_plan")
async def process_generate_workout_plan(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Автоматически"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Отправляем сообщение о генерации плана
    await callback.message.edit_text(
        "<b>🤖 Генерация плана тренировок</b>\n\n"
        "Пожалуйста, подожди, я создаю для тебя оптимальный план тренировок на основе твоих данных...",
        reply_markup=None
    )
    
    # Генерируем план тренировок
    workout_plan = await generate_workout_plan(session, user)
    
    if workout_plan:
        # Если план успешно создан, отображаем информацию о нем
        text = f"<b>✅ План тренировок создан!</b>\n\n"
        text += f"<b>{workout_plan.name}</b>\n"
        text += f"{workout_plan.description}\n\n"
        text += f"Дней в неделю: {workout_plan.days_per_week}\n"
        text += f"Количество упражнений: {len(workout_plan.exercises)}\n\n"
        text += f"Хочешь посмотреть детали плана или начать тренировку?"
        
        # Создаем клавиатуру с действиями
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="📋 Посмотреть план",
            callback_data=f"view_workout_plan_{workout_plan.id}"
        ))
        builder.row(InlineKeyboardButton(
            text="▶️ Начать тренировку",
            callback_data=f"start_workout_{workout_plan.id}"
        ))
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="workout_menu"))
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        # Если не удалось создать план
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "К сожалению, не удалось создать план тренировок автоматически.\n\n"
            "Попробуй создать план вручную или обратись в поддержку.",
            reply_markup=back_keyboard("workout_menu")
        )
    
    await callback.answer()


@router.callback_query(F.data == "create_workout_manual")
async def process_create_workout_manual(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Создать вручную"
    """
    # Устанавливаем состояние ожидания ввода названия тренировки
    await state.set_state(WorkoutStates.waiting_for_workout_name)
    
    await callback.message.edit_text(
        "<b>✍️ Создание плана тренировок</b>\n\n"
        "Введи название твоего нового плана тренировок:",
        reply_markup=back_keyboard("workout_menu")
    )
    await callback.answer()


@router.message(WorkoutStates.waiting_for_workout_name)
async def process_workout_name(message: Message, state: FSMContext):
    """
    Обработчик ввода названия тренировки
    """
    # Получаем название тренировки
    workout_name = message.text.strip()
    
    # Проверяем, что название не пустое и не слишком длинное
    if not workout_name or len(workout_name) > 100:
        await message.answer(
            "⚠️ Название тренировки должно быть от 1 до 100 символов. Попробуй еще раз:"
        )
        return
    
    # Сохраняем название тренировки в состоянии
    await state.update_data(workout_name=workout_name)
    
    # Переходим к следующему шагу - ввод описания
    await state.set_state(WorkoutStates.waiting_for_workout_description)
    
    await message.answer(
        "<b>✍️ Создание плана тренировок</b>\n\n"
        f"Отлично! Название плана: <b>{workout_name}</b>\n\n"
        "Теперь введи краткое описание плана (или отправь '🚫', чтобы пропустить этот шаг):",
        reply_markup=back_keyboard("workout_menu")
    )


@router.message(WorkoutStates.waiting_for_workout_description)
async def process_workout_description(message: Message, state: FSMContext):
    """
    Обработчик ввода описания тренировки
    """
    # Получаем описание тренировки
    workout_description = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот шаг
    if workout_description == "🚫":
        workout_description = None
    
    # Проверяем, что описание не слишком длинное
    if workout_description and len(workout_description) > 500:
        await message.answer(
            "⚠️ Описание тренировки должно быть не более 500 символов. Попробуй еще раз:"
        )
        return
    
    # Сохраняем описание тренировки в состоянии
    await state.update_data(workout_description=workout_description)
    
    # Переходим к следующему шагу - выбор количества дней
    await state.set_state(WorkoutStates.waiting_for_workout_days)
    
    # Создаем клавиатуру с выбором количества дней
    builder = InlineKeyboardBuilder()
    for days in [2, 3, 4, 5, 6]:
        builder.row(InlineKeyboardButton(text=f"{days} дня(ей) в неделю", callback_data=f"workout_days_{days}"))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="workout_menu"))
    
    await message.answer(
        "<b>✍️ Создание плана тренировок</b>\n\n"
        f"План: <b>{(await state.get_data())['workout_name']}</b>\n"
        f"Описание: {workout_description or 'Не указано'}\n\n"
        "Сколько дней в неделю ты планируешь тренироваться?",
        reply_markup=builder.as_markup()
    )


@router.callback_query(WorkoutStates.waiting_for_workout_days, F.data.startswith("workout_days_"))
async def process_workout_days(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик выбора количества дней тренировок в неделю
    """
    # Получаем количество дней
    workout_days = int(callback.data.split("_")[-1])
    
    # Сохраняем количество дней в состоянии
    await state.update_data(workout_days=workout_days)
    
    # Получаем данные из состояния
    data = await state.get_data()
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Создаем план тренировок в базе данных
    workout_plan = WorkoutPlan(
        user_id=user.id,
        name=data["workout_name"],
        description=data.get("workout_description"),
        days_per_week=workout_days,
        is_active=True
    )
    
    session.add(workout_plan)
    await session.commit()
    await session.refresh(workout_plan)
    
    # Переходим к следующему шагу - выбор упражнений
    await state.update_data(workout_plan_id=workout_plan.id)
    await state.set_state(WorkoutStates.waiting_for_exercise_selection)
    
    # Получаем упражнения, подходящие для пользователя
    exercises = await get_exercises_for_user(session, user)
    
    # Группируем упражнения по группам мышц
    exercise_groups = {}
    for exercise in exercises:
        group = exercise.muscle_group.value
        if group not in exercise_groups:
            exercise_groups[group] = []
        exercise_groups[group].append(exercise)
    
    # Создаем клавиатуру с выбором групп мышц
    builder = InlineKeyboardBuilder()
    for group in MuscleGroup:
        if group.value in exercise_groups:
            builder.row(InlineKeyboardButton(
                text=f"{group_emoji(group)} {group_name(group)}",
                callback_data=f"select_muscle_group_{group.value}"
            ))
    
    # Добавляем кнопку для завершения выбора упражнений
    builder.row(InlineKeyboardButton(text="✅ Завершить выбор", callback_data="finish_exercise_selection"))
    
    # Добавляем кнопку "Назад"
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="workout_menu"))
    
    await callback.message.edit_text(
        "<b>✍️ Создание плана тренировок</b>\n\n"
        f"План: <b>{data['workout_name']}</b>\n"
        f"Дней в неделю: {workout_days}\n\n"
        "Теперь выбери группы мышц и упражнения для твоего плана:",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.callback_query(WorkoutStates.waiting_for_exercise_selection, F.data.startswith("select_muscle_group_"))
async def process_select_muscle_group(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик выбора группы мышц
    """
    # Получаем группу мышц
    muscle_group = callback.data.split("_")[-1]
    
    # Получаем данные из состояния
    data = await state.get_data()
    workout_plan_id = data["workout_plan_id"]
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем упражнения для выбранной группы мышц
    result = await session.execute(
        select(Exercise).where(Exercise.muscle_group == MuscleGroup(muscle_group))
    )
    exercises = result.scalars().all()
    
    # Получаем уже выбранные упражнения для плана
    workout_plan = await session.get(WorkoutPlan, workout_plan_id, options=[selectinload(WorkoutPlan.exercises)])
    selected_exercise_ids = [exercise.id for exercise in workout_plan.exercises]
    
    # Создаем клавиатуру с выбором упражнений
    builder = InlineKeyboardBuilder()
    for exercise in exercises:
        # Отмечаем упражнения, которые уже выбраны
        prefix = "✅" if exercise.id in selected_exercise_ids else ""
        
        builder.row(InlineKeyboardButton(
            text=f"{prefix} {exercise.name} ({equipment_name(exercise.equipment)})",
            callback_data=f"toggle_exercise_{exercise.id}"
        ))
    
    # Добавляем кнопку "Назад к группам мышц"
    builder.row(InlineKeyboardButton(text="🔙 Назад к группам мышц", callback_data="back_to_muscle_groups"))
    
    await callback.message.edit_text(
        f"<b>✍️ Выбор упражнений: {group_emoji(MuscleGroup(muscle_group))} {group_name(MuscleGroup(muscle_group))}</b>\n\n"
        f"Выбери упражнения для твоего плана тренировок.\n"
        f"Упражнения, отмеченные ✅, уже добавлены в твой план.",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.callback_query(WorkoutStates.waiting_for_exercise_selection, F.data.startswith("toggle_exercise_"))
async def process_toggle_exercise(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик выбора упражнения
    """
    # Получаем id упражнения
    exercise_id = int(callback.data.split("_")[-1])
    
    # Получаем данные из состояния
    data = await state.get_data()
    workout_plan_id = data["workout_plan_id"]
    
    # Получаем план тренировок и упражнение
    workout_plan = await session.get(WorkoutPlan, workout_plan_id, options=[selectinload(WorkoutPlan.exercises)])
    exercise = await session.get(Exercise, exercise_id)
    
    # Проверяем, выбрано ли уже это упражнение
    selected_exercise_ids = [ex.id for ex in workout_plan.exercises]
    
    if exercise_id in selected_exercise_ids:
        # Если упражнение уже выбрано, удаляем его из плана
        workout_plan.exercises = [ex for ex in workout_plan.exercises if ex.id != exercise_id]
        await session.commit()
        await callback.answer("Упражнение удалено из плана")
    else:
        # Если упражнение не выбрано, добавляем его в план
        workout_plan.exercises.append(exercise)
        await session.commit()
        await callback.answer("Упражнение добавлено в план")
    
    # Обновляем сообщение с выбором упражнений для этой группы мышц
    muscle_group = exercise.muscle_group.value
    
    # Получаем упражнения для этой группы мышц
    result = await session.execute(
        select(Exercise).where(Exercise.muscle_group == exercise.muscle_group)
    )
    exercises = result.scalars().all()
    
    # Обновляем список выбранных упражнений
    selected_exercise_ids = [ex.id for ex in workout_plan.exercises]
    
    # Создаем клавиатуру с выбором упражнений
    builder = InlineKeyboardBuilder()
    for ex in exercises:
        # Отмечаем упражнения, которые уже выбраны
        prefix = "✅" if ex.id in selected_exercise_ids else ""
        
        builder.row(InlineKeyboardButton(
            text=f"{prefix} {ex.name} ({equipment_name(ex.equipment)})",
            callback_data=f"toggle_exercise_{ex.id}"
        ))
    
    # Добавляем кнопку "Назад к группам мышц"
    builder.row(InlineKeyboardButton(text="🔙 Назад к группам мышц", callback_data="back_to_muscle_groups"))
    
    await callback.message.edit_text(
        f"<b>✍️ Выбор упражнений: {group_emoji(exercise.muscle_group)} {group_name(exercise.muscle_group)}</b>\n\n"
        f"Выбери упражнения для твоего плана тренировок.\n"
        f"Упражнения, отмеченные ✅, уже добавлены в твой план.",
        reply_markup=builder.as_markup()
    )


@router.callback_query(WorkoutStates.waiting_for_exercise_selection, F.data == "back_to_muscle_groups")
async def process_back_to_muscle_groups(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик кнопки "Назад к группам мышц"
    """
    # Получаем данные из состояния
    data = await state.get_data()
    workout_plan_id = data["workout_plan_id"]
    
    # Получаем пользователя и план тренировок
    user = await get_user(session, callback.from_user.id)
    workout_plan = await session.get(WorkoutPlan, workout_plan_id)
    
    # Получаем упражнения, подходящие для пользователя
    exercises = await get_exercises_for_user(session, user)
    
    # Группируем упражнения по группам мышц
    exercise_groups = {}
    for exercise in exercises:
        group = exercise.muscle_group.value
        if group not in exercise_groups:
            exercise_groups[group] = []
        exercise_groups[group].append(exercise)
    
    # Создаем клавиатуру с выбором групп мышц
    builder = InlineKeyboardBuilder()
    for group in MuscleGroup:
        if group.value in exercise_groups:
            builder.row(InlineKeyboardButton(
                text=f"{group_emoji(group)} {group_name(group)}",
                callback_data=f"select_muscle_group_{group.value}"
            ))
    
    # Добавляем кнопку для завершения выбора упражнений
    builder.row(InlineKeyboardButton(text="✅ Завершить выбор", callback_data="finish_exercise_selection"))
    
    # Добавляем кнопку "Назад"
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="workout_menu"))
    
    await callback.message.edit_text(
        "<b>✍️ Создание плана тренировок</b>\n\n"
        f"План: <b>{workout_plan.name}</b>\n"
        f"Дней в неделю: {workout_plan.days_per_week}\n\n"
        "Выбери группы мышц и упражнения для твоего плана:",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.callback_query(WorkoutStates.waiting_for_exercise_selection, F.data == "finish_exercise_selection")
async def process_finish_exercise_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик кнопки "Завершить выбор"
    """
    # Получаем данные из состояния
    data = await state.get_data()
    workout_plan_id = data["workout_plan_id"]
    
    # Получаем план тренировок
    workout_plan = await session.get(WorkoutPlan, workout_plan_id, options=[selectinload(WorkoutPlan.exercises)])
    
    # Проверяем, что выбрано хотя бы одно упражнение
    if not workout_plan.exercises:
        await callback.answer("⚠️ Выбери хотя бы одно упражнение")
        return
    
    # Очищаем состояние
    await state.clear()
    
    # Отображаем информацию о созданном плане тренировок
    text = "<b>✅ План тренировок успешно создан!</b>\n\n"
    text += f"<b>{workout_plan.name}</b>\n"
    text += f"{workout_plan.description or 'Без описания'}\n\n"
    text += f"Дней в неделю: {workout_plan.days_per_week}\n"
    text += f"Количество упражнений: {len(workout_plan.exercises)}\n\n"
    
    # Группируем упражнения по группам мышц
    exercise_groups = {}
    for exercise in workout_plan.exercises:
        group = exercise.muscle_group.value
        if group not in exercise_groups:
            exercise_groups[group] = []
        exercise_groups[group].append(exercise)
    
    # Выводим список упражнений по группам мышц
    for group in MuscleGroup:
        if group.value in exercise_groups:
            text += f"\n<b>{group_emoji(group)} {group_name(group)}:</b>\n"
            for exercise in exercise_groups[group.value]:
                text += f"• {exercise.name}\n"
    
    # Создаем клавиатуру с действиями
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="▶️ Начать тренировку",
        callback_data=f"start_workout_{workout_plan.id}"
    ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="workout_menu"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer("План тренировок успешно создан!")


@router.callback_query(F.data.startswith("view_workout_plan_"))
async def process_view_workout_plan(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик просмотра плана тренировок
    """
    # Получаем id плана тренировок
    workout_plan_id = int(callback.data.split("_")[-1])
    
    # Получаем план тренировок
    workout_plan = await session.get(WorkoutPlan, workout_plan_id, options=[selectinload(WorkoutPlan.exercises)])
    
    if not workout_plan:
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "План тренировок не найден.",
            reply_markup=back_keyboard("workout_menu")
        )
        await callback.answer()
        return
    
    # Формируем текст с информацией о плане тренировок
    text = f"<b>🏋️‍♂️ План тренировок: {workout_plan.name}</b>\n\n"
    text += f"{workout_plan.description or 'Без описания'}\n\n"
    text += f"Дней в неделю: {workout_plan.days_per_week}\n"
    text += f"Количество упражнений: {len(workout_plan.exercises)}\n\n"
    
    # Группируем упражнения по группам мышц
    exercise_groups = {}
    for exercise in workout_plan.exercises:
        group = exercise.muscle_group.value
        if group not in exercise_groups:
            exercise_groups[group] = []
        exercise_groups[group].append(exercise)
    
    # Выводим список упражнений по группам мышц
    for group in MuscleGroup:
        if group.value in exercise_groups:
            text += f"\n<b>{group_emoji(group)} {group_name(group)}:</b>\n"
            for exercise in exercise_groups[group.value]:
                text += f"• {exercise.name}\n"
    
    # Создаем клавиатуру с действиями
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="▶️ Начать тренировку",
        callback_data=f"start_workout_{workout_plan.id}"
    ))
    builder.row(InlineKeyboardButton(
        text="✏️ Редактировать",
        callback_data=f"edit_workout_plan_{workout_plan.id}"
    ))
    builder.row(InlineKeyboardButton(
        text="🗑️ Удалить",
        callback_data=f"delete_workout_plan_{workout_plan.id}"
    ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="my_workouts"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data.startswith("delete_workout_plan_"))
async def process_delete_workout_plan(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик удаления плана тренировок
    """
    # Получаем id плана тренировок
    workout_plan_id = int(callback.data.split("_")[-1])
    
    # Получаем план тренировок
    workout_plan = await session.get(WorkoutPlan, workout_plan_id)
    
    if not workout_plan:
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "План тренировок не найден.",
            reply_markup=back_keyboard("workout_menu")
        )
        await callback.answer()
        return
    
    # Создаем клавиатуру для подтверждения удаления
    await callback.message.edit_text(
        f"<b>🗑️ Удаление плана тренировок</b>\n\n"
        f"Ты действительно хочешь удалить план <b>{workout_plan.name}</b>?",
        reply_markup=confirmation_keyboard(f"delete_plan_{workout_plan_id}")
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_plan_"))
async def process_confirm_delete_plan(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик подтверждения удаления плана тренировок
    """
    # Получаем id плана тренировок
    workout_plan_id = int(callback.data.split("_")[-1])
    
    # Удаляем план тренировок
    await session.execute(
        delete(WorkoutPlan).where(WorkoutPlan.id == workout_plan_id)
    )
    await session.commit()
    
    # Возвращаемся к списку планов тренировок
    await process_my_workouts(callback, session)
    
    await callback.answer("План тренировок удален")


@router.callback_query(F.data.startswith("cancel_delete_plan_"))
async def process_cancel_delete_plan(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик отмены удаления плана тренировок
    """
    # Получаем id плана тренировок
    workout_plan_id = int(callback.data.split("_")[-1])
    
    # Возвращаемся к просмотру плана тренировок
    await process_view_workout_plan(CallbackQuery(
        id=callback.id,
        from_user=callback.from_user,
        chat_instance=callback.chat_instance,
        message=callback.message,
        data=f"view_workout_plan_{workout_plan_id}"
    ), session)
    
    await callback.answer()


@router.callback_query(F.data.startswith("start_workout_"))
async def process_start_workout(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик начала тренировки
    """
    # Получаем id плана тренировок
    workout_plan_id = int(callback.data.split("_")[-1])
    
    # Получаем план тренировок
    workout_plan = await session.get(WorkoutPlan, workout_plan_id, options=[selectinload(WorkoutPlan.exercises)])
    
    if not workout_plan or not workout_plan.exercises:
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "План тренировок не найден или не содержит упражнений.",
            reply_markup=back_keyboard("workout_menu")
        )
        await callback.answer()
        return
    
    # Создаем новую запись о тренировке
    user = await get_user(session, callback.from_user.id)
    workout = Workout(
        user_id=user.id,
        workout_plan_id=workout_plan.id,
        date=date.today(),
        completed=False
    )
    
    session.add(workout)
    await session.commit()
    await session.refresh(workout)
    
    # Сохраняем id тренировки в состоянии
    await state.update_data(workout_id=workout.id)
    
    # Отображаем первое упражнение
    await display_workout_exercise(callback.message, workout_plan, 0, workout.id, session)
    
    # Устанавливаем состояние ожидания завершения тренировки
    await state.set_state(WorkoutStates.waiting_for_workout_completion)
    
    await callback.answer("Тренировка начата!")


async def display_workout_exercise(message, workout_plan, exercise_index, workout_id, session):
    """
    Отображает информацию об упражнении
    """
    # Получаем упражнения из плана тренировок
    exercises = workout_plan.exercises
    
    if not exercises or exercise_index >= len(exercises):
        # Если упражнений нет или индекс за пределами списка
        await message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "Упражнение не найдено.",
            reply_markup=back_keyboard("workout_menu")
        )
        return
    
    # Получаем текущее упражнение
    exercise = exercises[exercise_index]
    
    # Формируем текст с информацией об упражнении
    text = f"<b>🏋️‍♂️ Тренировка: {workout_plan.name}</b>\n"
    text += f"Упражнение {exercise_index + 1} из {len(exercises)}\n\n"
    text += f"<b>{exercise.name}</b>\n"
    text += f"Группа мышц: {group_emoji(exercise.muscle_group)} {group_name(exercise.muscle_group)}\n"
    text += f"Оборудование: {equipment_name(exercise.equipment)}\n\n"
    
    # Рекомендации по подходам и повторениям
    text += f"<b>Рекомендуемые параметры:</b>\n"
    text += f"Подходы: 3-4\n"
    text += f"Повторения: 8-12\n"
    text += f"Отдых между подходами: 1-2 минуты\n\n"
    
    if exercise.instructions:
        text += f"<b>Инструкция:</b>\n{exercise.instructions}\n\n"
    
    # Создаем клавиатуру для навигации между упражнениями
    builder = InlineKeyboardBuilder()
    
    # Если есть предыдущее упражнение, добавляем кнопку "Назад"
    if exercise_index > 0:
        builder.row(InlineKeyboardButton(
            text="⬅️ Предыдущее",
            callback_data=f"prev_exercise_{workout_id}_{exercise_index}"
        ))
    
    # Если есть следующее упражнение, добавляем кнопку "Далее"
    if exercise_index < len(exercises) - 1:
        builder.row(InlineKeyboardButton(
            text="➡️ Следующее",
            callback_data=f"next_exercise_{workout_id}_{exercise_index}"
        ))
    else:
        # Если это последнее упражнение, добавляем кнопку "Завершить тренировку"
        builder.row(InlineKeyboardButton(
            text="✅ Завершить тренировку",
            callback_data=f"complete_workout_{workout_id}"
        ))
    
    # Добавляем кнопку для просмотра видео/инструкции
    if exercise.video_url:
        builder.row(InlineKeyboardButton(
            text="📹 Смотреть видео",
            url=exercise.video_url
        ))
    
    # Добавляем кнопку для отмены тренировки
    builder.row(InlineKeyboardButton(
        text="❌ Отменить тренировку",
        callback_data=f"cancel_workout_{workout_id}"
    ))
    
    await message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("next_exercise_"))
async def process_next_exercise(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик перехода к следующему упражнению
    """
    # Получаем id тренировки и индекс текущего упражнения
    parts = callback.data.split("_")
    workout_id = int(parts[2])
    current_index = int(parts[3])
    
    # Получаем тренировку и план тренировок
    workout = await session.get(Workout, workout_id)
    workout_plan = await session.get(WorkoutPlan, workout.workout_plan_id, options=[selectinload(WorkoutPlan.exercises)])
    
    # Отображаем следующее упражнение
    await display_workout_exercise(callback.message, workout_plan, current_index + 1, workout_id, session)
    
    await callback.answer()


@router.callback_query(F.data.startswith("prev_exercise_"))
async def process_prev_exercise(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик перехода к предыдущему упражнению
    """
    # Получаем id тренировки и индекс текущего упражнения
    parts = callback.data.split("_")
    workout_id = int(parts[2])
    current_index = int(parts[3])
    
    # Получаем тренировку и план тренировок
    workout = await session.get(Workout, workout_id)
    workout_plan = await session.get(WorkoutPlan, workout.workout_plan_id, options=[selectinload(WorkoutPlan.exercises)])
    
    # Отображаем предыдущее упражнение
    await display_workout_exercise(callback.message, workout_plan, current_index - 1, workout_id, session)
    
    await callback.answer()


@router.callback_query(F.data.startswith("complete_workout_"))
async def process_complete_workout(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик завершения тренировки
    """
    # Получаем id тренировки
    workout_id = int(callback.data.split("_")[-1])
    
    # Получаем тренировку
    workout = await session.get(Workout, workout_id)
    
    if not workout:
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "Тренировка не найдена.",
            reply_markup=back_keyboard("workout_menu")
        )
        await callback.answer()
        return
    
    # Устанавливаем состояние ожидания ввода заметок о тренировке
    await state.update_data(workout_id=workout_id)
    await state.set_state(WorkoutStates.waiting_for_workout_notes)
    
    await callback.message.edit_text(
        "<b>✅ Тренировка завершена!</b>\n\n"
        "Ты можешь добавить заметки о тренировке (например, как ты себя чувствовал, "
        "какие веса использовал, какие упражнения были сложными и т.д.).\n\n"
        "Введи свои заметки или отправь '🚫', чтобы пропустить этот шаг:",
        reply_markup=None
    )
    
    await callback.answer("Тренировка завершена!")


@router.message(WorkoutStates.waiting_for_workout_notes)
async def process_workout_notes(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик ввода заметок о тренировке
    """
    # Получаем заметки
    notes = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот шаг
    if notes == "🚫":
        notes = None
    
    # Получаем id тренировки из состояния
    data = await state.get_data()
    workout_id = data["workout_id"]
    
    # Получаем тренировку
    workout = await session.get(Workout, workout_id)
    
    if not workout:
        await message.answer(
            "<b>❌ Ошибка</b>\n\n"
            "Тренировка не найдена.",
            reply_markup=back_keyboard("workout_menu")
        )
        return
    
    # Обновляем тренировку в базе данных
    workout.completed = True
    workout.notes = notes
    workout.duration = 60  # Примерная длительность тренировки в минутах
    
    await session.commit()
    
    # Очищаем состояние
    await state.clear()
    
    # Отображаем сообщение об успешном завершении тренировки
    await message.answer(
        "<b>🎉 Тренировка успешно завершена и сохранена!</b>\n\n"
        "Поздравляю с хорошей тренировкой! Продолжай в том же духе!\n\n"
        "Что ты хочешь сделать дальше?",
        reply_markup=main_menu_keyboard()
    )


@router.callback_query(F.data.startswith("cancel_workout_"))
async def process_cancel_workout(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик отмены тренировки
    """
    # Получаем id тренировки
    workout_id = int(callback.data.split("_")[-1])
    
    # Удаляем тренировку из базы данных
    await session.execute(
        delete(Workout).where(Workout.id == workout_id)
    )
    await session.commit()
    
    # Очищаем состояние
    await state.clear()
    
    # Возвращаемся в меню тренировок
    await process_workout_menu(callback, session)
    
    await callback.answer("Тренировка отменена")


@router.callback_query(F.data == "workout_history")
async def process_workout_history(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "История тренировок"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем историю тренировок пользователя (последние 10)
    result = await session.execute(
        select(Workout)
        .where(Workout.user_id == user.id, Workout.completed == True)
        .order_by(Workout.date.desc())
        .limit(10)
    )
    
    workouts = result.scalars().all()
    
    if not workouts:
        # Если у пользователя нет завершенных тренировок
        await callback.message.edit_text(
            "<b>📝 История тренировок</b>\n\n"
            "У тебя пока нет завершенных тренировок.",
            reply_markup=back_keyboard("workout_menu")
        )
    else:
        # Если у пользователя есть завершенные тренировки
        text = "<b>📝 История тренировок</b>\n\n"
        
        # Создаем клавиатуру с выбором тренировок
        builder = InlineKeyboardBuilder()
        
        for workout in workouts:
            # Получаем название плана тренировок
            if workout.workout_plan_id:
                workout_plan = await session.get(WorkoutPlan, workout.workout_plan_id)
                plan_name = workout_plan.name if workout_plan else "Неизвестный план"
            else:
                plan_name = "Произвольная тренировка"
            
            # Форматируем дату
            formatted_date = workout.date.strftime("%d.%m.%Y")
            
            text += f"<b>{formatted_date}</b> - {plan_name}\n"
            
            builder.row(InlineKeyboardButton(
                text=f"📝 {formatted_date} - {plan_name}",
                callback_data=f"view_workout_{workout.id}"
            ))
        
        # Добавляем кнопку "Назад"
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="workout_menu"))
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data.startswith("view_workout_"))
async def process_view_workout(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик просмотра тренировки
    """
    # Получаем id тренировки
    workout_id = int(callback.data.split("_")[-1])
    
    # Получаем тренировку
    workout = await session.get(Workout, workout_id)
    
    if not workout:
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "Тренировка не найдена.",
            reply_markup=back_keyboard("workout_menu")
        )
        await callback.answer()
        return
    
    # Получаем план тренировок
    workout_plan = await session.get(WorkoutPlan, workout.workout_plan_id) if workout.workout_plan_id else None
    
    # Формируем текст с информацией о тренировке
    text = f"<b>📝 Тренировка от {workout.date.strftime('%d.%m.%Y')}</b>\n\n"
    
    if workout_plan:
        text += f"План: <b>{workout_plan.name}</b>\n"
    else:
        text += f"Произвольная тренировка\n"
    
    text += f"Длительность: {workout.duration or 'Не указана'} минут\n"
    text += f"Статус: {'✅ Завершена' if workout.completed else '❌ Не завершена'}\n\n"
    
    if workout.exercises_data:
        # Если есть данные об упражнениях
        exercises_data = json.loads(workout.exercises_data)
        text += f"<b>Выполненные упражнения:</b>\n"
        
        for exercise_data in exercises_data:
            text += f"• {exercise_data['name']}: {exercise_data['sets']} подходов x {exercise_data['reps']} повторений\n"
    
    if workout.notes:
        text += f"\n<b>Заметки:</b>\n{workout.notes}\n"
    
    # Создаем клавиатуру с действиями
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопку "Повторить тренировку", если есть план
    if workout.workout_plan_id:
        builder.row(InlineKeyboardButton(
            text="🔄 Повторить тренировку",
            callback_data=f"start_workout_{workout.workout_plan_id}"
        ))
    
    # Добавляем кнопку "Назад"
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="workout_history"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data == "workout_stats")
async def process_workout_stats(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Статистика"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем статистику тренировок пользователя
    result = await session.execute(
        select(Workout)
        .where(Workout.user_id == user.id, Workout.completed == True)
    )
    
    workouts = result.scalars().all()
    
    if not workouts:
        # Если у пользователя нет завершенных тренировок
        await callback.message.edit_text(
            "<b>📊 Статистика тренировок</b>\n\n"
            "У тебя пока нет данных для статистики.\n\n"
            "Начни тренироваться, чтобы увидеть свой прогресс!",
            reply_markup=back_keyboard("workout_menu")
        )
    else:
        # Если у пользователя есть завершенные тренировки
        total_workouts = len(workouts)
        total_duration = sum(workout.duration or 0 for workout in workouts)
        
        # Считаем количество тренировок за последние 7 и 30 дней
        today = date.today()
        last_week = today - timedelta(days=7)
        last_month = today - timedelta(days=30)
        
        workouts_last_week = len([w for w in workouts if w.date >= last_week])
        workouts_last_month = len([w for w in workouts if w.date >= last_month])
        
        # Формируем текст с статистикой
        text = "<b>📊 Статистика тренировок</b>\n\n"
        text += f"Всего тренировок: {total_workouts}\n"
        text += f"Общая длительность: {total_duration} минут\n\n"
        text += f"Тренировок за последние 7 дней: {workouts_last_week}\n"
        text += f"Тренировок за последние 30 дней: {workouts_last_month}\n\n"
        
        # Вычисляем наиболее частые группы мышц
        muscle_groups = {}
        
        for workout in workouts:
            if workout.workout_plan_id:
                workout_plan = await session.get(WorkoutPlan, workout.workout_plan_id, options=[selectinload(WorkoutPlan.exercises)])
                if workout_plan:
                    for exercise in workout_plan.exercises:
                        group = exercise.muscle_group.value
                        muscle_groups[group] = muscle_groups.get(group, 0) + 1
        
        if muscle_groups:
            # Сортируем группы мышц по частоте
            sorted_groups = sorted(muscle_groups.items(), key=lambda x: x[1], reverse=True)
            
            text += f"<b>Наиболее тренируемые группы мышц:</b>\n"
            for group, count in sorted_groups[:3]:
                text += f"• {group_emoji(MuscleGroup(group))} {group_name(MuscleGroup(group))}: {count} раз\n"
        
        # Создаем клавиатуру с действиями
        builder = InlineKeyboardBuilder()
        
        # Добавляем кнопку "Детальная статистика" (если нужно)
        # builder.row(InlineKeyboardButton(
        #     text="📈 Детальная статистика",
        #     callback_data="detailed_workout_stats"
        # ))
        
        # Добавляем кнопку "Назад"
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="workout_menu"))
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


async def get_user(session: AsyncSession, telegram_id: int) -> User:
    """
    Получить пользователя по telegram_id
    """
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    return user


# Вспомогательные функции для форматирования имен групп мышц и типов оборудования

def group_emoji(muscle_group: MuscleGroup) -> str:
    """
    Возвращает эмодзи для группы мышц
    """
    emoji_map = {
        MuscleGroup.CHEST: "💪",
        MuscleGroup.BACK: "🔙",
        MuscleGroup.LEGS: "🦵",
        MuscleGroup.SHOULDERS: "🔄",
        MuscleGroup.BICEPS: "💪",
        MuscleGroup.TRICEPS: "💪",
        MuscleGroup.ABS: "🧠",
        MuscleGroup.CALVES: "🦵",
        MuscleGroup.FOREARMS: "💪",
        MuscleGroup.FULL_BODY: "🏋️‍♂️",
    }
    return emoji_map.get(muscle_group, "❓")


def group_name(muscle_group: MuscleGroup) -> str:
    """
    Возвращает название группы мышц на русском
    """
    name_map = {
        MuscleGroup.CHEST: "Грудные",
        MuscleGroup.BACK: "Спина",
        MuscleGroup.LEGS: "Ноги",
        MuscleGroup.SHOULDERS: "Плечи",
        MuscleGroup.BICEPS: "Бицепс",
        MuscleGroup.TRICEPS: "Трицепс",
        MuscleGroup.ABS: "Пресс",
        MuscleGroup.CALVES: "Икры",
        MuscleGroup.FOREARMS: "Предплечья",
        MuscleGroup.FULL_BODY: "Все тело",
    }
    return name_map.get(muscle_group, str(muscle_group))


def equipment_name(equipment: Equipment) -> str:
    """
    Возвращает название оборудования на русском
    """
    name_map = {
        Equipment.NONE: "Без оборудования",
        Equipment.DUMBBELLS: "Гантели",
        Equipment.BARBELL: "Штанга",
        Equipment.KETTLEBELL: "Гиря",
        Equipment.CABLE: "Трос",
        Equipment.MACHINE: "Тренажер",
        Equipment.BANDS: "Резиновые ленты",
    }
    return name_map.get(equipment, str(equipment))
