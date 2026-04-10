import re
import hashlib
from datetime import date
from aiogram import types
from aiogram.dispatcher.filters import Command

from flask_app import dp, telegram_bot
from config import MAIN_CHAT_ID, STREAK_BADGES, ADMIN_IDS
from bot.utils.supabase import (
    get_profile, get_sunday_schedule, create_workout,
    get_random_prize_for_user, award_prize, update_workout_repost,
    get_all_coaches, create_sunday_schedule as create_schedule,
    supabase
)
from bot.keyboards.inline import get_rating_keyboard
from bot.utils.helpers import calculate_pace, format_pace


# Кэш для защиты от повторной обработки сообщений
processed_messages = set()


def is_admin(user_id: int) -> bool:
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
    # ========== ЗАЩИТА ОТ ПОВТОРНОЙ ОБРАБОТКИ ==========
    msg_id = f"{message.chat.id}:{message.message_id}"
    if msg_id in processed_messages:
        print(f"⚠️ Сообщение {msg_id} уже обработано, пропускаем")
        return
    processed_messages.add(msg_id)
    
    # Очищаем старые сообщения из кэша (чтобы не рос бесконечно)
    if len(processed_messages) > 100:
        processed_messages.clear()
    
    user_id = message.from_user.id
    
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
    
    today = date.today().isoformat()
    
    # Получаем или создаём расписание
    schedule = await get_sunday_schedule(today)
    if not schedule:
        coaches = await get_all_coaches()
        if coaches:
            coach_id = coaches[0]["id"]
            await create_schedule(sunday_date=today, coach_id=coach_id)
            schedule = await get_sunday_schedule(today)
    
    if not schedule or not schedule.get("coach_id"):
        await message.reply("❌ Нет тренера. Добавь тренера через админку.")
        return
    
    # Сохраняем тренировку (триггеры БД обновят статистику)
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
    
    # Получаем обновлённый профиль (триггеры уже сработали)
    updated_profile = await get_profile(user_id)
    new_streak = updated_profile.get("sunday_streak", 0) or 0
    total_km = updated_profile.get("total_km", 0) or 0
    total_sundays = updated_profile.get("total_sundays", 0) or 0
    
    # Публикуем в общий чат
    coach_name = schedule.get("coaches", {}).get("full_name", "Неизвестный тренер")
    pace = calculate_pace(parsed["km"], parsed["min"])
    
    try:
        group_message = await telegram_bot.send_photo(
            chat_id=MAIN_CHAT_ID,
            photo=message.photo[-1].file_id,
            caption=(
                f"🧪 <b>ТЕСТОВАЯ ТРЕНИРОВКА</b>\n\n"
                f"✅ <b>Тренировка принята!</b>\n\n"
                f"👤 {profile['full_name']}\n"
                f"👟 Тренер: {coach_name}\n"
                f"📏 Дистанция: {parsed['km']} км\n"
                f"⏱ Время: {parsed['min']} мин\n"
                f"⚡️ Темп: {format_pace(pace)} мин/км\n"
                f"🔥 Серия: {new_streak} воскресений\n\n"
                f"#km{parsed['km']} #min{parsed['min']}"
            ),
            parse_mode="HTML"
        )
        await update_workout_repost(workout["id"], group_message.message_id)
    except Exception as e:
        print(f"⚠️ Не удалось отправить в общий чат: {e}")
    
    response_text = (
        f"🧪 <b>ТЕСТОВАЯ ТРЕНИРОВКА ЗАПИСАНА!</b>\n\n"
        f"📊 {parsed['km']} км / {parsed['min']} мин\n"
        f"⚡️ Темп: {format_pace(pace)} мин/км\n"
        f"🔥 Текущая серия: {new_streak} воскресений\n"
        f"🏃 Всего тренировок: {total_sundays}\n"
        f"📏 Всего км: {total_km}\n"
    )
    
    # ========== ПРОВЕРЯЕМ БЕЙДЖИ И ПРИЗЫ ==========
    # Бейдж за первую тренировку
    if total_sundays == 1:
        existing = supabase.table("badges").select("*").eq("user_id", profile["id"]).eq("badge_type", "first_workout").execute()
        if not existing.data:
            supabase.table("badges").insert({
                "user_id": profile["id"],
                "badge_type": "first_workout",
                "awarded_at": "now()"
            }).execute()
            response_text += "\n🏅 <b>НОВЫЙ БЕЙДЖ!</b>\n🚀 Первый шаг\n"
    
    # Бейджи и призы за серии (4, 8, 12)
    if new_streak in STREAK_BADGES:
        badge_type = STREAK_BADGES[new_streak]
        
        # Бейдж
        existing_badge = supabase.table("badges").select("*").eq("user_id", profile["id"]).eq("badge_type", badge_type).execute()
        if not existing_badge.data:
            supabase.table("badges").insert({
                "user_id": profile["id"],
                "badge_type": badge_type,
                "awarded_at": "now()"
            }).execute()
            response_text += f"\n🏅 <b>НОВЫЙ БЕЙДЖ!</b>\n🔥 Серия {new_streak} тренировок!\n"
        
        # Приз (выдаётся независимо от бейджа)
        existing_prize = supabase.table("user_prizes").select("*").eq("user_id", profile["id"]).eq("awarded_for", f"streak_{new_streak}").execute()
        if not existing_prize.data:
            prize = await get_random_prize_for_user(profile["id"])
            if prize:
                await award_prize(profile["id"], prize["id"], f"streak_{new_streak}")
                response_text += f"\n🎁 <b>ТЫ ВЫИГРАЛ ПРИЗ!</b>\n{prize['name']}\n"
    
    # Бейдж за 100 км
    if total_km >= 100:
        existing = supabase.table("badges").select("*").eq("user_id", profile["id"]).eq("badge_type", "km_100").execute()
        if not existing.data:
            supabase.table("badges").insert({
                "user_id": profile["id"],
                "badge_type": "km_100",
                "awarded_at": "now()"
            }).execute()
            response_text += "\n🏅 <b>НОВЫЙ БЕЙДЖ!</b>\n🏆 100 км\n"
    
    # Бейдж за 500 км
    if total_km >= 500:
        existing = supabase.table("badges").select("*").eq("user_id", profile["id"]).eq("badge_type", "km_500").execute()
        if not existing.data:
            supabase.table("badges").insert({
                "user_id": profile["id"],
                "badge_type": "km_500",
                "awarded_at": "now()"
            }).execute()
            response_text += "\n🏅 <b>НОВЫЙ БЕЙДЖ!</b>\n👑 500 км\n"
    
    await message.reply(response_text, parse_mode="HTML")
    
    # Предлагаем оценить тренера
    await message.answer(
        f"⭐️ Пожалуйста, оцени тренера {coach_name}:",
        reply_markup=get_rating_keyboard(workout["id"])
    )


@dp.message_handler(Command("check_sunday"))
async def cmd_check_sunday(message: types.Message):
    await message.answer("🧪 Тестовый режим: можно отправлять тренировки в любой день!")


@dp.message_handler(Command("clear_cache"))
async def cmd_clear_cache(message: types.Message):
    """Очистить кэш обработанных сообщений (для админа)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    processed_messages.clear()
    await message.answer("✅ Кэш очищен")
