from aiogram import Router, types, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, timedelta

from config import ADMIN_IDS, MAIN_CHAT_ID
from bot.utils.supabase import (
    get_all_coaches, get_sunday_schedule, 
    create_sunday_schedule, update_sunday_coach,
    get_upcoming_sundays_without_coach, get_rating_by_km
)
from bot.utils.helpers import get_next_sunday, is_sunday

router = Router()


def is_admin(user_id: int) -> bool:
    """Проверка на админа"""
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У тебя нет доступа к админ-панели")
        return
    
    await message.answer(
        "🛠 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        "<b>Команды:</b>\n"
        "/coaches — список тренеров\n"
        "/set_coach YYYY-MM-DD — назначить тренера\n"
        "/next_sunday — инфо о следующем воскресенье\n"
        "/check_coaches — проверить тренировки без тренера\n"
        "/broadcast — рассылка (ответ на сообщение)\n"
        "/top10 — топ-10 по км\n"
        "/add_schedule YYYY-MM-DD — создать расписание",
        parse_mode="HTML"
    )


@router.message(Command("coaches"))
async def cmd_coaches(message: types.Message):
    """Список тренеров"""
    if not is_admin(message.from_user.id):
        return
    
    coaches = await get_all_coaches()
    
    if not coaches:
        await message.answer("❌ Список тренеров пуст")
        return
    
    text = "👟 <b>СПИСОК ТРЕНЕРОВ</b>\n\n"
    for coach in coaches:
        text += f"• <b>{coach['full_name']}</b>\n"
        text += f"  ID: <code>{coach['id']}</code>\n"
        text += f"  Рейтинг: {coach['avg_rating_pro']:.1f}/5 ({coach['total_ratings']} оценок)\n\n"
    
    await message.answer(text, parse_mode="HTML")


@router.message(Command("set_coach"))
async def cmd_set_coach(message: types.Message, command: CommandObject):
    """Назначить тренера на дату: /set_coach 2026-04-13"""
    if not is_admin(message.from_user.id):
        return
    
    args = command.args
    if not args:
        await message.answer("❌ Укажи дату: /set_coach YYYY-MM-DD")
        return
    
    sunday_date = args.strip()
    
    # Проверяем формат даты
    try:
        date.fromisoformat(sunday_date)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используй YYYY-MM-DD")
        return
    
    # Получаем список тренеров
    coaches = await get_all_coaches()
    
    if not coaches:
        await message.answer("❌ Нет тренеров в базе")
        return
    
    # Создаем клавиатуру выбора тренера
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=coach['full_name'],
                callback_data=f"admin_set_coach:{sunday_date}:{coach['id']}"
            )] for coach in coaches
        ] + [[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]]
    )
    
    await message.answer(
        f"👟 Выбери тренера на {sunday_date}:",
        reply_markup=keyboard
    )


@router.callback_query(lambda c: c.data.startswith("admin_set_coach:"))
async def process_set_coach(callback: types.CallbackQuery):
    """Обработка выбора тренера"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    
    _, sunday_date, coach_id = callback.data.split(":")
    
    # Проверяем, есть ли уже расписание
    schedule = await get_sunday_schedule(sunday_date)
    
    if not schedule:
        # Создаем новое расписание
        await create_sunday_schedule(sunday_date=sunday_date, coach_id=coach_id)
        await callback.message.edit_text(f"✅ Создано расписание на {sunday_date} с тренером")
    else:
        # Обновляем существующее
        await update_sunday_coach(sunday_date, coach_id)
        await callback.message.edit_text(f"✅ Тренер на {sunday_date} обновлен")
    
    await callback.answer()


@router.message(Command("next_sunday"))
async def cmd_next_sunday(message: types.Message):
    """Информация о следующем воскресенье"""
    if not is_admin(message.from_user.id):
        return
    
    next_sunday = get_next_sunday()
    schedule = await get_sunday_schedule(next_sunday.isoformat())
    
    if not schedule:
        await message.answer(
            f"📅 На {next_sunday} еще нет расписания.\n"
            f"Создай командой /add_schedule {next_sunday}"
        )
        return
    
    coach_name = schedule.get("coaches", {}).get("full_name", "НЕ НАЗНАЧЕН ⚠️")
    
    await message.answer(
        f"📅 <b>Следующее воскресенье:</b> {next_sunday}\n"
        f"👟 <b>Тренер:</b> {coach_name}\n"
        f"📍 <b>Локация:</b> {schedule.get('location', 'Не указана')}\n"
        f"🕐 <b>Время:</b> {schedule.get('start_time', 'Не указано')}\n"
        f"📋 <b>Формат:</b> {schedule.get('format', 'Не указан')}",
        parse_mode="HTML"
    )


@router.message(Command("check_coaches"))
async def cmd_check_coaches(message: types.Message):
    """Проверить будущие тренировки без тренера"""
    if not is_admin(message.from_user.id):
        return
    
    upcoming = await get_upcoming_sundays_without_coach()
    
    if not upcoming:
        await message.answer("✅ На все будущие воскресенья назначены тренеры!")
        return
    
    text = "⚠️ <b>Воскресенья без тренера:</b>\n\n"
    for s in upcoming:
        text += f"• {s['sunday_date']}\n"
    
    text += "\nНазначь командой /set_coach YYYY-MM-DD"
    
    await message.answer(text, parse_mode="HTML")


@router.message(Command("add_schedule"))
async def cmd_add_schedule(message: types.Message, command: CommandObject):
    """Создать расписание: /add_schedule 2026-04-13"""
    if not is_admin(message.from_user.id):
        return
    
    args = command.args
    if not args:
        await message.answer("❌ Укажи дату: /add_schedule YYYY-MM-DD")
        return
    
    sunday_date = args.strip()
    
    try:
        date.fromisoformat(sunday_date)
    except ValueError:
        await message.answer("❌ Неверный формат даты")
        return
    
    schedule = await create_sunday_schedule(sunday_date=sunday_date)
    
    if schedule:
        await message.answer(
            f"✅ Расписание на {sunday_date} создано!\n"
            f"Теперь назначь тренера: /set_coach {sunday_date}"
        )
    else:
        await message.answer("❌ Ошибка при создании расписания")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, bot: Bot):
    """Рассылка сообщения (ответ на сообщение)"""
    if not is_admin(message.from_user.id):
        return
    
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение, которое хочешь разослать")
        return
    
    # Здесь нужно получить всех пользователей и разослать
    # Пока просто отправляем в общий чат
    
    try:
        await bot.copy_message(
            chat_id=MAIN_CHAT_ID,
            from_chat_id=message.chat.id,
            message_id=message.reply_to_message.message_id
        )
        await message.answer("✅ Сообщение отправлено в общий чат")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(Command("top10"))
async def cmd_top10(message: types.Message):
    """Топ-10 по километражу"""
    if not is_admin(message.from_user.id):
        return
    
    rating = await get_rating_by_km()
    
    if not rating:
        await message.answer("📊 Нет данных для рейтинга")
        return
    
    text = "🏆 <b>ТОП-10 ПО КИЛОМЕТРАЖУ</b>\n\n"
    for i, user in enumerate(rating[:10], 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} <b>{user['full_name']}</b>\n"
        text += f"   📏 {user['total_km']} км | 🔥 {user['sunday_streak']} серия\n\n"
    
    await message.answer(text, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "admin_cancel")
async def admin_cancel(callback: types.CallbackQuery):
    """Отмена админского действия"""
    await callback.message.edit_text("❌ Действие отменено")
    await callback.answer()