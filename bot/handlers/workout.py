from aiogram import Router, types, Bot
from aiogram.filters import Command
from datetime import datetime, date, timedelta
import re

from config import MAIN_CHAT_ID, SUNDAY_WEEKDAY, STREAK_BADGES, ADMIN_IDS
from bot.utils.supabase import (
    get_profile, get_sunday_schedule, create_workout, 
    get_user_workout_for_sunday, update_workout_repost,
    get_random_prize_for_user, award_prize
)

router = Router()


def is_sunday() -> bool:
    """Проверяет, сегодня воскресенье или нет"""
    return datetime.now().weekday() == SUNDAY_WEEKDAY


def parse_workout_caption(caption: str) -> dict:
    """Парсит подпись вида #dayX #kmX #tX"""
    result = {"day": None, "km": None, "min": None}
    
    # Ищем #dayX
    day_match = re.search(r'#day(\d+)', caption, re.IGNORECASE)
    if day_match:
        result["day"] = int(day_match.group(1))
    
    # Ищем #kmX
    km_match = re.search(r'#km(\d+(?:\.\d+)?)', caption, re.IGNORECASE)
    if km_match:
        result["km"] = float(km_match.group(1))
    
    # Ищем #tX
    min_match = re.search(r'#t(\d+)', caption, re.IGNORECASE)
    if min_match:
        result["min"] = int(min_match.group(1))
    
    return result


@router.message(lambda message: message.photo and message.caption)
async def handle_workout_photo(message: types.Message, bot: Bot):
    """Обработка фото с отчетом о тренировке"""
    
    # Проверяем, воскресенье ли сегодня
    if not is_sunday():
        await message.reply("❌ Отчеты принимаются только по воскресеньям!")
        return
    
    user_id = message.from_user.id
    
    # Получаем профиль
    profile = await get_profile(user_id)
    if not profile:
        await message.reply("❌ Сначала зарегистрируйся командой /start")
        return
    
    # Парсим подпись
    caption = message.caption
    parsed = parse_workout_caption(caption)
    
    # Проверки
    if not parsed["km"] or not parsed["min"]:
        await message.reply(
            "❌ Неверный формат подписи!\n\n"
            "Нужно указать:\n"
            "#dayX #kmX #tX\n\n"
            "Например: #day1 #km10 #t45"
        )
        return
    
    if parsed["km"] < 5:
        await message.reply("❌ Минимальная дистанция — 5 км")
        return
    
    if parsed["min"] < 30:
        await message.reply("❌ Минимальное время — 30 минут")
        return
    
    # Получаем расписание на сегодня
    today = date.today().isoformat()
    schedule = await get_sunday_schedule(today)
    
    if not schedule:
        await message.reply("❌ На сегодня нет расписания тренировки. Обратись к администратору.")
        return
    
    if not schedule.get("coach_id"):
        await message.reply("❌ На сегодня не назначен тренер. Обратись к администратору.")
        return
    
    # Проверяем, нет ли уже отчета за сегодня
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
        await message.reply("❌ Ошибка при сохранении тренировки. Попробуй позже.")
        return
    
    # Публикуем в общий чат
    coach_name = schedule.get("coaches", {}).get("full_name", "Неизвестный тренер")
    
    group_message = await bot.send_photo(
        chat_id=MAIN_CHAT_ID,
        photo=message.photo[-1].file_id,
        caption=(
            f"✅ <b>Тренировка принята!</b>\n\n"
            f"👤 {profile['full_name']}\n"
            f"👟 Тренер: {coach_name}\n"
            f"📏 Дистанция: {parsed['km']} км\n"
            f"⏱ Время: {parsed['min']} мин\n"
            f"⚡️ Темп: {round(parsed['min'] / parsed['km'], 2)} мин/км\n"
            f"🔥 Серия: {profile['sunday_streak'] + 1} воскресений\n\n"
            f"#{profile['full_name'].replace(' ', '')} #day{parsed['day']} #km{parsed['km']} #t{parsed['min']}"
        ),
        parse_mode="HTML"
    )
    
    # Сохраняем ID сообщения в общем чате
    await update_workout_repost(workout["id"], group_message.message_id)
    
    # Получаем обновленный профиль (серия уже обновлена триггером в БД)
    updated_profile = await get_profile(user_id)
    new_streak = updated_profile["sunday_streak"]
    
    # Проверяем, нужно ли выдать бейдж или приз
    response_text = (
        f"✅ <b>Тренировка записана!</b>\n\n"
        f"📊 День {parsed['day']}: {parsed['km']} км / {parsed['min']} мин\n"
        f"⚡️ Темп: {round(parsed['min'] / parsed['km'], 2)} мин/км\n"
        f"🔥 Текущая серия: {new_streak} воскресений\n"
    )
    
    # Проверяем бейджи за серии
    if new_streak in STREAK_BADGES:
        response_text += f"\n🏅 <b>НОВЫЙ БЕЙДЖ!</b>\n🔥 Серия {new_streak} недель!\n"
        
        # Выдаем случайный приз
        prize = await get_random_prize_for_user(profile["id"])
        if prize:
            await award_prize(profile["id"], prize["id"], f"streak_{new_streak}")
            response_text += f"\n🎁 <b>ТЫ ВЫИГРАЛ ПРИЗ!</b>\n{prize['name']}\n"
    
    await message.reply(response_text, parse_mode="HTML")
    
    # Предлагаем оценить тренера
    from bot.keyboards.inline import get_rating_keyboard
    await message.answer(
        f"⭐️ Пожалуйста, оцени тренера {coach_name}:",
        reply_markup=get_rating_keyboard(workout["id"])
    )


@router.message(Command("check_sunday"))
async def cmd_check_sunday(message: types.Message):
    """Проверить, воскресенье ли сегодня (для тестов)"""
    if is_sunday():
        await message.answer("✅ Сегодня воскресенье! Можно отправлять отчеты.")
    else:
        await message.answer("❌ Сегодня не воскресенье. Отчеты не принимаются.")
