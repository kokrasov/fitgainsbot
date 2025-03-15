from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard(new_user: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура главного меню
    
    :param new_user: Если True, отображается кнопка регистрации
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    if new_user:
        # Для нового пользователя предлагаем заполнить профиль
        builder.add(InlineKeyboardButton(text="📝 Заполнить профиль", callback_data="profile_setup"))
    else:
        # Основные кнопки меню
        builder.row(
            InlineKeyboardButton(text="💪 Тренировки", callback_data="workout_menu"),
            InlineKeyboardButton(text="🍽️ Питание", callback_data="nutrition_menu")
        )
        builder.row(
            InlineKeyboardButton(text="📊 Прогресс", callback_data="progress_menu"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile_menu")
        )
        builder.row(
            InlineKeyboardButton(text="🏆 Достижения", callback_data="achievements"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="help")
        )
        # Кнопка подписки
        builder.row(InlineKeyboardButton(text="⭐ Подписка", callback_data="subscription"))
    
    return builder.as_markup()


def profile_setup_keyboard(step: str) -> InlineKeyboardMarkup:
    """
    Клавиатура для настройки профиля
    
    :param step: Текущий шаг настройки (gender, age, height, weight и т.д.)
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    if step == "gender":
        builder.row(
            InlineKeyboardButton(text="♂️ Мужской", callback_data="gender_male"),
            InlineKeyboardButton(text="♀️ Женский", callback_data="gender_female")
        )
    elif step == "activity_level":
        builder.row(InlineKeyboardButton(text="📱 Сидячий образ жизни", callback_data="activity_sedentary"))
        builder.row(InlineKeyboardButton(text="🚶 Легкая активность (1-2 раза в неделю)", callback_data="activity_lightly_active"))
        builder.row(InlineKeyboardButton(text="🏃 Умеренная активность (3-5 раз в неделю)", callback_data="activity_moderately_active"))
        builder.row(InlineKeyboardButton(text="🏋️ Высокая активность (6-7 раз в неделю)", callback_data="activity_very_active"))
        builder.row(InlineKeyboardButton(text="🏅 Профессиональный спорт", callback_data="activity_extremely_active"))
    elif step == "experience_level":
        builder.row(InlineKeyboardButton(text="🔰 Новичок (0-6 месяцев)", callback_data="experience_beginner"))
        builder.row(InlineKeyboardButton(text="🥉 Средний (6 месяцев - 2 года)", callback_data="experience_intermediate"))
        builder.row(InlineKeyboardButton(text="🥇 Продвинутый (2+ лет)", callback_data="experience_advanced"))
    elif step == "diet_type":
        builder.row(InlineKeyboardButton(text="🍗 Обычная", callback_data="diet_regular"))
        builder.row(InlineKeyboardButton(text="🥗 Вегетарианская", callback_data="diet_vegetarian"))
        builder.row(InlineKeyboardButton(text="🥬 Веганская", callback_data="diet_vegan"))
        builder.row(InlineKeyboardButton(text="🥩 Кето", callback_data="diet_keto"))
        builder.row(InlineKeyboardButton(text="🍳 Палео", callback_data="diet_paleo"))
    elif step == "has_gym":
        builder.row(
            InlineKeyboardButton(text="✅ Да", callback_data="gym_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="gym_no")
        )
    elif step == "training_days":
        builder.row(
            InlineKeyboardButton(text="2 дня", callback_data="training_days_2"),
            InlineKeyboardButton(text="3 дня", callback_data="training_days_3"),
        )
        builder.row(
            InlineKeyboardButton(text="4 дня", callback_data="training_days_4"),
            InlineKeyboardButton(text="5 дней", callback_data="training_days_5"),
        )
        builder.row(
            InlineKeyboardButton(text="6 дней", callback_data="training_days_6"),
        )
    
    # Кнопка отмены для всех шагов (кроме gender, который является первым)
    if step != "gender":
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_from_{step}"))
    
    # Кнопка для пропуска необязательных шагов
    optional_steps = ["allergies"]
    if step in optional_steps:
        builder.row(InlineKeyboardButton(text="⏩ Пропустить", callback_data=f"skip_{step}"))
    
    return builder.as_markup()


def workout_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура меню тренировок
    
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="📅 Мои тренировки", callback_data="my_workouts"))
    builder.row(InlineKeyboardButton(text="➕ Новая тренировка", callback_data="new_workout"))
    builder.row(InlineKeyboardButton(text="📝 История тренировок", callback_data="workout_history"))
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="workout_stats"))
    
    # Кнопка возврата в главное меню
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"))
    
    return builder.as_markup()


def nutrition_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура меню питания
    
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="🍽️ Мой план питания", callback_data="my_nutrition_plan"))
    builder.row(InlineKeyboardButton(text="🔄 Обновить план", callback_data="update_nutrition_plan"))
    builder.row(InlineKeyboardButton(text="🔍 Поиск рецептов", callback_data="search_recipes"))
    builder.row(InlineKeyboardButton(text="📊 Статистика питания", callback_data="nutrition_stats"))
    
    # Кнопка возврата в главное меню
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"))
    
    return builder.as_markup()


def progress_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура меню прогресса
    
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="⚖️ Внести замеры", callback_data="add_measurements"))
    builder.row(InlineKeyboardButton(text="📷 Загрузить фото", callback_data="upload_photo"))
    builder.row(InlineKeyboardButton(text="📈 Мой прогресс", callback_data="view_progress"))
    builder.row(InlineKeyboardButton(text="📊 Графики", callback_data="progress_charts"))
    
    # Кнопка возврата в главное меню
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"))
    
    return builder.as_markup()


def profile_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура меню профиля
    
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="👤 Мой профиль", callback_data="view_profile"))
    builder.row(InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit_profile"))
    builder.row(InlineKeyboardButton(text="🎯 Изменить цели", callback_data="edit_goals"))
    builder.row(InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"))
    
    # Кнопка возврата в главное меню
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"))
    
    return builder.as_markup()


def subscription_keyboard(is_premium: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура для подписки
    
    :param is_premium: Имеет ли пользователь премиум-подписку
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    if not is_premium:
        builder.row(InlineKeyboardButton(text="💎 Подписка на месяц (300₽)", callback_data="subscribe_basic"))
        builder.row(InlineKeyboardButton(text="💎💎 Премиум подписка (500₽)", callback_data="subscribe_premium"))
    else:
        builder.row(InlineKeyboardButton(text="📆 Управление подпиской", callback_data="manage_subscription"))
        builder.row(InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="renew_subscription"))
    
    # Отдельные услуги
    builder.row(InlineKeyboardButton(text="🍽️ Персональный план питания (99₽)", callback_data="buy_nutrition_plan"))
    builder.row(InlineKeyboardButton(text="💪 Индивидуальная тренировка (199₽)", callback_data="buy_workout_plan"))
    
    # Кнопка возврата в главное меню
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"))
    
    return builder.as_markup()


def confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения действия
    
    :param action: Действие, которое нужно подтвердить
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{action}")
    )
    
    return builder.as_markup()


def back_keyboard(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой "Назад"
    
    :param callback_data: Callback-данные для кнопки "Назад"
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data))
    
    return builder.as_markup()
