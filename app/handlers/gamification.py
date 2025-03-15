from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime, date, timedelta
import json

from app.models.user import User
from app.models.workout import Workout
from app.models.progress import Progress
from app.keyboards.inline import back_keyboard, main_menu_keyboard
from app.utils.db import get_session

router = Router()


# Определяем типы достижений (бейджей)
ACHIEVEMENTS = {
    # Достижения за тренировки
    "workout_starter": {
        "name": "🏋️‍♂️ Начинающий атлет",
        "description": "Записал первую тренировку",
        "condition": lambda stats: stats["total_workouts"] >= 1
    },
    "workout_regular": {
        "name": "🏆 Регулярные тренировки",
        "description": "Тренировался 3 раза в неделю в течение 2 недель подряд",
        "condition": lambda stats: stats["consistent_weeks"] >= 2
    },
    "workout_master": {
        "name": "🥇 Мастер тренировок",
        "description": "Провел более 30 тренировок",
        "condition": lambda stats: stats["total_workouts"] >= 30
    },
    "iron_will": {
        "name": "🦾 Железная воля",
        "description": "Тренировался 5 дней подряд",
        "condition": lambda stats: stats["consecutive_days"] >= 5
    },
    
    # Достижения за прогресс
    "progress_tracker": {
        "name": "📊 Аналитик прогресса",
        "description": "Записал первые замеры",
        "condition": lambda stats: stats["progress_records"] >= 1
    },
    "consistent_progress": {
        "name": "📈 Стабильный прогресс",
        "description": "Вносил замеры каждую неделю в течение месяца",
        "condition": lambda stats: stats["progress_weeks"] >= 4
    },
    "body_transformer": {
        "name": "💪 Преображение тела",
        "description": "Достиг прогресса в уменьшении жира или увеличении мышечной массы",
        "condition": lambda stats: stats["body_composition_improved"]
    },
    
    # Достижения за питание
    "nutrition_planner": {
        "name": "🍽️ Мастер питания",
        "description": "Создал план питания",
        "condition": lambda stats: stats["has_nutrition_plan"]
    },
    "protein_king": {
        "name": "🥩 Король протеина",
        "description": "Поддерживал высокое потребление белка в течение недели",
        "condition": lambda stats: stats["high_protein_days"] >= 7
    }
}


@router.callback_query(F.data == "achievements")
async def process_achievements(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Достижения"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем статистику пользователя
    stats = await get_user_stats(session, user)
    
    # Определяем, какие достижения получены
    achieved = []
    not_achieved = []
    
    for achievement_id, achievement in ACHIEVEMENTS.items():
        if achievement["condition"](stats):
            achieved.append(achievement)
        else:
            not_achieved.append(achievement)
    
    # Формируем текст сообщения
    text = "<b>🏆 Твои достижения</b>\n\n"
    
    if achieved:
        text += "<b>Полученные достижения:</b>\n"
        for achievement in achieved:
            text += f"• {achievement['name']} - {achievement['description']}\n"
    else:
        text += "У тебя пока нет полученных достижений.\n"
    
    text += "\n<b>Предстоящие достижения:</b>\n"
    for achievement in not_achieved[:5]:  # Показываем только первые 5 предстоящих достижений
        text += f"• {achievement['name']} - {achievement['description']}\n"
    
    # Добавляем статистику
    text += "\n<b>Твоя статистика:</b>\n"
    text += f"• Всего тренировок: {stats['total_workouts']}\n"
    text += f"• Дней тренировок подряд: {stats['consecutive_days']}\n"
    text += f"• Всего замеров прогресса: {stats['progress_records']}\n"
    
    # Создаем клавиатуру с действиями
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопку для вызова челленджей
    builder.row(InlineKeyboardButton(text="🎯 Принять вызов", callback_data="challenges"))
    
    # Добавляем кнопку для рейтинга (в будущем)
    # builder.row(InlineKeyboardButton(text="🏅 Рейтинг", callback_data="leaderboard"))
    
    # Добавляем кнопку "Назад"
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data == "challenges")
async def process_challenges(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Принять вызов"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Формируем список активных челленджей
    challenges = [
        {
            "id": "workout_streak",
            "name": "🔥 7 дней подряд",
            "description": "Тренируйся 7 дней подряд",
            "reward": "Бейдж 'Огненная серия'",
            "duration": "7 дней"
        },
        {
            "id": "protein_challenge",
            "name": "🥩 Протеиновый вызов",
            "description": "Потребляй не менее 2г белка на кг веса каждый день в течение недели",
            "reward": "Бейдж 'Король протеина'",
            "duration": "7 дней"
        },
        {
            "id": "weight_challenge",
            "name": "⚖️ +2 кг чистой массы",
            "description": "Набери 2 кг веса за 30 дней, сохраняя или уменьшая процент жира",
            "reward": "Бейдж 'Мастер массы'",
            "duration": "30 дней"
        },
        {
            "id": "measurement_challenge",
            "name": "📏 Еженедельные замеры",
            "description": "Вноси замеры каждую неделю в течение месяца",
            "reward": "Бейдж 'Аналитик прогресса'",
            "duration": "28 дней"
        }
    ]
    
    # Формируем текст сообщения
    text = "<b>🎯 Доступные вызовы</b>\n\n"
    text += "Выбери вызов, который хочешь принять:\n\n"
    
    for challenge in challenges:
        text += f"<b>{challenge['name']}</b>\n"
        text += f"• {challenge['description']}\n"
        text += f"• Награда: {challenge['reward']}\n"
        text += f"• Длительность: {challenge['duration']}\n\n"
    
    # Создаем клавиатуру с действиями
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки для принятия челленджей
    for challenge in challenges:
        builder.row(InlineKeyboardButton(
            text=f"Принять вызов: {challenge['name']}",
            callback_data=f"accept_challenge_{challenge['id']}"
        ))
    
    # Добавляем кнопку "Назад"
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="achievements"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data.startswith("accept_challenge_"))
async def process_accept_challenge(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик принятия вызова
    """
    # Получаем id челленджа
    challenge_id = callback.data.split("_")[-1]
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # В будущем здесь можно сохранять информацию о принятых челленджах в базе данных
    
    # Отправляем сообщение о принятии вызова
    await callback.message.edit_text(
        f"<b>🎯 Вызов принят!</b>\n\n"
        f"Ты принял вызов. Я буду отслеживать твой прогресс и уведомлю тебя о результатах.\n\n"
        f"Удачи! 💪",
        reply_markup=back_keyboard("achievements")
    )
    
    await callback.answer("Вызов успешно принят!")


async def get_user_stats(session: AsyncSession, user: User) -> dict:
    """
    Получает статистику пользователя для определения достижений
    
    :param session: Сессия базы данных
    :param user: Пользователь
    :return: Словарь со статистикой
    """
    stats = {
        "total_workouts": 0,
        "consecutive_days": 0,
        "consistent_weeks": 0,
        "progress_records": 0,
        "progress_weeks": 0,
        "body_composition_improved": False,
        "has_nutrition_plan": False,
        "high_protein_days": 0
    }
    
    # Получаем количество завершенных тренировок
    result = await session.execute(
        select(func.count()).select_from(Workout)
        .where(Workout.user_id == user.id, Workout.completed == True)
    )
    stats["total_workouts"] = result.scalar_one() or 0
    
    # Получаем даты тренировок для определения последовательности
    result = await session.execute(
        select(Workout.date).where(Workout.user_id == user.id, Workout.completed == True)
        .order_by(Workout.date.desc())
    )
    workout_dates = [record[0] for record in result.all()]
    
    # Определяем количество дней тренировок подряд
    consecutive_days = 0
    if workout_dates:
        today = date.today()
        consecutive_days = 0
        for i in range(30):  # Проверяем последние 30 дней
            check_date = today - timedelta(days=i)
            if check_date in workout_dates:
                consecutive_days += 1
            else:
                break
    
    stats["consecutive_days"] = consecutive_days
    
    # Определяем количество недель с 3+ тренировками подряд
    consistent_weeks = 0
    for week_start in range(0, len(workout_dates), 7):
        week_dates = workout_dates[week_start:week_start+7]
        if len(week_dates) >= 3:
            consistent_weeks += 1
        else:
            break
    
    stats["consistent_weeks"] = consistent_weeks
    
    # Получаем количество записей о прогрессе
    result = await session.execute(
        select(func.count()).select_from(Progress)
        .where(Progress.user_id == user.id)
    )
    stats["progress_records"] = result.scalar_one() or 0
    
    # Получаем записи о прогрессе для дальнейшего анализа
    result = await session.execute(
        select(Progress).where(Progress.user_id == user.id)
        .order_by(Progress.date.asc())
    )
    progress_records = result.scalars().all()
    
    # Определяем улучшение состава тела
    if len(progress_records) >= 2:
        first_record = progress_records[0]
        last_record = progress_records[-1]
        
        # Проверяем уменьшение жира или увеличение мышечной массы при сохранении или увеличении веса
        if (first_record.weight and last_record.weight and 
            first_record.body_fat_percentage and last_record.body_fat_percentage):
            
            weight_increased = last_record.weight >= first_record.weight
            fat_decreased = last_record.body_fat_percentage < first_record.body_fat_percentage
            
            if weight_increased and fat_decreased:
                stats["body_composition_improved"] = True
        
        # Или проверяем увеличение обхватов при сохранении или уменьшении талии
        elif (first_record.chest and last_record.chest and 
              first_record.waist and last_record.waist):
            
            chest_increased = last_record.chest > first_record.chest
            waist_stable_or_decreased = last_record.waist <= first_record.waist
            
            if chest_increased and waist_stable_or_decreased:
                stats["body_composition_improved"] = True
    
    # Определяем количество недель с записями о прогрессе
    if progress_records:
        first_date = progress_records[0].date
        last_date = progress_records[-1].date
        weeks_diff = (last_date - first_date).days // 7
        
        # Грубая оценка - если количество записей >= количеству недель, то считаем, что записи делались еженедельно
        if stats["progress_records"] >= weeks_diff:
            stats["progress_weeks"] = weeks_diff
    
    # Проверяем наличие плана питания
    result = await session.execute(
        select(func.count()).select_from(NutritionPlan)
        .where(NutritionPlan.user_id == user.id)
    )
    nutrition_plan_count = result.scalar_one() or 0
    stats["has_nutrition_plan"] = nutrition_plan_count > 0
    
    # Высокопротеиновые дни - пока заглушка, в будущем можно добавить учет потребляемых продуктов
    stats["high_protein_days"] = 0
    
    return stats


async def get_user(session: AsyncSession, telegram_id: int) -> User:
    """
    Получить пользователя по telegram_id
    """
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    return user


from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from app.models.nutrition import NutritionPlan
