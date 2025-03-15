from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ContentType, LabeledPrice, PreCheckoutQuery, ShippingOption, ShippingQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import json

from app.models.user import User
from app.models.subscription import Subscription, Payment, SubscriptionType, PaymentStatus
from app.keyboards.inline import subscription_keyboard, back_keyboard, confirmation_keyboard, main_menu_keyboard
from app.utils.db import get_session
from app.config import settings

router = Router()


@router.callback_query(F.data == "subscription")
async def process_subscription(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Подписка"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем активную подписку пользователя
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.is_active == True)
        .order_by(Subscription.end_date.desc())
    )
    
    subscription = result.scalar_one_or_none()
    
    is_premium = subscription is not None and subscription.is_valid
    
    # Получаем историю платежей
    result = await session.execute(
        select(Payment)
        .where(Payment.user_id == user.id, Payment.status == PaymentStatus.COMPLETED)
        .order_by(Payment.created_at.desc())
        .limit(5)
    )
    
    payments = result.scalars().all()
    
    # Формируем текст сообщения
    text = "<b>⭐ Подписка</b>\n\n"
    
    if is_premium:
        text += f"У тебя активная подписка <b>{get_subscription_type_name(subscription.subscription_type)}</b>.\n"
        text += f"Осталось дней: <b>{subscription.days_left}</b>.\n\n"
    else:
        text += "У тебя нет активной подписки.\n\n"
    
    # Описываем преимущества подписки
    text += "<b>Преимущества подписки:</b>\n"
    text += "• Полный доступ ко всем функциям приложения\n"
    text += "• Расширенная аналитика прогресса\n"
    text += "• Консультации персонального тренера\n"
    text += "• Индивидуальные планы питания\n"
    text += "• Приоритетная поддержка\n\n"
    
    # Отображаем историю платежей
    if payments:
        text += "<b>История платежей:</b>\n"
        for payment in payments:
            text += f"• {payment.created_at.strftime('%d.%m.%Y')}: {payment.amount/100} {payment.currency} - {payment.description or 'Платеж'}\n"
    
    # Создаем клавиатуру
    await callback.message.edit_text(
        text,
        reply_markup=subscription_keyboard(is_premium)
    )
    
    await callback.answer()


@router.callback_query(F.data == "subscribe_basic")
async def process_subscribe_basic(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Подписка на месяц"
    """
    # Если платежный токен не настроен, отображаем сообщение
    if not settings.PAYMENT_TOKEN:
        await callback.message.edit_text(
            "<b>⚠️ Платежная система временно недоступна</b>\n\n"
            "Приносим извинения, но в данный момент платежная система не настроена.\n\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=back_keyboard("subscription")
        )
        await callback.answer()
        return
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Создаем инвойс для оплаты через Telegram Payments
    await bot.send_invoice(
        chat_id=user.telegram_id,
        title="Подписка на FitGains",
        description="Базовая подписка на 1 месяц",
        payload=json.dumps({"type": "subscription", "subscription_type": "basic"}),
        provider_token=settings.PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Подписка на 1 месяц", amount=settings.BASIC_SUBSCRIPTION_PRICE)],
        start_parameter="subscription",
        photo_url="https://example.com/fitgains_subscription.jpg",
        photo_width=600,
        photo_height=400,
        need_name=True,
        need_email=True,
        is_flexible=False
    )
    
    await callback.answer()


@router.callback_query(F.data == "subscribe_premium")
async def process_subscribe_premium(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Премиум подписка"
    """
    # Если платежный токен не настроен, отображаем сообщение
    if not settings.PAYMENT_TOKEN:
        await callback.message.edit_text(
            "<b>⚠️ Платежная система временно недоступна</b>\n\n"
            "Приносим извинения, но в данный момент платежная система не настроена.\n\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=back_keyboard("subscription")
        )
        await callback.answer()
        return
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Создаем инвойс для оплаты через Telegram Payments
    await bot.send_invoice(
        chat_id=user.telegram_id,
        title="Премиум подписка на FitGains",
        description="Премиум подписка на 1 месяц",
        payload=json.dumps({"type": "subscription", "subscription_type": "premium"}),
        provider_token=settings.PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Премиум подписка на 1 месяц", amount=settings.PREMIUM_SUBSCRIPTION_PRICE)],
        start_parameter="subscription",
        photo_url="https://example.com/fitgains_premium.jpg",
        photo_width=600,
        photo_height=400,
        need_name=True,
        need_email=True,
        is_flexible=False
    )
    
    await callback.answer()


@router.callback_query(F.data == "buy_nutrition_plan")
async def process_buy_nutrition_plan(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Персональный план питания"
    """
    # Если платежный токен не настроен, отображаем сообщение
    if not settings.PAYMENT_TOKEN:
        await callback.message.edit_text(
            "<b>⚠️ Платежная система временно недоступна</b>\n\n"
            "Приносим извинения, но в данный момент платежная система не настроена.\n\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=back_keyboard("subscription")
        )
        await callback.answer()
        return
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Создаем инвойс для оплаты через Telegram Payments
    await bot.send_invoice(
        chat_id=user.telegram_id,
        title="Персональный план питания",
        description="Индивидуальный план питания с рецептами",
        payload=json.dumps({"type": "nutrition_plan"}),
        provider_token=settings.PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Персональный план питания", amount=settings.PERSONAL_NUTRITION_PRICE)],
        start_parameter="nutrition_plan",
        photo_url="https://example.com/fitgains_nutrition.jpg",
        photo_width=600,
        photo_height=400,
        need_name=True,
        need_email=True,
        is_flexible=False
    )
    
    await callback.answer()


@router.callback_query(F.data == "buy_workout_plan")
async def process_buy_workout_plan(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Индивидуальная тренировка"
    """
    # Если платежный токен не настроен, отображаем сообщение
    if not settings.PAYMENT_TOKEN:
        await callback.message.edit_text(
            "<b>⚠️ Платежная система временно недоступна</b>\n\n"
            "Приносим извинения, но в данный момент платежная система не настроена.\n\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=back_keyboard("subscription")
        )
        await callback.answer()
        return
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Создаем инвойс для оплаты через Telegram Payments
    await bot.send_invoice(
        chat_id=user.telegram_id,
        title="Индивидуальная тренировка",
        description="Персональная программа тренировок",
        payload=json.dumps({"type": "workout_plan"}),
        provider_token=settings.PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Индивидуальная тренировка", amount=settings.PERSONAL_WORKOUT_PRICE)],
        start_parameter="workout_plan",
        photo_url="https://example.com/fitgains_workout.jpg",
        photo_width=600,
        photo_height=400,
        need_name=True,
        need_email=True,
        is_flexible=False
    )
    
    await callback.answer()


@router.callback_query(F.data == "manage_subscription")
async def process_manage_subscription(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Управление подпиской"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем активную подписку пользователя
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.is_active == True)
        .order_by(Subscription.end_date.desc())
    )
    
    subscription = result.scalar_one_or_none()
    
    if not subscription or not subscription.is_valid:
        await callback.message.edit_text(
            "<b>⚠️ У тебя нет активной подписки</b>\n\n"
            "Приобрети подписку, чтобы получить доступ ко всем функциям приложения.",
            reply_markup=back_keyboard("subscription")
        )
        await callback.answer()
        return
    
    # Формируем текст сообщения
    text = "<b>📝 Управление подпиской</b>\n\n"
    text += f"Тип подписки: <b>{get_subscription_type_name(subscription.subscription_type)}</b>\n"
    text += f"Дата начала: {subscription.start_date.strftime('%d.%m.%Y')}\n"
    text += f"Дата окончания: {subscription.end_date.strftime('%d.%m.%Y')}\n"
    text += f"Осталось дней: {subscription.days_left}\n"
    text += f"Автопродление: {'Включено' if subscription.auto_renew else 'Отключено'}\n\n"
    
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    
    # Кнопка для управления автопродлением
    if subscription.auto_renew:
        builder.row(InlineKeyboardButton(text="❌ Отключить автопродление", callback_data="toggle_auto_renew"))
    else:
        builder.row(InlineKeyboardButton(text="✅ Включить автопродление", callback_data="toggle_auto_renew"))
    
    # Кнопка для отмены подписки
    builder.row(InlineKeyboardButton(text="🗑️ Отменить подписку", callback_data="cancel_subscription"))
    
    # Кнопка "Назад"
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="subscription"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data == "toggle_auto_renew")
async def process_toggle_auto_renew(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки включения/отключения автопродления
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем активную подписку пользователя
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.is_active == True)
        .order_by(Subscription.end_date.desc())
    )
    
    subscription = result.scalar_one_or_none()
    
    if not subscription or not subscription.is_valid:
        await callback.message.edit_text(
            "<b>⚠️ У тебя нет активной подписки</b>\n\n"
            "Приобрети подписку, чтобы получить доступ ко всем функциям приложения.",
            reply_markup=back_keyboard("subscription")
        )
        await callback.answer()
        return
    
    # Переключаем состояние автопродления
    subscription.auto_renew = not subscription.auto_renew
    await session.commit()
    
    # Формируем сообщение
    if subscription.auto_renew:
        message = (
            "<b>✅ Автопродление включено</b>\n\n"
            "Твоя подписка будет автоматически продлена по окончании текущего периода."
        )
    else:
        message = (
            "<b>❌ Автопродление отключено</b>\n\n"
            "Твоя подписка не будет автоматически продлена по окончании текущего периода."
        )
    
    await callback.message.edit_text(
        message,
        reply_markup=back_keyboard("manage_subscription")
    )
    
    await callback.answer()


@router.callback_query(F.data == "cancel_subscription")
async def process_cancel_subscription(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки отмены подписки
    """
    # Запрашиваем подтверждение
    await callback.message.edit_text(
        "<b>⚠️ Отменить подписку?</b>\n\n"
        "Ты действительно хочешь отменить подписку?\n\n"
        "Ты сможешь пользоваться подпиской до окончания оплаченного периода, но после этого доступ к премиум-функциям будет прекращен.",
        reply_markup=confirmation_keyboard("cancel_subscription")
    )
    
    await callback.answer()


@router.callback_query(F.data == "confirm_cancel_subscription")
async def process_confirm_cancel_subscription(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик подтверждения отмены подписки
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем активную подписку пользователя
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.is_active == True)
        .order_by(Subscription.end_date.desc())
    )
    
    subscription = result.scalar_one_or_none()
    
    if not subscription or not subscription.is_valid:
        await callback.message.edit_text(
            "<b>⚠️ У тебя нет активной подписки</b>\n\n"
            "Приобрети подписку, чтобы получить доступ ко всем функциям приложения.",
            reply_markup=back_keyboard("subscription")
        )
        await callback.answer()
        return
    
    # Отключаем автопродление и деактивируем подписку
    subscription.auto_renew = False
    subscription.is_active = False
    await session.commit()
    
    # Обновляем статус пользователя
    user.is_premium = False
    await session.commit()
    
    await callback.message.edit_text(
        "<b>✅ Подписка отменена</b>\n\n"
        "Твоя подписка успешно отменена.\n\n"
        "Ты можешь продолжать пользоваться базовыми функциями приложения. Если ты захочешь снова оформить подписку, ты всегда можешь сделать это в разделе 'Подписка'.",
        reply_markup=back_keyboard("subscription")
    )
    
    await callback.answer()


@router.callback_query(F.data == "cancel_cancel_subscription")
async def process_cancel_cancel_subscription(callback: CallbackQuery):
    """
    Обработчик отмены отмены подписки
    """
    await callback.message.edit_text(
        "<b>✅ Отмена отменена</b>\n\n"
        "Твоя подписка остается активной.",
        reply_markup=back_keyboard("manage_subscription")
    )
    
    await callback.answer()


@router.callback_query(F.data == "renew_subscription")
async def process_renew_subscription(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки продления подписки
    """
    # Если платежный токен не настроен, отображаем сообщение
    if not settings.PAYMENT_TOKEN:
        await callback.message.edit_text(
            "<b>⚠️ Платежная система временно недоступна</b>\n\n"
            "Приносим извинения, но в данный момент платежная система не настроена.\n\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=back_keyboard("subscription")
        )
        await callback.answer()
        return
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем активную подписку пользователя
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.is_active == True)
        .order_by(Subscription.end_date.desc())
    )
    
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        await callback.message.edit_text(
            "<b>⚠️ У тебя нет активной подписки</b>\n\n"
            "Приобрети подписку, чтобы получить доступ ко всем функциям приложения.",
            reply_markup=back_keyboard("subscription")
        )
        await callback.answer()
        return
    
    # Определяем тип подписки для продления
    subscription_type = subscription.subscription_type
    
    # Определяем сумму в зависимости от типа подписки
    amount = settings.BASIC_SUBSCRIPTION_PRICE
    title = "Продление подписки на FitGains"
    description = "Продление базовой подписки на 1 месяц"
    
    if subscription_type == SubscriptionType.PREMIUM:
        amount = settings.PREMIUM_SUBSCRIPTION_PRICE
        description = "Продление премиум подписки на 1 месяц"
    
    # Создаем инвойс для оплаты через Telegram Payments
    await bot.send_invoice(
        chat_id=user.telegram_id,
        title=title,
        description=description,
        payload=json.dumps({"type": "renew_subscription", "subscription_type": subscription_type.value}),
        provider_token=settings.PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label=description, amount=amount)],
        start_parameter="renew_subscription",
        photo_url="https://example.com/fitgains_subscription.jpg",
        photo_width=600,
        photo_height=400,
        need_name=True,
        need_email=True,
        is_flexible=False
    )
    
    await callback.answer()


@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, session: AsyncSession):
    """
    Обработчик пре-чекаута
    """
    # Проверяем payload
    try:
        payload = json.loads(pre_checkout_query.invoice_payload)
        
        # Если всё в порядке, подтверждаем платеж
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    except Exception as e:
        # Если возникла ошибка, отменяем платеж
        await bot.answer_pre_checkout_query(
            pre_checkout_query.id,
            ok=False,
            error_message="К сожалению, произошла ошибка при обработке платежа. Пожалуйста, попробуйте позже."
        )


@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: Message, session: AsyncSession):
    """
    Обработчик успешного платежа
    """
    # Получаем информацию о платеже
    payment_info = message.successful_payment
    
    # Получаем пользователя
    user = await get_user(session, message.from_user.id)
    
    # Парсим payload
    payload = json.loads(payment_info.invoice_payload)
    payment_type = payload.get("type")
    
    # Создаем запись о платеже
    payment = Payment(
        user_id=user.id,
        amount=payment_info.total_amount,
        currency=payment_info.currency,
        payment_method=payment_info.payment_method_name,
        status=PaymentStatus.COMPLETED,
        payment_id=payment_info.telegram_payment_charge_id,
        description=f"Оплата {payment_type}"
    )
    
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    
    # Обрабатываем платеж в зависимости от типа
    if payment_type in ["subscription", "renew_subscription"]:
        await process_subscription_payment(session, user, payment, payload)
    elif payment_type == "nutrition_plan":
        await process_nutrition_plan_payment(session, user, payment)
    elif payment_type == "workout_plan":
        await process_workout_plan_payment(session, user, payment)
    
    # Отправляем сообщение об успешной оплате
    await message.answer(
        "<b>✅ Платеж успешно обработан!</b>\n\n"
        f"Спасибо за покупку! Твой платеж на сумму {payment_info.total_amount / 100} {payment_info.currency} успешно обработан.",
        reply_markup=main_menu_keyboard()
    )


async def process_subscription_payment(session: AsyncSession, user: User, payment: Payment, payload: dict):
    """
    Обрабатывает платеж за подписку
    
    :param session: Сессия базы данных
    :param user: Пользователь
    :param payment: Платеж
    :param payload: Данные платежа
    """
    # Определяем тип подписки
    subscription_type_str = payload.get("subscription_type", "basic")
    subscription_type = SubscriptionType(subscription_type_str)
    
    # Получаем текущую подписку пользователя (если есть)
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.is_active == True)
        .order_by(Subscription.end_date.desc())
    )
    
    current_subscription = result.scalar_one_or_none()
    
    # Определяем даты начала и окончания подписки
    start_date = datetime.utcnow()
    
    # Если есть активная подписка и она еще не истекла, продлеваем ее
    if current_subscription and current_subscription.end_date > start_date:
        start_date = current_subscription.end_date
    
    # Подписка действует 30 дней
    end_date = start_date + timedelta(days=30)
    
    # Деактивируем все текущие подписки
    await session.execute(
        Subscription.__table__.update()
        .where(Subscription.user_id == user.id, Subscription.id != (current_subscription.id if current_subscription else None))
        .values(is_active=False)
    )
    
    # Создаем новую подписку
    subscription = Subscription(
        user_id=user.id,
        subscription_type=subscription_type,
        start_date=start_date,
        end_date=end_date,
        is_active=True,
        auto_renew=True
    )
    
    session.add(subscription)
    
    # Связываем платеж с подпиской
    payment.subscription_id = subscription.id
    
    # Обновляем статус пользователя
    user.is_premium = True
    
    await session.commit()


async def process_nutrition_plan_payment(session: AsyncSession, user: User, payment: Payment):
    """
    Обрабатывает платеж за персональный план питания
    
    :param session: Сессия базы данных
    :param user: Пользователь
    :param payment: Платеж
    """
    # В будущем здесь можно добавить логику для создания персонального плана питания
    pass


async def process_workout_plan_payment(session: AsyncSession, user: User, payment: Payment):
    """
    Обрабатывает платеж за индивидуальную тренировку
    
    :param session: Сессия базы данных
    :param user: Пользователь
    :param payment: Платеж
    """
    # В будущем здесь можно добавить логику для создания индивидуального плана тренировок
    pass


async def get_user(session: AsyncSession, telegram_id: int) -> User:
    """
    Получить пользователя по telegram_id
    """
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    return user


def get_subscription_type_name(subscription_type: SubscriptionType) -> str:
    """
    Возвращает название типа подписки на русском
    
    :param subscription_type: Тип подписки
    :return: Название на русском
    """
    subscription_type_names = {
        SubscriptionType.BASIC: "Базовая",
        SubscriptionType.PREMIUM: "Премиум"
    }
    
    return subscription_type_names.get(subscription_type, str(subscription_type))


from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram import Bot

# Получаем бота из context
bot = None

# Регистрируем бота при запуске
def register_bot(new_bot: Bot):
    global bot
    bot = new_bot
