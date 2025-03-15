from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload
from datetime import datetime, date, timedelta
import os
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import numpy as np

from app.models.user import User
from app.models.progress import Progress, ProgressPhoto
from app.keyboards.inline import progress_menu_keyboard, back_keyboard, confirmation_keyboard, main_menu_keyboard
from app.utils.db import get_session

router = Router()


class ProgressStates(StatesGroup):
    """
    Состояния для работы с прогрессом
    """
    waiting_for_weight = State()
    waiting_for_chest = State()
    waiting_for_waist = State()
    waiting_for_hips = State()
    waiting_for_biceps_left = State()
    waiting_for_biceps_right = State()
    waiting_for_thigh_left = State()
    waiting_for_thigh_right = State()
    waiting_for_calf_left = State()
    waiting_for_calf_right = State()
    waiting_for_body_fat = State()
    waiting_for_notes = State()
    waiting_for_photo_front = State()
    waiting_for_photo_side = State()
    waiting_for_photo_back = State()


@router.callback_query(F.data == "progress_menu")
async def process_progress_menu(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Прогресс"
    """
    await callback.message.edit_text(
        "<b>📊 Прогресс</b>\n\n"
        "Здесь ты можешь отслеживать свой прогресс, вносить замеры и загружать фотографии.\n\n"
        "Выбери действие:",
        reply_markup=progress_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "add_measurements")
async def process_add_measurements(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Внести замеры"
    """
    # Устанавливаем состояние ожидания ввода веса
    await state.set_state(ProgressStates.waiting_for_weight)
    
    await callback.message.edit_text(
        "<b>⚖️ Внесение замеров</b>\n\n"
        "Для начала введи свой текущий вес в килограммах (например, 75.5).\n\n"
        "Если ты хочешь пропустить какой-либо параметр, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )
    await callback.answer()


@router.message(ProgressStates.waiting_for_weight)
async def process_weight(message: Message, state: FSMContext):
    """
    Обработчик ввода веса
    """
    # Получаем вес
    weight_text = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот параметр
    if weight_text == "🚫":
        await state.update_data(weight=None)
    else:
        try:
            # Парсим вес
            weight = float(weight_text)
            
            # Проверяем, что вес в пределах разумного (от 30 до 300 кг)
            if weight < 30 or weight > 300:
                await message.answer(
                    "⚠️ Ты указал некорректный вес. Пожалуйста, введи свой вес в килограммах (от 30 до 300)."
                )
                return
            
            # Сохраняем вес в состоянии
            await state.update_data(weight=weight)
        except ValueError:
            await message.answer(
                "⚠️ Неверный формат. Пожалуйста, введи свой вес в килограммах числом (например, 75.5)."
            )
            return
    
    # Переходим к следующему шагу - ввод объема груди
    await state.set_state(ProgressStates.waiting_for_chest)
    
    await message.answer(
        "<b>⚖️ Внесение замеров (2/10)</b>\n\n"
        "Теперь введи объем груди в сантиметрах (например, 100).\n\n"
        "Если ты хочешь пропустить этот параметр, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_chest)
async def process_chest(message: Message, state: FSMContext):
    """
    Обработчик ввода объема груди
    """
    # Получаем объем груди
    chest_text = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот параметр
    if chest_text == "🚫":
        await state.update_data(chest=None)
    else:
        try:
            # Парсим объем груди
            chest = float(chest_text)
            
            # Проверяем, что объем груди в пределах разумного (от 60 до 150 см)
            if chest < 60 or chest > 150:
                await message.answer(
                    "⚠️ Ты указал некорректный объем груди. Пожалуйста, введи объем груди в сантиметрах (от 60 до 150)."
                )
                return
            
            # Сохраняем объем груди в состоянии
            await state.update_data(chest=chest)
        except ValueError:
            await message.answer(
                "⚠️ Неверный формат. Пожалуйста, введи объем груди в сантиметрах числом (например, 100)."
            )
            return
    
    # Переходим к следующему шагу - ввод объема талии
    await state.set_state(ProgressStates.waiting_for_waist)
    
    await message.answer(
        "<b>⚖️ Внесение замеров (3/10)</b>\n\n"
        "Теперь введи объем талии в сантиметрах (например, 80).\n\n"
        "Если ты хочешь пропустить этот параметр, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_waist)
async def process_waist(message: Message, state: FSMContext):
    """
    Обработчик ввода объема талии
    """
    # Получаем объем талии
    waist_text = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот параметр
    if waist_text == "🚫":
        await state.update_data(waist=None)
    else:
        try:
            # Парсим объем талии
            waist = float(waist_text)
            
            # Проверяем, что объем талии в пределах разумного (от 50 до 150 см)
            if waist < 50 or waist > 150:
                await message.answer(
                    "⚠️ Ты указал некорректный объем талии. Пожалуйста, введи объем талии в сантиметрах (от 50 до 150)."
                )
                return
            
            # Сохраняем объем талии в состоянии
            await state.update_data(waist=waist)
        except ValueError:
            await message.answer(
                "⚠️ Неверный формат. Пожалуйста, введи объем талии в сантиметрах числом (например, 80)."
            )
            return
    
    # Переходим к следующему шагу - ввод объема бедер
    await state.set_state(ProgressStates.waiting_for_hips)
    
    await message.answer(
        "<b>⚖️ Внесение замеров (4/10)</b>\n\n"
        "Теперь введи объем бедер в сантиметрах (например, 95).\n\n"
        "Если ты хочешь пропустить этот параметр, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_hips)
async def process_hips(message: Message, state: FSMContext):
    """
    Обработчик ввода объема бедер
    """
    # Получаем объем бедер
    hips_text = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот параметр
    if hips_text == "🚫":
        await state.update_data(hips=None)
    else:
        try:
            # Парсим объем бедер
            hips = float(hips_text)
            
            # Проверяем, что объем бедер в пределах разумного (от 60 до 150 см)
            if hips < 60 or hips > 150:
                await message.answer(
                    "⚠️ Ты указал некорректный объем бедер. Пожалуйста, введи объем бедер в сантиметрах (от 60 до 150)."
                )
                return
            
            # Сохраняем объем бедер в состоянии
            await state.update_data(hips=hips)
        except ValueError:
            await message.answer(
                "⚠️ Неверный формат. Пожалуйста, введи объем бедер в сантиметрах числом (например, 95)."
            )
            return
    
    # Переходим к следующему шагу - ввод объема левого бицепса
    await state.set_state(ProgressStates.waiting_for_biceps_left)
    
    await message.answer(
        "<b>⚖️ Внесение замеров (5/10)</b>\n\n"
        "Теперь введи объем левого бицепса в сантиметрах (например, 35).\n\n"
        "Если ты хочешь пропустить этот параметр, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_biceps_left)
async def process_biceps_left(message: Message, state: FSMContext):
    """
    Обработчик ввода объема левого бицепса
    """
    # Получаем объем левого бицепса
    biceps_left_text = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот параметр
    if biceps_left_text == "🚫":
        await state.update_data(biceps_left=None)
    else:
        try:
            # Парсим объем левого бицепса
            biceps_left = float(biceps_left_text)
            
            # Проверяем, что объем левого бицепса в пределах разумного (от 20 до 60 см)
            if biceps_left < 20 or biceps_left > 60:
                await message.answer(
                    "⚠️ Ты указал некорректный объем левого бицепса. Пожалуйста, введи объем в сантиметрах (от 20 до 60)."
                )
                return
            
            # Сохраняем объем левого бицепса в состоянии
            await state.update_data(biceps_left=biceps_left)
        except ValueError:
            await message.answer(
                "⚠️ Неверный формат. Пожалуйста, введи объем левого бицепса в сантиметрах числом (например, 35)."
            )
            return
    
    # Переходим к следующему шагу - ввод объема правого бицепса
    await state.set_state(ProgressStates.waiting_for_biceps_right)
    
    await message.answer(
        "<b>⚖️ Внесение замеров (6/10)</b>\n\n"
        "Теперь введи объем правого бицепса в сантиметрах (например, 35).\n\n"
        "Если ты хочешь пропустить этот параметр, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_biceps_right)
async def process_biceps_right(message: Message, state: FSMContext):
    """
    Обработчик ввода объема правого бицепса
    """
    # Получаем объем правого бицепса
    biceps_right_text = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот параметр
    if biceps_right_text == "🚫":
        await state.update_data(biceps_right=None)
    else:
        try:
            # Парсим объем правого бицепса
            biceps_right = float(biceps_right_text)
            
            # Проверяем, что объем правого бицепса в пределах разумного (от 20 до 60 см)
            if biceps_right < 20 or biceps_right > 60:
                await message.answer(
                    "⚠️ Ты указал некорректный объем правого бицепса. Пожалуйста, введи объем в сантиметрах (от 20 до 60)."
                )
                return
            
            # Сохраняем объем правого бицепса в состоянии
            await state.update_data(biceps_right=biceps_right)
        except ValueError:
            await message.answer(
                "⚠️ Неверный формат. Пожалуйста, введи объем правого бицепса в сантиметрах числом (например, 35)."
            )
            return
    
    # Переходим к следующему шагу - ввод объема левого бедра
    await state.set_state(ProgressStates.waiting_for_thigh_left)
    
    await message.answer(
        "<b>⚖️ Внесение замеров (7/10)</b>\n\n"
        "Теперь введи объем левого бедра в сантиметрах (например, 55).\n\n"
        "Если ты хочешь пропустить этот параметр, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_thigh_left)
async def process_thigh_left(message: Message, state: FSMContext):
    """
    Обработчик ввода объема левого бедра
    """
    # Получаем объем левого бедра
    thigh_left_text = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот параметр
    if thigh_left_text == "🚫":
        await state.update_data(thigh_left=None)
    else:
        try:
            # Парсим объем левого бедра
            thigh_left = float(thigh_left_text)
            
            # Проверяем, что объем левого бедра в пределах разумного (от 40 до 80 см)
            if thigh_left < 40 or thigh_left > 80:
                await message.answer(
                    "⚠️ Ты указал некорректный объем левого бедра. Пожалуйста, введи объем в сантиметрах (от 40 до 80)."
                )
                return
            
            # Сохраняем объем левого бедра в состоянии
            await state.update_data(thigh_left=thigh_left)
        except ValueError:
            await message.answer(
                "⚠️ Неверный формат. Пожалуйста, введи объем левого бедра в сантиметрах числом (например, 55)."
            )
            return
    
    # Переходим к следующему шагу - ввод объема правого бедра
    await state.set_state(ProgressStates.waiting_for_thigh_right)
    
    await message.answer(
        "<b>⚖️ Внесение замеров (8/10)</b>\n\n"
        "Теперь введи объем правого бедра в сантиметрах (например, 55).\n\n"
        "Если ты хочешь пропустить этот параметр, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_thigh_right)
async def process_thigh_right(message: Message, state: FSMContext):
    """
    Обработчик ввода объема правого бедра
    """
    # Получаем объем правого бедра
    thigh_right_text = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот параметр
    if thigh_right_text == "🚫":
        await state.update_data(thigh_right=None)
    else:
        try:
            # Парсим объем правого бедра
            thigh_right = float(thigh_right_text)
            
            # Проверяем, что объем правого бедра в пределах разумного (от 40 до 80 см)
            if thigh_right < 40 or thigh_right > 80:
                await message.answer(
                    "⚠️ Ты указал некорректный объем правого бедра. Пожалуйста, введи объем в сантиметрах (от 40 до 80)."
                )
                return
            
            # Сохраняем объем правого бедра в состоянии
            await state.update_data(thigh_right=thigh_right)
        except ValueError:
            await message.answer(
                "⚠️ Неверный формат. Пожалуйста, введи объем правого бедра в сантиметрах числом (например, 55)."
            )
            return
    
    # Переходим к следующему шагу - ввод объема левой икры
    await state.set_state(ProgressStates.waiting_for_calf_left)
    
    await message.answer(
        "<b>⚖️ Внесение замеров (9/10)</b>\n\n"
        "Теперь введи объем левой икры в сантиметрах (например, 38).\n\n"
        "Если ты хочешь пропустить этот параметр, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_calf_left)
async def process_calf_left(message: Message, state: FSMContext):
    """
    Обработчик ввода объема левой икры
    """
    # Получаем объем левой икры
    calf_left_text = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот параметр
    if calf_left_text == "🚫":
        await state.update_data(calf_left=None)
    else:
        try:
            # Парсим объем левой икры
            calf_left = float(calf_left_text)
            
            # Проверяем, что объем левой икры в пределах разумного (от 30 до 50 см)
            if calf_left < 30 or calf_left > 50:
                await message.answer(
                    "⚠️ Ты указал некорректный объем левой икры. Пожалуйста, введи объем в сантиметрах (от 30 до 50)."
                )
                return
            
            # Сохраняем объем левой икры в состоянии
            await state.update_data(calf_left=calf_left)
        except ValueError:
            await message.answer(
                "⚠️ Неверный формат. Пожалуйста, введи объем левой икры в сантиметрах числом (например, 38)."
            )
            return
    
    # Переходим к следующему шагу - ввод объема правой икры
    await state.set_state(ProgressStates.waiting_for_calf_right)
    
    await message.answer(
        "<b>⚖️ Внесение замеров (10/10)</b>\n\n"
        "Теперь введи объем правой икры в сантиметрах (например, 38).\n\n"
        "Если ты хочешь пропустить этот параметр, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_calf_right)
async def process_calf_right(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик ввода объема правой икры
    """
    # Получаем объем правой икры
    calf_right_text = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот параметр
    if calf_right_text == "🚫":
        await state.update_data(calf_right=None)
    else:
        try:
            # Парсим объем правой икры
            calf_right = float(calf_right_text)
            
            # Проверяем, что объем правой икры в пределах разумного (от 30 до 50 см)
            if calf_right < 30 or calf_right > 50:
                await message.answer(
                    "⚠️ Ты указал некорректный объем правой икры. Пожалуйста, введи объем в сантиметрах (от 30 до 50)."
                )
                return
            
            # Сохраняем объем правой икры в состоянии
            await state.update_data(calf_right=calf_right)
        except ValueError:
            await message.answer(
                "⚠️ Неверный формат. Пожалуйста, введи объем правой икры в сантиметрах числом (например, 38)."
            )
            return
    
    # Переходим к следующему шагу - ввод процента жира (опционально)
    await state.set_state(ProgressStates.waiting_for_body_fat)
    
    await message.answer(
        "<b>⚖️ Внесение замеров (Дополнительно)</b>\n\n"
        "Если у тебя есть информация о проценте жира в теле, введи ее (например, 15).\n\n"
        "Если нет такой информации, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_body_fat)
async def process_body_fat(message: Message, state: FSMContext):
    """
    Обработчик ввода процента жира
    """
    # Получаем процент жира
    body_fat_text = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот параметр
    if body_fat_text == "🚫":
        await state.update_data(body_fat=None)
    else:
        try:
            # Парсим процент жира
            body_fat = float(body_fat_text)
            
            # Проверяем, что процент жира в пределах разумного (от 3 до 40%)
            if body_fat < 3 or body_fat > 40:
                await message.answer(
                    "⚠️ Ты указал некорректный процент жира. Пожалуйста, введи процент жира (от 3 до 40)."
                )
                return
            
            # Сохраняем процент жира в состоянии
            await state.update_data(body_fat=body_fat)
        except ValueError:
            await message.answer(
                "⚠️ Неверный формат. Пожалуйста, введи процент жира числом (например, 15)."
            )
            return
    
    # Переходим к следующему шагу - ввод заметок (опционально)
    await state.set_state(ProgressStates.waiting_for_notes)
    
    await message.answer(
        "<b>⚖️ Внесение замеров (Дополнительно)</b>\n\n"
        "Если хочешь, можешь добавить заметки о своем прогрессе.\n\n"
        "Например, как ты себя чувствуешь, какие изменения замечаешь, и т.д.\n\n"
        "Если не хочешь добавлять заметки, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_notes)
async def process_notes(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик ввода заметок
    """
    # Получаем заметки
    notes_text = message.text.strip()
    
    # Если пользователь отправил "🚫", пропускаем этот параметр
    if notes_text == "🚫":
        notes = None
    else:
        notes = notes_text
    
    # Получаем все данные из состояния
    data = await state.get_data()
    
    # Получаем пользователя
    user = await get_user(session, message.from_user.id)
    
    # Создаем запись о прогрессе
    progress = Progress(
        user_id=user.id,
        date=date.today(),
        weight=data.get("weight"),
        chest=data.get("chest"),
        waist=data.get("waist"),
        hips=data.get("hips"),
        biceps_left=data.get("biceps_left"),
        biceps_right=data.get("biceps_right"),
        thigh_left=data.get("thigh_left"),
        thigh_right=data.get("thigh_right"),
        calf_left=data.get("calf_left"),
        calf_right=data.get("calf_right"),
        body_fat_percentage=data.get("body_fat"),
        notes=notes
    )
    
    session.add(progress)
    await session.commit()
    await session.refresh(progress)
    
    # Спрашиваем, хочет ли пользователь добавить фотографии
    text = (
        "<b>✅ Замеры успешно сохранены!</b>\n\n"
        "Хочешь также добавить фотографии для отслеживания визуального прогресса?"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📷 Добавить фото", callback_data=f"add_photos_{progress.id}"))
    builder.row(InlineKeyboardButton(text="➡️ Пропустить", callback_data="progress_menu"))
    
    # Очищаем состояние
    await state.clear()
    
    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("add_photos_"))
async def process_add_photos(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Добавить фото"
    """
    # Получаем id записи о прогрессе
    progress_id = int(callback.data.split("_")[-1])
    
    # Сохраняем id записи о прогрессе в состоянии
    await state.update_data(progress_id=progress_id)
    
    # Устанавливаем состояние ожидания загрузки фото спереди
    await state.set_state(ProgressStates.waiting_for_photo_front)
    
    await callback.message.edit_text(
        "<b>📷 Загрузка фотографий</b>\n\n"
        "Пожалуйста, загрузи фотографию спереди.\n\n"
        "Если ты не хочешь загружать фотографию спереди, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )
    await callback.answer()


@router.message(ProgressStates.waiting_for_photo_front, F.photo)
async def process_photo_front(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик загрузки фото спереди
    """
    # Получаем id записи о прогрессе из состояния
    data = await state.get_data()
    progress_id = data["progress_id"]
    
    # Получаем информацию о фото
    photo = message.photo[-1]
    
    # Создаем директорию для сохранения фото, если она не существует
    os.makedirs("data/photos", exist_ok=True)
    
    # Генерируем имя файла
    file_name = f"data/photos/progress_{progress_id}_front_{date.today().strftime('%Y%m%d')}.jpg"
    
    # Скачиваем фото
    await photo.download(destination=file_name)
    
    # Создаем запись о фото
    photo_record = ProgressPhoto(
        progress_id=progress_id,
        photo_type="front",
        photo_path=file_name
    )
    
    session.add(photo_record)
    await session.commit()
    
    # Переходим к следующему шагу - загрузка фото сбоку
    await state.set_state(ProgressStates.waiting_for_photo_side)
    
    await message.answer(
        "<b>📷 Загрузка фотографий (2/3)</b>\n\n"
        "Фотография спереди успешно сохранена!\n\n"
        "Теперь, пожалуйста, загрузи фотографию сбоку.\n\n"
        "Если ты не хочешь загружать фотографию сбоку, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_photo_front, F.text == "🚫")
async def skip_photo_front(message: Message, state: FSMContext):
    """
    Обработчик пропуска загрузки фото спереди
    """
    # Переходим к следующему шагу - загрузка фото сбоку
    await state.set_state(ProgressStates.waiting_for_photo_side)
    
    await message.answer(
        "<b>📷 Загрузка фотографий (2/3)</b>\n\n"
        "Пожалуйста, загрузи фотографию сбоку.\n\n"
        "Если ты не хочешь загружать фотографию сбоку, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_photo_side, F.photo)
async def process_photo_side(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик загрузки фото сбоку
    """
    # Получаем id записи о прогрессе из состояния
    data = await state.get_data()
    progress_id = data["progress_id"]
    
    # Получаем информацию о фото
    photo = message.photo[-1]
    
    # Создаем директорию для сохранения фото, если она не существует
    os.makedirs("data/photos", exist_ok=True)
    
    # Генерируем имя файла
    file_name = f"data/photos/progress_{progress_id}_side_{date.today().strftime('%Y%m%d')}.jpg"
    
    # Скачиваем фото
    await photo.download(destination=file_name)
    
    # Создаем запись о фото
    photo_record = ProgressPhoto(
        progress_id=progress_id,
        photo_type="side",
        photo_path=file_name
    )
    
    session.add(photo_record)
    await session.commit()
    
    # Переходим к следующему шагу - загрузка фото сзади
    await state.set_state(ProgressStates.waiting_for_photo_back)
    
    await message.answer(
        "<b>📷 Загрузка фотографий (3/3)</b>\n\n"
        "Фотография сбоку успешно сохранена!\n\n"
        "Теперь, пожалуйста, загрузи фотографию сзади.\n\n"
        "Если ты не хочешь загружать фотографию сзади, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_photo_side, F.text == "🚫")
async def skip_photo_side(message: Message, state: FSMContext):
    """
    Обработчик пропуска загрузки фото сбоку
    """
    # Переходим к следующему шагу - загрузка фото сзади
    await state.set_state(ProgressStates.waiting_for_photo_back)
    
    await message.answer(
        "<b>📷 Загрузка фотографий (3/3)</b>\n\n"
        "Пожалуйста, загрузи фотографию сзади.\n\n"
        "Если ты не хочешь загружать фотографию сзади, отправь '🚫'.",
        reply_markup=back_keyboard("progress_menu")
    )


@router.message(ProgressStates.waiting_for_photo_back, F.photo)
async def process_photo_back(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик загрузки фото сзади
    """
    # Получаем id записи о прогрессе из состояния
    data = await state.get_data()
    progress_id = data["progress_id"]
    
    # Получаем информацию о фото
    photo = message.photo[-1]
    
    # Создаем директорию для сохранения фото, если она не существует
    os.makedirs("data/photos", exist_ok=True)
    
    # Генерируем имя файла
    file_name = f"data/photos/progress_{progress_id}_back_{date.today().strftime('%Y%m%d')}.jpg"
    
    # Скачиваем фото
    await photo.download(destination=file_name)
    
    # Создаем запись о фото
    photo_record = ProgressPhoto(
        progress_id=progress_id,
        photo_type="back",
        photo_path=file_name
    )
    
    session.add(photo_record)
    await session.commit()
    
    # Очищаем состояние
    await state.clear()
    
    # Отправляем сообщение об успешном сохранении фотографий
    await message.answer(
        "<b>✅ Фотографии успешно сохранены!</b>\n\n"
        "Теперь ты можешь отслеживать свой прогресс не только по замерам, но и визуально.\n\n"
        "Что ты хочешь сделать дальше?",
        reply_markup=progress_menu_keyboard()
    )


@router.message(ProgressStates.waiting_for_photo_back, F.text == "🚫")
async def skip_photo_back(message: Message, state: FSMContext):
    """
    Обработчик пропуска загрузки фото сзади
    """
    # Очищаем состояние
    await state.clear()
    
    # Отправляем сообщение об успешном сохранении фотографий
    await message.answer(
        "<b>✅ Фотографии успешно сохранены!</b>\n\n"
        "Теперь ты можешь отслеживать свой прогресс не только по замерам, но и визуально.\n\n"
        "Что ты хочешь сделать дальше?",
        reply_markup=progress_menu_keyboard()
    )


@router.callback_query(F.data == "upload_photo")
async def process_upload_photo(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик кнопки "Загрузить фото"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Проверяем, есть ли у пользователя запись о прогрессе за сегодня
    result = await session.execute(
        select(Progress)
        .where(Progress.user_id == user.id, Progress.date == date.today())
    )
    
    progress = result.scalar_one_or_none()
    
    if progress:
        # Если запись о прогрессе за сегодня уже есть, предлагаем добавить фото к ней
        await callback.message.edit_text(
            "<b>📷 Загрузка фотографий</b>\n\n"
            "У тебя уже есть запись о прогрессе за сегодня. Хочешь добавить фотографии к этой записи?",
            reply_markup=InlineKeyboardBuilder()
            .row(InlineKeyboardButton(text="✅ Да", callback_data=f"add_photos_{progress.id}"))
            .row(InlineKeyboardButton(text="❌ Нет", callback_data="progress_menu"))
            .as_markup()
        )
    else:
        # Если записи о прогрессе за сегодня нет, создаем новую запись
        progress = Progress(
            user_id=user.id,
            date=date.today()
        )
        
        session.add(progress)
        await session.commit()
        await session.refresh(progress)
        
        # Начинаем процесс загрузки фотографий
        await process_add_photos(CallbackQuery(
            id=callback.id,
            from_user=callback.from_user,
            chat_instance=callback.chat_instance,
            message=callback.message,
            data=f"add_photos_{progress.id}"
        ), state)
    
    await callback.answer()


@router.callback_query(F.data == "view_progress")
async def process_view_progress(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Мой прогресс"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем записи о прогрессе пользователя (последние 10)
    result = await session.execute(
        select(Progress)
        .where(Progress.user_id == user.id)
        .order_by(Progress.date.desc())
        .limit(10)
    )
    
    progress_records = result.scalars().all()
    
    if not progress_records:
        # Если у пользователя нет записей о прогрессе
        await callback.message.edit_text(
            "<b>📊 Мой прогресс</b>\n\n"
            "У тебя пока нет записей о прогрессе.\n\n"
            "Начни отслеживать свой прогресс, добавив замеры и фотографии!",
            reply_markup=back_keyboard("progress_menu")
        )
    else:
        # Если у пользователя есть записи о прогрессе
        # Создаем клавиатуру с выбором записей о прогрессе
        builder = InlineKeyboardBuilder()
        
        for record in progress_records:
            builder.row(InlineKeyboardButton(
                text=f"📝 {record.date.strftime('%d.%m.%Y')}",
                callback_data=f"view_progress_record_{record.id}"
            ))
        
        # Добавляем кнопку для просмотра графиков
        builder.row(InlineKeyboardButton(text="📈 Графики", callback_data="progress_charts"))
        
        # Добавляем кнопку "Назад"
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="progress_menu"))
        
        await callback.message.edit_text(
            "<b>📊 Мой прогресс</b>\n\n"
            "Выбери дату, чтобы посмотреть детали прогресса:",
            reply_markup=builder.as_markup()
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("view_progress_record_"))
async def process_view_progress_record(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик просмотра записи о прогрессе
    """
    # Получаем id записи о прогрессе
    progress_id = int(callback.data.split("_")[-1])
    
    # Получаем запись о прогрессе
    progress = await session.get(Progress, progress_id, options=[selectinload(Progress.photos)])
    
    if not progress:
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "Запись о прогрессе не найдена.",
            reply_markup=back_keyboard("view_progress")
        )
        await callback.answer()
        return
    
    # Получаем предыдущую запись о прогрессе (для сравнения)
    result = await session.execute(
        select(Progress)
        .where(Progress.user_id == progress.user_id, Progress.date < progress.date)
        .order_by(Progress.date.desc())
        .limit(1)
    )
    
    prev_progress = result.scalar_one_or_none()
    
    # Формируем текст с информацией о прогрессе
    text = f"<b>📊 Прогресс от {progress.date.strftime('%d.%m.%Y')}</b>\n\n"
    
    # Добавляем информацию о весе
    if progress.weight:
        text += f"<b>Вес:</b> {progress.weight} кг"
        if prev_progress and prev_progress.weight:
            diff = progress.weight - prev_progress.weight
            text += f" ({diff:+.1f} кг с {prev_progress.date.strftime('%d.%m.%Y')})"
        text += "\n"
    
    # Добавляем информацию о процентах жира
    if progress.body_fat_percentage:
        text += f"<b>Процент жира:</b> {progress.body_fat_percentage}%"
        if prev_progress and prev_progress.body_fat_percentage:
            diff = progress.body_fat_percentage - prev_progress.body_fat_percentage
            text += f" ({diff:+.1f}% с {prev_progress.date.strftime('%d.%m.%Y')})"
        text += "\n"
    
    text += "\n<b>Обхваты:</b>\n"
    
    # Добавляем информацию об обхватах
    measurements = [
        ("Грудь", "chest"),
        ("Талия", "waist"),
        ("Бёдра", "hips"),
        ("Бицепс (левый)", "biceps_left"),
        ("Бицепс (правый)", "biceps_right"),
        ("Бедро (левое)", "thigh_left"),
        ("Бедро (правое)", "thigh_right"),
        ("Икра (левая)", "calf_left"),
        ("Икра (правая)", "calf_right")
    ]
    
    for name, attr in measurements:
        value = getattr(progress, attr)
        if value:
            text += f"• {name}: {value} см"
            if prev_progress and getattr(prev_progress, attr):
                diff = value - getattr(prev_progress, attr)
                text += f" ({diff:+.1f} см)"
            text += "\n"
    
    # Добавляем заметки
    if progress.notes:
        text += f"\n<b>Заметки:</b>\n{progress.notes}\n"
    
    # Создаем клавиатуру с действиями
    builder = InlineKeyboardBuilder()
    
    # Если есть фотографии, добавляем кнопку для просмотра
    if progress.photos:
        builder.row(InlineKeyboardButton(
            text="📷 Просмотреть фото",
            callback_data=f"view_progress_photos_{progress.id}"
        ))
    
    # Добавляем кнопку "Назад"
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="view_progress"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data.startswith("view_progress_photos_"))
async def process_view_progress_photos(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик просмотра фотографий прогресса
    """
    # Получаем id записи о прогрессе
    progress_id = int(callback.data.split("_")[-1])
    
    # Получаем запись о прогрессе
    progress = await session.get(Progress, progress_id, options=[selectinload(Progress.photos)])
    
    if not progress or not progress.photos:
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "Фотографии не найдены.",
            reply_markup=back_keyboard(f"view_progress_record_{progress_id}")
        )
        await callback.answer()
        return
    
    # Отправляем сообщение с информацией о фотографиях
    await callback.message.edit_text(
        f"<b>📷 Фотографии прогресса от {progress.date.strftime('%d.%m.%Y')}</b>\n\n"
        f"Сейчас я отправлю тебе фотографии, которые ты загрузил в этот день.",
        reply_markup=back_keyboard(f"view_progress_record_{progress_id}")
    )
    
    # Отправляем фотографии
    for photo in progress.photos:
        # Проверяем, существует ли файл
        if os.path.exists(photo.photo_path):
            # Отправляем фото
            caption = f"Фото {photo.photo_type} от {progress.date.strftime('%d.%m.%Y')}"
            await callback.message.answer_photo(
                FSInputFile(photo.photo_path),
                caption=caption
            )
    
    await callback.answer()


@router.callback_query(F.data == "progress_charts")
async def process_progress_charts(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Графики"
    """
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем записи о прогрессе пользователя (последние 30)
    result = await session.execute(
        select(Progress)
        .where(Progress.user_id == user.id)
        .order_by(Progress.date.asc())
        .limit(30)
    )
    
    progress_records = result.scalars().all()
    
    if not progress_records:
        # Если у пользователя нет записей о прогрессе
        await callback.message.edit_text(
            "<b>📈 Графики</b>\n\n"
            "У тебя пока нет достаточно данных для построения графиков.\n\n"
            "Начни отслеживать свой прогресс, добавив замеры!",
            reply_markup=back_keyboard("progress_menu")
        )
    else:
        # Если у пользователя есть записи о прогрессе
        # Создаем клавиатуру с выбором типа графика
        builder = InlineKeyboardBuilder()
        
        if any(p.weight for p in progress_records):
            builder.row(InlineKeyboardButton(text="⚖️ Вес", callback_data="chart_weight"))
        
        if any(p.body_fat_percentage for p in progress_records):
            builder.row(InlineKeyboardButton(text="📉 Процент жира", callback_data="chart_body_fat"))
        
        # Добавляем кнопки для обхватов
        measurements = [
            ("Грудь", "chest"),
            ("Талия", "waist"),
            ("Бёдра", "hips"),
            ("Бицепсы", "biceps"),
            ("Бёдра", "thighs"),
            ("Икры", "calves")
        ]
        
        for name, attr in measurements:
            if attr == "biceps" and (any(p.biceps_left for p in progress_records) or any(p.biceps_right for p in progress_records)):
                builder.row(InlineKeyboardButton(text=f"📏 {name}", callback_data=f"chart_{attr}"))
            elif attr == "thighs" and (any(p.thigh_left for p in progress_records) or any(p.thigh_right for p in progress_records)):
                builder.row(InlineKeyboardButton(text=f"📏 {name}", callback_data=f"chart_{attr}"))
            elif attr == "calves" and (any(p.calf_left for p in progress_records) or any(p.calf_right for p in progress_records)):
                builder.row(InlineKeyboardButton(text=f"📏 {name}", callback_data=f"chart_{attr}"))
            elif attr not in ["biceps", "thighs", "calves"] and any(getattr(p, attr) for p in progress_records):
                builder.row(InlineKeyboardButton(text=f"📏 {name}", callback_data=f"chart_{attr}"))
        
        # Добавляем кнопку "Назад"
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="view_progress"))
        
        await callback.message.edit_text(
            "<b>📈 Графики</b>\n\n"
            "Выбери параметр, для которого хочешь увидеть график:",
            reply_markup=builder.as_markup()
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("chart_"))
async def process_chart(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик выбора типа графика
    """
    # Получаем тип графика
    chart_type = callback.data.split("_")[1]
    
    # Получаем пользователя
    user = await get_user(session, callback.from_user.id)
    
    # Получаем записи о прогрессе пользователя (последние 30)
    result = await session.execute(
        select(Progress)
        .where(Progress.user_id == user.id)
        .order_by(Progress.date.asc())
        .limit(30)
    )
    
    progress_records = result.scalars().all()
    
    if not progress_records:
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "Нет данных для построения графика.",
            reply_markup=back_keyboard("progress_charts")
        )
        await callback.answer()
        return
    
    # Создаем график в зависимости от типа
    if chart_type == "weight":
        # График веса
        dates = [p.date for p in progress_records if p.weight]
        values = [p.weight for p in progress_records if p.weight]
        title = "Динамика веса"
        ylabel = "Вес (кг)"
    elif chart_type == "body_fat":
        # График процента жира
        dates = [p.date for p in progress_records if p.body_fat_percentage]
        values = [p.body_fat_percentage for p in progress_records if p.body_fat_percentage]
        title = "Динамика процента жира"
        ylabel = "Процент жира (%)"
    elif chart_type == "chest":
        # График обхвата груди
        dates = [p.date for p in progress_records if p.chest]
        values = [p.chest for p in progress_records if p.chest]
        title = "Динамика обхвата груди"
        ylabel = "Обхват (см)"
    elif chart_type == "waist":
        # График обхвата талии
        dates = [p.date for p in progress_records if p.waist]
        values = [p.waist for p in progress_records if p.waist]
        title = "Динамика обхвата талии"
        ylabel = "Обхват (см)"
    elif chart_type == "hips":
        # График обхвата бедер
        dates = [p.date for p in progress_records if p.hips]
        values = [p.hips for p in progress_records if p.hips]
        title = "Динамика обхвата бёдер"
        ylabel = "Обхват (см)"
    elif chart_type == "biceps":
        # График обхвата бицепсов (левый и правый)
        dates_left = [p.date for p in progress_records if p.biceps_left]
        values_left = [p.biceps_left for p in progress_records if p.biceps_left]
        dates_right = [p.date for p in progress_records if p.biceps_right]
        values_right = [p.biceps_right for p in progress_records if p.biceps_right]
        title = "Динамика обхвата бицепсов"
        ylabel = "Обхват (см)"
        
        # Создаем график с двумя линиями
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(dates_left, values_left, 'b-', label='Левый')
        ax.plot(dates_right, values_right, 'r-', label='Правый')
        
        # Настройка графика
        ax.set_title(title)
        ax.set_xlabel("Дата")
        ax.set_ylabel(ylabel)
        ax.grid(True)
        ax.legend()
        
        # Форматирование дат на оси X
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        plt.xticks(rotation=45)
        
        # Настройка внешнего вида графика
        plt.tight_layout()
        
        # Сохраняем график в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Отправляем график
        await callback.message.answer_photo(
            buf,
            caption=f"📈 {title}",
            reply_markup=back_keyboard("progress_charts")
        )
        
        # Закрываем график
        plt.close()
        
        await callback.answer()
        return
    elif chart_type == "thighs":
        # График обхвата бедер (левое и правое)
        dates_left = [p.date for p in progress_records if p.thigh_left]
        values_left = [p.thigh_left for p in progress_records if p.thigh_left]
        dates_right = [p.date for p in progress_records if p.thigh_right]
        values_right = [p.thigh_right for p in progress_records if p.thigh_right]
        title = "Динамика обхвата бёдер"
        ylabel = "Обхват (см)"
        
        # Создаем график с двумя линиями
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(dates_left, values_left, 'b-', label='Левое')
        ax.plot(dates_right, values_right, 'r-', label='Правое')
        
        # Настройка графика
        ax.set_title(title)
        ax.set_xlabel("Дата")
        ax.set_ylabel(ylabel)
        ax.grid(True)
        ax.legend()
        
        # Форматирование дат на оси X
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        plt.xticks(rotation=45)
        
        # Настройка внешнего вида графика
        plt.tight_layout()
        
        # Сохраняем график в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Отправляем график
        await callback.message.answer_photo(
            buf,
            caption=f"📈 {title}",
            reply_markup=back_keyboard("progress_charts")
        )
        
        # Закрываем график
        plt.close()
        
        await callback.answer()
        return
    elif chart_type == "calves":
        # График обхвата икр (левая и правая)
        dates_left = [p.date for p in progress_records if p.calf_left]
        values_left = [p.calf_left for p in progress_records if p.calf_left]
        dates_right = [p.date for p in progress_records if p.calf_right]
        values_right = [p.calf_right for p in progress_records if p.calf_right]
        title = "Динамика обхвата икр"
        ylabel = "Обхват (см)"
        
        # Создаем график с двумя линиями
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(dates_left, values_left, 'b-', label='Левая')
        ax.plot(dates_right, values_right, 'r-', label='Правая')
        
        # Настройка графика
        ax.set_title(title)
        ax.set_xlabel("Дата")
        ax.set_ylabel(ylabel)
        ax.grid(True)
        ax.legend()
        
        # Форматирование дат на оси X
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        plt.xticks(rotation=45)
        
        # Настройка внешнего вида графика
        plt.tight_layout()
        
        # Сохраняем график в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Отправляем график
        await callback.message.answer_photo(
            buf,
            caption=f"📈 {title}",
            reply_markup=back_keyboard("progress_charts")
        )
        
        # Закрываем график
        plt.close()
        
        await callback.answer()
        return
    else:
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "Неизвестный тип графика.",
            reply_markup=back_keyboard("progress_charts")
        )
        await callback.answer()
        return
    
    # Проверяем, что есть данные для построения графика
    if not dates or not values:
        await callback.message.edit_text(
            "<b>❌ Ошибка</b>\n\n"
            "Нет данных для построения графика.",
            reply_markup=back_keyboard("progress_charts")
        )
        await callback.answer()
        return
    
    # Создаем график
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(dates, values, 'b-')
    
    # Настройка графика
    ax.set_title(title)
    ax.set_xlabel("Дата")
    ax.set_ylabel(ylabel)
    ax.grid(True)
    
    # Форматирование дат на оси X
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    plt.xticks(rotation=45)
    
    # Настройка внешнего вида графика
    plt.tight_layout()
    
    # Сохраняем график в буфер
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    # Отправляем график
    await callback.message.answer_photo(
        buf,
        caption=f"📈 {title}",
        reply_markup=back_keyboard("progress_charts")
    )
    
    # Закрываем график
    plt.close()
    
    await callback.answer()


async def get_user(session: AsyncSession, telegram_id: int) -> User:
    """
    Получить пользователя по telegram_id
    """
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    return user
