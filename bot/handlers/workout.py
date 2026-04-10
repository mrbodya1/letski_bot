import re
from datetime import date
from aiogram import types
from aiogram.dispatcher.filters import Command

from flask_app import dp, telegram_bot
from config import MAIN_CHAT_ID, STREAK_BADGES, ADMIN_IDS
from bot.utils.supabase import (
    get_profile, get_sunday_schedule, create_workout,
    get_user_workout_for_sunday, update_workout_repost,
    get_random_prize_for_user, award_prize
)
from bot.keyboards.inline import get_rating_keyboard
from bot.utils.helpers import is_sunday, calculate_pace, format_pace


def is_admin(user_id: int) -> bool:
    """Проверка на админа"""
    return user_id in ADMIN_IDS


def parse_workout_caption(caption: str) -> dict:
    result = {"km": None, "min": None, "error": None}
    
    km_match = re.search(r'#km(\d+(?:[.,]\d+)?)', caption, re.IGNORECASE)
    if km_match:
        km_str = km_match.group(1).replace(',', '.')
        result["km"] = float(km_str)
    else:
        result["error"] = "❌ Не найден тег #kmX"
        return result
    
    min_match = re.search(r'#min(\d+)', caption, re.IGNORECASE)
    if min_match:
        result["min"] = int(min_match.group(1))
    else:
        result["error"] = "❌ Не найден тег #minX"
        return result
    
    return result


@dp.message_handler(content_types=['photo'])
async def handle_workout_photo(message: types.Message):
    user_id = message.from_user.id
    user_is_admin = is_admin(user_id)
    
    # ========== ПРОВЕРКИ (ПРОПУСКАЕМ ДЛЯ АДМИНА) ==========
    if not user_is_admin:
        # Проверка на воскресенье
        if not is_sunday():
            await message.reply("❌ Отчеты принимаются только по воскресеньям!")
            return
    
    # Получаем профиль
    profile = await get_profile(user_id)
    if not profile:
        await message.reply("❌ Сначала зарегистрируйся командой /start")
        return
    
    # Проверка подписи
    if not message.caption:
        await message.reply(
            "❌ Нужна подпись к фото!\n\n"
            "Формат: #kmX #minX\n"
            "Пример: #km10 #min45"
        )
        return
    
    caption = message.caption
    parsed = parse_workout_caption(caption)
    
    if parsed["error"]:
        await message.reply(parsed["error"])
        return
    
    if not user_is_admin:
        # Обычные проверки для обычных пользователей
        if parsed["km"] < 5:
            await message.reply("❌ Минимальная дистанция — 5 км")
            return
        
        if parsed["min"] < 30:
            await message.reply("❌ Минимальное время — 30 минут")
            return
    
    today = date.today().isoformat()
    schedule = await get_sunday_schedule(today)
    
    if not schedule:
        if user_is_admin:
            # Для админа создаём расписание автоматически
            from bot.utils.supabase import get_all_coaches, create_sunday_schedule
            coaches = await get_all_coaches()
            if coaches:
                coach_id = coaches[0]["id"]
                await create_sunday_schedule(sunday_date=today, coach_id=coach_id)
                schedule = await get_sunday_schedule(today)
            else:
                await message.reply("❌ Нет тренеров в базе. Добавь тренера.")
                return
        else:
            await message.reply("❌ На сегодня нет расписания тренировки.")
            return
    
    if not schedule or not schedule.get("coach_id"):
        if user_is_admin:
            await message.reply("❌ Не удалось назначить тренера. Проверь список тренеров.")
        else:
            await message.reply("❌ На сегодня не назначен тренер.")
        return
    
    # Проверка на повторную тренировку (пропускаем для админа)
    if not user_is_admin:
        existing = await get_user_workout_for_sunday(profile["id"], today)
        if existing:
            await message.reply("❌ Ты уже отправлял отчет за сегодня!")
            return
    
    # Сохраняем тренировку
    workout = await create_workout(
        user_id=profile["id"],
        coach_id=schedule["coach_id"],
        sunday_date=today,
        distance_km=parsed["km"],
        duration_min=parsed["min"],
        photo_id=message.photo[-1].file_id
    )
    
    if not workout:
        await message.reply("❌ Ошибка при сохранении тренировки.")
        return
    
    # Публикуем в общий чат
    coach_name = schedule.get("coaches", {}).get("full_name", "Неизвестный тренер")
    pace = calculate_pace(parsed["km"], parsed["min"])
    
    # Для админа добавляем пометку "ТЕСТ" в сообщение
    admin_prefix = "🧪 <b>ТЕСТОВАЯ ТРЕНИРОВКА</b>\n\n" if user_is_admin else ""
    
    group_message = await telegram_bot.send_photo(
        chat_id=MAIN_CHAT_ID,
        photo=message.photo[-1].file_id,
        caption=(
            f"{admin_prefix}"
            f"✅ <b>Тренировка принята!</b>\n\n"
            f"👤 {profile['full_name']}\n"
            f"👟 Тренер: {coach_name}\n"
            f"📏 Дистанция: {parsed['km']} км\n"
            f"⏱ Время: {parsed['min']} мин\n"
            f"⚡️ Темп: {format_pace(pace)} мин/км\n"
            f"🔥 Серия: {profile['sunday_streak'] + 1} воскресений\n\n"
            f"#km{parsed['km']} #min{parsed['min']}"
        ),
        parse_mode="HTML"
    )
    
    await update_workout_repost(workout["id"], group_message.message_id)
    
    # Получаем обновлённый профиль
    updated_profile = await get_profile(user_id)
    new_streak = updated_profile["sunday_streak"]
    
    response_text = (
        f"{'🧪 ТЕСТОВАЯ ' if user_is_admin else ''}"
        f"✅ <b>Тренировка записана!</b>\n\n"
        f"📊 {parsed['km']} км / {parsed['min']} мин\n"
        f"⚡️ Темп: {format_pace(pace)} мин/км\n"
        f"🔥 Текущая серия: {new_streak} воскресений\n"
    )
    
    # Проверяем бейджи и призы (работает одинаково для всех)
    if new_streak in STREAK_BADGES:
        response_text += f"\n🏅 <b>НОВЫЙ БЕЙДЖ!</b>\n🔥 Серия {new_streak} недель!\n"
        
        prize = await get_random_prize_for_user(profile["id"])
        if prize:
            await award_prize(profile["id"], prize["id"], f"streak_{new_streak}")
            response_text += f"\n🎁 <b>ТЫ ВЫИГРАЛ ПРИЗ!</b>\n{prize['name']}\n"
    
    await message.reply(response_text, parse_mode="HTML")
    
    # Предлагаем оценить тренера
    await message.answer(
        f"⭐️ Пожалуйста, оцени тренера {coach_name}:",
        reply_markup=get_rating_keyboard(workout["id"])
    )


@dp.message_handler(Command("check_sunday"))
async def cmd_check_sunday(message: types.Message):
    if is_sunday():
        await message.answer("✅ Сегодня воскресенье! Можно отправлять отчеты.")
    else:
        if is_admin(message.from_user.id):
            await message.answer("👑 Для админа ограничений нет — можешь отправлять тренировки в любой день!")
        else:
            await message.answer("❌ Сегодня не воскресенье. Отчеты не принимаются.")
