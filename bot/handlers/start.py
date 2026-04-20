from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup

from flask_app import dp
from bot.utils.supabase import get_profile, create_profile
from bot.keyboards.reply import get_gender_keyboard, get_main_menu_keyboard
from config import WEBHOOK_HOST


class RegistrationState(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_gender = State()


@dp.message_handler(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    
    profile = await get_profile(user_id)
    
    if profile:
        await message.answer(
            f"👋 С возвращением, {profile['full_name']}!\n\n"
            f"📊 Твоя статистика:\n"
            f"• Серия воскресений: {profile['sunday_streak']}\n"
            f"• Всего тренировок: {profile['total_sundays']}\n"
            f"• Общий км: {profile['total_km']} км\n\n"
            f"Жду твой отчет в это воскресенье! 🏃‍♂️",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await message.answer(
            "Привет! Добро пожаловать в «Длительную» от школы спорта LETSKI\n\n"
            "Это бесплатные воскресные тренировки в 09:00 в парке Маяковского, где мы:\n"
            "— бегаем вместе\n"
            "— знакомимся и общаемся\n"
            "— становимся сильнее от недели к неделе\n\n"
            "Скоро здесь появятся твои тренировки, серии и достижения, а еще мы будем раздавать подарки! 🙂\n\n"
            "Но сначала давай познакомимся.\n\n"
            "Как тебя зовут?\n\n"
            "Напиши Имя и Фамилию👇"
        )
        await RegistrationState.waiting_for_full_name.set()


@dp.message_handler(state=RegistrationState.waiting_for_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    full_name = message.text.strip()
    
    if len(full_name.split()) < 2:
        await message.answer("❌ Пожалуйста, введи Имя и Фамилию через пробел:")
        return
    
    await state.update_data(full_name=full_name)
    await message.answer(
        "Отлично! Теперь укажи свой пол:",
        reply_markup=get_gender_keyboard()
    )
    await RegistrationState.waiting_for_gender.set()


@dp.message_handler(state=RegistrationState.waiting_for_gender)
async def process_gender(message: types.Message, state: FSMContext):
    gender_text = message.text.strip()
    
    if gender_text not in ["👨 Мужской", "👩 Женский"]:
        await message.answer("❌ Пожалуйста, выбери пол из предложенных вариантов:")
        return
    
    gender = "М" if "Мужской" in gender_text else "Ж"
    data = await state.get_data()
    
    profile = await create_profile(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=data['full_name'],
        gender=gender
    )
    
    if profile:
        await message.answer(
            f"✅ Регистрация завершена!\n\n"
            f"👤 {data['full_name']}\n"
            f"⚥ {gender_text}\n\n"
            f"Теперь ты — часть проекта «Длительная» от команды LETSKI.\n"
            f"Рады видеть в наших воскресных рядах!\n\n"
            f"🏃 Жду твой первый отчёт в это воскресенье.\n"
            f"Всю статистику, правила и полученные призы ты найдёшь в своём личном кабинете (кнопка в меню).\n\n"
            f"💬 Общий чат участников: t.me/letski_ekb",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Произошла ошибка при регистрации. Попробуй позже.")
    
    await state.finish()


@dp.message_handler(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📸 <b>Пример оформления отчёта:</b>\n\n"
        "1️⃣ Открой свой трекер (Strava, Garmin, Nike Run Club и т.д.)\n"
        "2️⃣ Сделай скриншот с дистанцией и временем\n"
        "3️⃣ В подписи к фото укажи: <code>#kmX #minX</code>\n\n"
        "Вот так выглядит правильный отчёт 👇",
        parse_mode="HTML"
    )
    
    await message.answer_photo(
        photo="AgACAgIAAxkBAAPUaeZeIZuttQ-RrCW92HhBWxtRr4kAAvsUaxtqozlLxAf-lwXhkF8BAAMCAAN3AAM7BA",
        caption="#km20 #min132"
    )


@dp.message_handler(Command("profile"))
async def cmd_profile(message: types.Message):
    user_id = message.from_user.id
    profile = await get_profile(user_id)
    
    if not profile:
        await message.answer("❌ Ты еще не зарегистрирован. Напиши /start")
        return
    
    await message.answer(
        f"👤 <b>ТВОЙ ПРОФИЛЬ</b>\n\n"
        f"Имя: {profile['full_name']}\n"
        f"Пол: {profile['gender']}\n"
        f"🔥 Серия: {profile['sunday_streak']} воскресений\n"
        f"🏆 Рекорд: {profile['max_sunday_streak']} воскресений\n"
        f"🏃 Тренировок: {profile['total_sundays']}\n"
        f"📏 Всего км: {profile['total_km']} км",
        parse_mode="HTML"
    )


# ========== ОБРАБОТЧИКИ КНОПОК МЕНЮ ==========
@dp.message_handler(lambda message: message.text == "📊 Мой профиль")
async def button_profile(message: types.Message):
    await cmd_profile(message)


@dp.message_handler(lambda message: message.text == "ℹ️ Помощь")
async def button_help(message: types.Message):
    await cmd_help(message)
