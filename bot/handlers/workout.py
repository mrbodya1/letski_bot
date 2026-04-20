import re
import random
from datetime import date
from aiogram import types
from aiogram.dispatcher.filters import Command

from flask_app import dp, telegram_bot
from config import MAIN_CHAT_ID, ADMIN_IDS
from bot.utils.supabase import (
    get_profile, get_sunday_schedule, create_workout,
    get_all_coaches,
    create_sunday_schedule as create_schedule,
    supabase, check_and_award_badges,
    award_prize_with_promo, get_issued_prizes_count_for_workout
)
from bot.keyboards.inline import get_rating_keyboard
from bot.utils.helpers import calculate_pace, format_pace, is_sunday


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
    
    # Очищаем старые сообщения из кэша
    if len(processed_messages) > 100:
        processed_messages.clear()
    
    user_id = message.from_user.id
    user_is_admin = is_admin(user_id)
    
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
    
    # ========== ПРОВЕРКИ ДЛЯ ОБЫЧНЫХ ПОЛЬЗОВАТЕЛЕЙ ==========
    if not user_is_admin:
        # Проверка на воскресенье
        if not is_sunday():
            await message.reply("❌ Отчеты принимаются только по воскресеньям!")
            return
        
        # Проверка на повторную тренировку
        existing = await get_user_workout_for_sunday(profile["id"], today)
        if existing:
            await message.reply("❌ Ты уже отправлял отчет за сегодня!")
            return
    
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
    
    coach_name = schedule.get("coaches", {}).get("full_name", "Неизвестный тренер")
    pace = calculate_pace(parsed["km"], parsed["min"])
    
    # ========== ОТПРАВКА В ОБЩИЙ ЧАТ ОТКЛЮЧЕНА ==========
    # Оставляем только еженедельный отчёт по понедельникам
    
    # Ответ пользователю (в личку)
    if user_is_admin:
        title = "🧪 <b>ТЕСТОВАЯ ТРЕНИРОВКА ЗАПИСАНА!</b>"
    else:
        title = "✅ <b>ТРЕНИРОВКА ЗАПИСАНА!</b>"
    
    response_text = (
        f"{title}\n\n"
        f"📊 {parsed['km']} км / {parsed['min']} мин\n"
        f"⚡️ Темп: {format_pace(pace)} мин/км\n"
        f"🔥 Текущая серия: {new_streak} воскресений\n"
        f"🏃 Всего тренировок: {total_sundays}\n"
        f"📏 Всего км: {total_km}\n"
    )
    
    # ========== ПРОВЕРКА БЕЙДЖЕЙ ==========
    stats = {
        'total_workouts': total_sundays,
        'total_km': total_km,
        'streak': new_streak,
    }
    
    awarded_badges = await check_and_award_badges(profile["id"], stats)
    
    for badge in awarded_badges:
        response_text += f"\n🏅 <b>НОВЫЙ БЕЙДЖ!</b>\n{badge['emoji']} {badge['name']}\n"
    
    # ========== ВЫДАЧА ПРИЗОВ ==========
    all_prizes = supabase.table("prizes_pool").select("*").eq("is_active", True).execute()
    
    if all_prizes.data:
        available_prizes = []
        for prize in all_prizes.data:
            trigger_workouts = prize.get("trigger_workouts", 0) or 0
            
            if total_sundays >= trigger_workouts:
                quota = prize.get("quota_per_workout", 0) or 0
                
                if quota == 0:
                    available_prizes.append(prize)
                else:
                    issued_count = await get_issued_prizes_count_for_workout(prize["id"], today)
                    
                    if issued_count < quota:
                        remaining = quota - issued_count
                        for _ in range(remaining * 2):
                            available_prizes.append(prize)
        
        if available_prizes:
            selected_prize = random.choice(available_prizes)
            
            result = await award_prize_with_promo(
                user_id=profile["id"],
                prize_id=selected_prize["id"],
                awarded_for=f"workout_{today}",
                valid_days=selected_prize.get("valid_days", 14)
            )
            
            if result:
                response_text += (
                    f"\n🎁 <b>Ты получил новый приз!</b>\n"
                    f"Загляни в личный кабинет, чтобы открыть его 🎰\n"
                )
    
    await message.reply(response_text, parse_mode="HTML")
    
    # Предлагаем оценить тренера
    await message.answer(
        f"⭐️ Пожалуйста, оцени тренера {coach_name}:",
        reply_markup=get_rating_keyboard(workout["id"])
    )


@dp.message_handler(Command("check_sunday"))
async def cmd_check_sunday(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer("👑 Админский режим: можно отправлять тренировки в любой день!")
    else:
        await message.answer("ℹ️ Обычные пользователи могут отправлять тренировки только по воскресеньям.")


@dp.message_handler(Command("clear_cache"))
async def cmd_clear_cache(message: types.Message):
    """Очистить кэш обработанных сообщений (для админа)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    processed_messages.clear()
    await message.answer("✅ Кэш очищен")


@dp.message_handler(Command("file_id"))
async def cmd_get_file_id(message: types.Message):
    """Временная команда для получения file_id фото"""
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.reply("❌ Ответь на сообщение с фото, для которого нужно получить file_id")
        return
    
    file_id = message.reply_to_message.photo[-1].file_id
    await message.reply(f"📸 FILE_ID:\n\n{file_id}")
