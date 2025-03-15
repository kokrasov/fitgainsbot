from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from datetime import datetime, date
import json

from app.models.user import User
from app.models.nutrition import NutritionPlan, Meal, MealType, Recipe, Product
from app.keyboards.inline import nutrition_menu_keyboard, back_keyboard, confirmation_keyboard, main_menu_keyboard
from app.utils.db import get_session
from app.services.nutrition_service import generate_nutrition_plan, calculate_calories_and_macros

router = Router()


class NutritionStates(StatesGroup):
    """
    Состояния для работы с питанием
    """
    waiting_for_nutrition_name = State()
    waiting_for_nutrition_description = State()
    waiting_for_meal_selection = State()
    waiting_for_recipe_selection = State()
    waiting_for_manual_calories = State()
    waiting_for_manual_protein = State()
    waiting_for_manual_fat = State()
    waiting_for_manual_carbs = State()


@router.callback_query(F.data == "nutrition_menu")
async def process_nutrition_menu(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Питание"
    """
    await callback.message.edit_text(
        "<b>🍽️ Питание</b>\n\n"
        "Здесь ты можешь управлять своим планом питания, создавать новые планы и искать рецепты.\n\n"
        "Выбери действие:",
        reply_markup=nutrition_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "my_nutrition_plan")
async def process_my_nutrition_plan(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Мой план питания"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем активный план питания пользователя
    result = await session.execute(
        select(NutritionPlan)
        .where(NutritionPlan.user_id == user.id, NutritionPlan.is_active == True)
        .options(selectinload(NutritionPlan.meals).selectinload(Meal.recipes))
        .order_by(NutritionPlan.created_at.desc())
    )
    
    nutrition_plan = result.scalar_one_or_none()
    
    if not nutrition_plan:
        # Если у пользователя нет активного плана питания
        await callback.message.edit_text(
            "<b>🍽️ Мой план питания</b>\n\n"
            "У тебя пока нет активного плана питания.\n\n"
            "Давай создадим новый план, который поможет тебе достичь твоих целей!",
            reply_markup=back_keyboard("nutrition_menu")
        )
        
        # Создаем кнопку для создания нового плана
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="➕ Создать план питания", callback_data="update_nutrition_plan"))
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="nutrition_menu"))
        
        await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    else:
        # Если у пользователя есть активный план питания
        text = f"<b>🍽️ Мой план питания: {nutrition_plan.name}</b>\n\n"
        text += f"{nutrition_plan.description or ''}\n\n"
        
        # Добавляем информацию о калориях и макросах
        text += f"<b>Целевые показатели:</b>\n"
        text += f"Калории: {nutrition_plan.calories_target} ккал\n"
        text += f"Белки: {nutrition_plan.protein_target} г\n"
        text += f"Жиры: {nutrition_plan.fat_target} г\n"
        text += f"Углеводы: {nutrition_plan.carbs_target} г\n\n"
        
        # Добавляем информацию о приемах пищи
        meals = nutrition_plan.meals
        
        if meals:
            text += f"<b>Приемы пищи:</b>\n"
            
            # Сортируем приемы пищи по типу
            meal_order = {
                MealType.BREAKFAST: 1,
                MealType.LUNCH: 2,
                MealType.DINNER: 3,
                MealType.SNACK: 4,
                MealType.PRE_WORKOUT: 5,
                MealType.POST_WORKOUT: 6
            }
            
            sorted_meals = sorted(meals, key=lambda m: meal_order.get(m.meal_type, 99))
            
            for meal in sorted_meals:
                # Получаем название типа приема пищи на русском
                meal_type_name = get_meal_type_name(meal.meal_type)
                
                text += f"\n<b>{meal_type_name}</b> ({meal.time or 'время не указано'}):\n"
                
                # Если есть рецепты в приеме пищи
                if meal.recipes:
                    for recipe in meal.recipes:
                        text += f"• {recipe.name}\n"
                else:
                    text += "Нет рецептов\n"
        else:
            text += "В плане питания пока нет приемов пищи."
        
        # Создаем клавиатуру с действиями
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="✏️ Редактировать план",
            callback_data=f"edit_nutrition_plan_{nutrition_plan.id}"
        ))
        builder.row(InlineKeyboardButton(
            text="🔄 Обновить план",
            callback_data="update_nutrition_plan"
        ))
        builder.row(InlineKeyboardButton(
            text="🗑️ Удалить план",
            callback_data=f"delete_nutrition_plan_{nutrition_plan.id}"
        ))
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="nutrition_menu"))
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data == "update_nutrition_plan")
async def process_update_nutrition_plan(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик кнопки "Обновить план питания"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Если у пользователя есть все необходимые данные для генерации плана
    if user.gender and user.height and user.weight and user.activity_level and user.diet_type:
        # Предлагаем два варианта: автоматическая генерация или ручное создание
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🤖 Автоматически", callback_data="generate_nutrition_plan"))
        builder.row(InlineKeyboardButton(text="✍️ Создать вручную", callback_data="create_nutrition_manual"))
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="nutrition_menu"))
        
        await callback.message.edit_text(
            "<b>➕ Новый план питания</b>\n\n"
            "Как ты хочешь создать план питания?",
            reply_markup=builder.as_markup()
        )
    else:
        # Если у пользователя не хватает данных для генерации плана
        await callback.message.edit_text(
            "<b>⚠️ Недостаточно данных</b>\n\n"
            "Для создания персонализированного плана питания мне нужна дополнительная информация о тебе.\n\n"
            "Пожалуйста, заполни свой профиль полностью, чтобы я мог предложить тебе оптимальный план.",
            reply_markup=back_keyboard("nutrition_menu")
        )
    
    await callback.answer()


@router.callback_query(F.data == "generate_nutrition_plan")
async def process_generate_nutrition_plan(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Автоматически"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Отправляем сообщение о генерации плана
    await callback.message.edit_text(
        "<b>🤖 Генерация плана питания</b>\n\n"
        "Пожалуйста, подожди, я создаю для тебя оптимальный план питания на основе твоих данных...",
        reply_markup=None
    )
    
    # Рассчитываем целевые показатели калорий и макронутриентов
    calories, macros = calculate_calories_and_macros(user)
    
    # Генерируем план питания
    nutrition_plan = await generate_nutrition_plan(session, user, calories, macros)
    
    if nutrition_plan:
        # Если план успешно создан, отображаем информацию о нем
        text = f"<b>✅ План питания создан!</b>\n\n"
        text += f"<b>{nutrition_plan.name}</b>\n"
        text += f"{nutrition_plan.description or ''}\n\n"
        
        # Добавляем информацию о калориях и макросах
        text += f"<b>Целевые показатели:</b>\n"
        text += f"Калории: {nutrition_plan.calories_target} ккал\n"
        text += f"Белки: {nutrition_plan.protein_target} г\n"
        text += f"Жиры: {nutrition_plan.fat_target} г\n"
        text += f"Углеводы: {nutrition_plan.carbs_target} г\n\n"
        
        # Добавляем информацию о приемах пищи
        meals = nutrition_plan.meals
        
        if meals:
            text += f"<b>Приемы пищи:</b>\n"
            
            # Сортируем приемы пищи по типу
            meal_order = {
                MealType.BREAKFAST: 1,
                MealType.LUNCH: 2,
                MealType.DINNER: 3,
                MealType.SNACK: 4,
                MealType.PRE_WORKOUT: 5,
                MealType.POST_WORKOUT: 6
            }
            
            sorted_meals = sorted(meals, key=lambda m: meal_order.get(m.meal_type, 99))
            
            for meal in sorted_meals:
                # Получаем название типа приема пищи на русском
                meal_type_name = get_meal_type_name(meal.meal_type)
                
                text += f"\n<b>{meal_type_name}</b> ({meal.time or 'время не указано'}):\n"
                
                # Если есть рецепты в приеме пищи
                if meal.recipes:
                    for recipe in meal.recipes:
                        text += f"• {recipe.name}\n"
                else:
                    text += "Нет рецептов\n"
        
        # Создаем клавиатуру с действиями
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="📋 Посмотреть подробнее",
            callback_data=f"view_nutrition_plan_{nutrition_plan.id}"
        ))
        builder.row(InlineKeyboardButton(
            text="✏️ Редактировать план",
            callback_data=f"edit_nutrition_plan_{nutrition_plan.id}"
        ))
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="nutrition_menu"))
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        # Если не удалось создать план
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "К сожалению, не удалось создать план питания автоматически.\n\n"
            "Попробуй создать план вручную или обратись в поддержку.",
            reply_markup=back_keyboard("nutrition_menu")
        )
    
    await callback.answer()


@router.callback_query(F.data == "create_nutrition_manual")
async def process_create_nutrition_manual(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Создать вручную"
    """
    # Устанавливаем состояние ожидания ввода названия плана питания
    await state.set_state(NutritionStates.waiting_for_nutrition_name)
    
    await callback.message.edit_text(
        "<b>✍️ Создание плана питания</b>\n\n"
        "Введи название твоего нового плана питания:",
        reply_markup=back_keyboard("nutrition_menu")
    )
    await callback.answer()


@router.message(NutritionStates.waiting_for_nutrition_name)
async def process_nutrition_name(message: Message, state: FSMContext):
    """
    Обработчик ввода названия плана питания
    """
    # Получаем название плана питания
    nutrition_name = message.text.strip()
    
    # Проверяем, что название не пустое и не слишком длинное
    if not nutrition_name or len(nutrition_name) > 100:
        await message.answer(
            "⚠️ Название плана питания должно быть от 1 до 100 символов. Попробуй еще раз:"
        )
        return
    
    # Сохраняем название плана питания в состоянии
    await state.update_data(nutrition_name=nutrition_name)
    
    # Переходим к следующему шагу - ввод описания
    await state.set_state(NutritionStates.waiting_for_nutrition_description)
    
    await message.answer(
        "<b>✍️ Создание плана питания</b>\n\n"
        f"Отлично! Название плана: <b>{nutrition_name}</b>\n\n"
        "Теперь введи краткое описание плана (или отправь '🚫', чтобы пропустить этот шаг):",
        reply_markup=back_keyboard("nutrition_menu")
    )


@router.message(NutritionStates.waiting_for_nutrition_description)
async def process_nutrition_description(message: Message, state: FSMContext):
    """
    Обработчик ввода описания плана питания
    """
    # Получаем описание плана питания
    nutrition_description = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот шаг
    if nutrition_description == "🚫":
        nutrition_description = None
    
    # Проверяем, что описание не слишком длинное
    if nutrition_description and len(nutrition_description) > 500:
        await message.answer(
            "⚠️ Описание плана питания должно быть не более 500 символов. Попробуй еще раз:"
        )
        return
    
    # Сохраняем описание плана питания в состоянии
    await state.update_data(nutrition_description=nutrition_description)
    
    # Переходим к следующему шагу - ввод целевых калорий
    await state.set_state(NutritionStates.waiting_for_manual_calories)
    
    await message.answer(
        "<b>✍️ Создание плана питания</b>\n\n"
        f"План: <b>{(await state.get_data())['nutrition_name']}</b>\n"
        f"Описание: {nutrition_description or 'Не указано'}\n\n"
        "Теперь укажи целевое количество калорий в день (например, 2500):",
        reply_markup=back_keyboard("nutrition_menu")
    )


@router.message(NutritionStates.waiting_for_manual_calories)
async def process_manual_calories(message: Message, state: FSMContext):
    """
    Обработчик ввода целевых калорий
    """
    try:
        # Парсим целевые калории
        calories = int(message.text.strip())
        
        # Проверяем, что значение в разумных пределах
        if calories < 1000 or calories > 5000:
            await message.answer(
                "⚠️ Целевое количество калорий должно быть в пределах от 1000 до 5000. Попробуй еще раз:"
            )
            return
        
        # Сохраняем целевые калории в состоянии
        await state.update_data(calories=calories)
        
        # Переходим к следующему шагу - ввод целевого белка
        await state.set_state(NutritionStates.waiting_for_manual_protein)
        
        await message.answer(
            "<b>✍️ Создание плана питания</b>\n\n"
            f"План: <b>{(await state.get_data())['nutrition_name']}</b>\n"
            f"Калории: {calories} ккал\n\n"
            "Теперь укажи целевое количество белка в граммах (например, 150):",
            reply_markup=back_keyboard("nutrition_menu")
        )
    except ValueError:
        await message.answer(
            "⚠️ Пожалуйста, введи целевое количество калорий числом (например, 2500):"
        )


@router.message(NutritionStates.waiting_for_manual_protein)
async def process_manual_protein(message: Message, state: FSMContext):
    """
    Обработчик ввода целевого белка
    """
    try:
        # Парсим целевой белок
        protein = int(message.text.strip())
        
        # Проверяем, что значение в разумных пределах
        if protein < 50 or protein > 300:
            await message.answer(
                "⚠️ Целевое количество белка должно быть в пределах от 50 до 300 грамм. Попробуй еще раз:"
            )
            return
        
        # Сохраняем целевой белок в состоянии
        await state.update_data(protein=protein)
        
        # Переходим к следующему шагу - ввод целевых жиров
        await state.set_state(NutritionStates.waiting_for_manual_fat)
        
        await message.answer(
            "<b>✍️ Создание плана питания</b>\n\n"
            f"План: <b>{(await state.get_data())['nutrition_name']}</b>\n"
            f"Калории: {(await state.get_data())['calories']} ккал\n"
            f"Белки: {protein} г\n\n"
            "Теперь укажи целевое количество жиров в граммах (например, 70):",
            reply_markup=back_keyboard("nutrition_menu")
        )
    except ValueError:
        await message.answer(
            "⚠️ Пожалуйста, введи целевое количество белка числом (например, 150):"
        )


@router.message(NutritionStates.waiting_for_manual_fat)
async def process_manual_fat(message: Message, state: FSMContext):
    """
    Обработчик ввода целевых жиров
    """
    try:
        # Парсим целевые жиры
        fat = int(message.text.strip())
        
        # Проверяем, что значение в разумных пределах
        if fat < 30 or fat > 150:
            await message.answer(
                "⚠️ Целевое количество жиров должно быть в пределах от 30 до 150 грамм. Попробуй еще раз:"
            )
            return
        
        # Сохраняем целевые жиры в состоянии
        await state.update_data(fat=fat)
        
        # Переходим к следующему шагу - ввод целевых углеводов
        await state.set_state(NutritionStates.waiting_for_manual_carbs)
        
        await message.answer(
            "<b>✍️ Создание плана питания</b>\n\n"
            f"План: <b>{(await state.get_data())['nutrition_name']}</b>\n"
            f"Калории: {(await state.get_data())['calories']} ккал\n"
            f"Белки: {(await state.get_data())['protein']} г\n"
            f"Жиры: {fat} г\n\n"
            "Теперь укажи целевое количество углеводов в граммах (например, 250):",
            reply_markup=back_keyboard("nutrition_menu")
        )
    except ValueError:
        await message.answer(
            "⚠️ Пожалуйста, введи целевое количество жиров числом (например, 70):"
        )


@router.message(NutritionStates.waiting_for_manual_carbs)
async def process_manual_carbs(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик ввода целевых углеводов
    """
    try:
        # Парсим целевые углеводы
        carbs = int(message.text.strip())
        
        # Проверяем, что значение в разумных пределах
        if carbs < 100 or carbs > 500:
            await message.answer(
                "⚠️ Целевое количество углеводов должно быть в пределах от 100 до 500 грамм. Попробуй еще раз:"
            )
            return
        
        # Сохраняем целевые углеводы в состоянии
        await state.update_data(carbs=carbs)
        
        # Получаем все данные из состояния
        data = await state.get_data()
        
        # Получаем пользователя
        user = await get_user(session, message.from_user.id)
        
        # Создаем план питания
        nutrition_plan = NutritionPlan(
            user_id=user.id,
            name=data["nutrition_name"],
            description=data.get("nutrition_description"),
            calories_target=data["calories"],
            protein_target=data["protein"],
            fat_target=data["fat"],
            carbs_target=data["carbs"],
            is_active=True
        )
        
        # Деактивируем предыдущие планы питания
        await session.execute(
            NutritionPlan.__table__.update()
            .where(NutritionPlan.user_id == user.id, NutritionPlan.id != nutrition_plan.id)
            .values(is_active=False)
        )
        
        # Сохраняем план питания в базе данных
        session.add(nutrition_plan)
        await session.commit()
        await session.refresh(nutrition_plan)
        
        # Очищаем состояние
        await state.clear()
        
        # Отображаем информацию о созданном плане питания
        await message.answer(
            f"<b>✅ План питания успешно создан!</b>\n\n"
            f"<b>{nutrition_plan.name}</b>\n"
            f"{nutrition_plan.description or ''}\n\n"
            f"<b>Целевые показатели:</b>\n"
            f"Калории: {nutrition_plan.calories_target} ккал\n"
            f"Белки: {nutrition_plan.protein_target} г\n"
            f"Жиры: {nutrition_plan.fat_target} г\n"
            f"Углеводы: {nutrition_plan.carbs_target} г\n\n"
            f"Теперь ты можешь добавить приемы пищи и рецепты в свой план.",
            reply_markup=main_menu_keyboard()
        )
    except ValueError:
        await message.answer(
            "⚠️ Пожалуйста, введи целевое количество углеводов числом (например, 250):"
        )


@router.callback_query(F.data.startswith("view_nutrition_plan_"))
async def process_view_nutrition_plan(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик просмотра плана питания
    """
    # Получаем id плана питания
    nutrition_plan_id = int(callback.data.split("_")[-1])
    
    # Получаем план питания
    nutrition_plan = await session.get(
        NutritionPlan, 
        nutrition_plan_id, 
        options=[selectinload(NutritionPlan.meals).selectinload(Meal.recipes)]
    )
    
    if not nutrition_plan:
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "План питания не найден.",
            reply_markup=back_keyboard("nutrition_menu")
        )
        await callback.answer()
        return
    
    # Формируем текст с информацией о плане питания
    text = f"<b>🍽️ План питания: {nutrition_plan.name}</b>\n\n"
    text += f"{nutrition_plan.description or ''}\n\n"
    
    # Добавляем информацию о калориях и макросах
    text += f"<b>Целевые показатели:</b>\n"
    text += f"Калории: {nutrition_plan.calories_target} ккал\n"
    text += f"Белки: {nutrition_plan.protein_target} г\n"
    text += f"Жиры: {nutrition_plan.fat_target} г\n"
    text += f"Углеводы: {nutrition_plan.carbs_target} г\n\n"
    
    # Добавляем информацию о приемах пищи
    meals = nutrition_plan.meals
    
    if meals:
        text += f"<b>Приемы пищи:</b>\n"
        
        # Сортируем приемы пищи по типу
        meal_order = {
            MealType.BREAKFAST: 1,
            MealType.LUNCH: 2,
            MealType.DINNER: 3,
            MealType.SNACK: 4,
            MealType.PRE_WORKOUT: 5,
            MealType.POST_WORKOUT: 6
        }
        
        sorted_meals = sorted(meals, key=lambda m: meal_order.get(m.meal_type, 99))
        
        for meal in sorted_meals:
            # Получаем название типа приема пищи на русском
            meal_type_name = get_meal_type_name(meal.meal_type)
            
            text += f"\n<b>{meal_type_name}</b> ({meal.time or 'время не указано'}):\n"
            
            # Если есть рецепты в приеме пищи
            if meal.recipes:
                for recipe in meal.recipes:
                    text += f"• {recipe.name}\n"
            else:
                text += "Нет рецептов\n"
    else:
        text += "В плане питания пока нет приемов пищи."
    
    # Создаем клавиатуру с действиями
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="✏️ Редактировать план",
        callback_data=f"edit_nutrition_plan_{nutrition_plan.id}"
    ))
    builder.row(InlineKeyboardButton(
        text="🗑️ Удалить план",
        callback_data=f"delete_nutrition_plan_{nutrition_plan.id}"
    ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="my_nutrition_plan"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data.startswith("delete_nutrition_plan_"))
async def process_delete_nutrition_plan(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик удаления плана питания
    """
    # Получаем id плана питания
    nutrition_plan_id = int(callback.data.split("_")[-1])
    
    # Получаем план питания
    nutrition_plan = await session.get(NutritionPlan, nutrition_plan_id)
    
    if not nutrition_plan:
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "План питания не найден.",
            reply_markup=back_keyboard("nutrition_menu")
        )
        await callback.answer()
        return
    
    # Создаем клавиатуру для подтверждения удаления
    await callback.message.edit_text(
        f"<b>🗑️ Удаление плана питания</b>\n\n"
        f"Ты действительно хочешь удалить план <b>{nutrition_plan.name}</b>?",
        reply_markup=confirmation_keyboard(f"delete_plan_{nutrition_plan_id}")
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_plan_"))
async def process_confirm_delete_plan(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик подтверждения удаления плана питания
    """
    # Получаем id плана питания
    nutrition_plan_id = int(callback.data.split("_")[-1])
    
    # Удаляем план питания
    await session.execute(
        delete(NutritionPlan).where(NutritionPlan.id == nutrition_plan_id)
    )
    await session.commit()
    
    # Возвращаемся к списку планов питания
    await process_my_nutrition_plan(callback, session)
    
    await callback.answer("План питания удален")


@router.callback_query(F.data.startswith("cancel_delete_plan_"))
async def process_cancel_delete_plan(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик отмены удаления плана питания
    """
    # Получаем id плана питания
    nutrition_plan_id = int(callback.data.split("_")[-1])
    
    # Возвращаемся к просмотру плана питания
    await process_view_nutrition_plan(CallbackQuery(
        id=callback.id,
        from_user=callback.from_user,
        chat_instance=callback.chat_instance,
        message=callback.message,
        data=f"view_nutrition_plan_{nutrition_plan_id}"
    ), session)
    
    await callback.answer()


@router.callback_query(F.data == "search_recipes")
async def process_search_recipes(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Поиск рецептов"
    """
    # Получаем все рецепты (в будущем можно добавить фильтрацию)
    result = await session.execute(select(Recipe).limit(20))
    recipes = result.scalars().all()
    
    if not recipes:
        await callback.message.edit_text(
            "<b>🔍 Поиск рецептов</b>\n\n"
            "К сожалению, в базе данных пока нет рецептов.",
            reply_markup=back_keyboard("nutrition_menu")
        )
    else:
        text = "<b>🔍 Поиск рецептов</b>\n\n"
        text += "Выбери рецепт для просмотра:"
        
        # Создаем клавиатуру с рецептами
        builder = InlineKeyboardBuilder()
        
        for recipe in recipes:
            builder.row(InlineKeyboardButton(
                text=recipe.name,
                callback_data=f"view_recipe_{recipe.id}"
            ))
        
        # Добавляем кнопку "Назад"
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="nutrition_menu"))
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data.startswith("view_recipe_"))
async def process_view_recipe(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик просмотра рецепта
    """
    # Получаем id рецепта
    recipe_id = int(callback.data.split("_")[-1])
    
    # Получаем рецепт
    recipe = await session.get(Recipe, recipe_id, options=[selectinload(Recipe.products)])
    
    if not recipe:
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "Рецепт не найден.",
            reply_markup=back_keyboard("search_recipes")
        )
        await callback.answer()
        return
    
    # Формируем текст с информацией о рецепте
    text = f"<b>🍽️ {recipe.name}</b>\n\n"
    
    if recipe.description:
        text += f"{recipe.description}\n\n"
    
    # Добавляем информацию о времени приготовления
    if recipe.prep_time or recipe.cook_time:
        text += "<b>Время приготовления:</b>\n"
        if recipe.prep_time:
            text += f"• Подготовка: {recipe.prep_time} мин.\n"
        if recipe.cook_time:
            text += f"• Готовка: {recipe.cook_time} мин.\n"
        text += "\n"
    
    # Добавляем информацию о порциях
    text += f"<b>Количество порций:</b> {recipe.servings}\n\n"
    
    # Добавляем информацию о пищевой ценности
    calories, protein, fat, carbs = await get_recipe_nutrition(recipe)
    
    text += "<b>Пищевая ценность (на порцию):</b>\n"
    text += f"• Калории: {calories:.0f} ккал\n"
    text += f"• Белки: {protein:.1f} г\n"
    text += f"• Жиры: {fat:.1f} г\n"
    text += f"• Углеводы: {carbs:.1f} г\n\n"
    
    # Добавляем информацию о ингредиентах
    text += "<b>Ингредиенты:</b>\n"
    
    if recipe.products:
        for assoc in recipe.recipe_product_associations:
            product = assoc.product
            amount = assoc.amount
            text += f"• {product.name}: {amount} г\n"
    else:
        text += "Нет информации об ингредиентах.\n"
    
    # Добавляем информацию о способе приготовления
    if recipe.instructions:
        text += f"\n<b>Инструкция по приготовлению:</b>\n{recipe.instructions}\n"
    
    # Создаем клавиатуру с действиями
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопку "Назад"
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="search_recipes"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data == "nutrition_stats")
async def process_nutrition_stats(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Статистика питания"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем активный план питания пользователя
    result = await session.execute(
        select(NutritionPlan)
        .where(NutritionPlan.user_id == user.id, NutritionPlan.is_active == True)
        .options(selectinload(NutritionPlan.meals).selectinload(Meal.recipes))
        .order_by(NutritionPlan.created_at.desc())
    )
    
    nutrition_plan = result.scalar_one_or_none()
    
    if not nutrition_plan:
        await callback.message.edit_text(
            "<b>📊 Статистика питания</b>\n\n"
            "У тебя пока нет активного плана питания для статистики.\n\n"
            "Создай план питания, чтобы видеть статистику.",
            reply_markup=back_keyboard("nutrition_menu")
        )
    else:
        # Формируем текст статистики
        text = "<b>📊 Статистика питания</b>\n\n"
        
        # Добавляем информацию о целевых показателях
        text += f"<b>Целевые показатели:</b>\n"
        text += f"Калории: {nutrition_plan.calories_target} ккал\n"
        text += f"Белки: {nutrition_plan.protein_target} г\n"
        text += f"Жиры: {nutrition_plan.fat_target} г\n"
        text += f"Углеводы: {nutrition_plan.carbs_target} г\n\n"
        
        # Добавляем информацию о текущем потреблении (на основе плана)
        total_calories = 0
        total_protein = 0
        total_fat = 0
        total_carbs = 0
        
        for meal in nutrition_plan.meals:
            for recipe in meal.recipes:
                calories, protein, fat, carbs = await get_recipe_nutrition(recipe)
                total_calories += calories
                total_protein += protein
                total_fat += fat
                total_carbs += carbs
        
        text += f"<b>Текущий план (ежедневно):</b>\n"
        text += f"Калории: {total_calories:.0f} ккал "
        text += f"({100 * total_calories / nutrition_plan.calories_target:.0f}%)\n"
        
        text += f"Белки: {total_protein:.1f} г "
        text += f"({100 * total_protein / nutrition_plan.protein_target:.0f}%)\n"
        
        text += f"Жиры: {total_fat:.1f} г "
        text += f"({100 * total_fat / nutrition_plan.fat_target:.0f}%)\n"
        
        text += f"Углеводы: {total_carbs:.1f} г "
        text += f"({100 * total_carbs / nutrition_plan.carbs_target:.0f}%)\n\n"
        
        # Рассчитываем распределение калорий по макросам
        protein_calories = total_protein * 4  # 4 ккал/г
        fat_calories = total_fat * 9  # 9 ккал/г
        carbs_calories = total_carbs * 4  # 4 ккал/г
        
        text += f"<b>Распределение калорий:</b>\n"
        text += f"Белки: {protein_calories:.0f} ккал ({100 * protein_calories / total_calories:.0f}%)\n"
        text += f"Жиры: {fat_calories:.0f} ккал ({100 * fat_calories / total_calories:.0f}%)\n"
        text += f"Углеводы: {carbs_calories:.0f} ккал ({100 * carbs_calories / total_calories:.0f}%)\n"
        
        # Создаем клавиатуру с действиями
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="nutrition_menu"))
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


async def get_user(session: AsyncSession, telegram_id: int) -> User:
    """
    Получить пользователя по telegram_id
    """
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    return user


async def get_recipe_nutrition(recipe: Recipe) -> tuple[float, float, float, float]:
    """
    Рассчитывает пищевую ценность рецепта на порцию
    
    :param recipe: Рецепт
    :return: Калории, белки, жиры, углеводы
    """
    calories = 0
    protein = 0
    fat = 0
    carbs = 0
    
    for assoc in recipe.recipe_product_associations:
        product = assoc.product
        amount = assoc.amount / 100  # Переводим в сотни грамм (продукты хранят информацию на 100г)
        
        calories += product.calories * amount
        protein += product.protein * amount
        fat += product.fat * amount
        carbs += product.carbs * amount
    
    # Делим на количество порций
    if recipe.servings > 0:
        calories /= recipe.servings
        protein /= recipe.servings
        fat /= recipe.servings
        carbs /= recipe.servings
    
    return calories, protein, fat, carbs


def get_meal_type_name(meal_type: MealType) -> str:
    """
    Возвращает название типа приема пищи на русском
    
    :param meal_type: Тип приема пищи
    :return: Название на русском
    """
    meal_type_names = {
        MealType.BREAKFAST: "Завтрак",
        MealType.LUNCH: "Обед",
        MealType.DINNER: "Ужин",
        MealType.SNACK: "Перекус",
        MealType.PRE_WORKOUT: "До тренировки",
        MealType.POST_WORKOUT: "После тренировки"
    }
    
    return meal_type_names.get(meal_type, str(meal_type))
