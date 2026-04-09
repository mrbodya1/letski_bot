from aiogram import Router, types, Bot
from aiogram.filters import Command

from config import ADMIN_IDS
from bot.utils.supabase import (
    get_profile, get_workout_by_id, get_coach, 
    create_rating, has_rating_for_workout
)
from bot.keyboards.inline import get_rating_stars

router = Router()

# Временное хранилище оценок (в продакшене лучше использовать Redis или FSM)
temp_ratings = {}


@router.callback_query(lambda c: c.data.startswith("rate_start:"))
async def start_rating(callback: types.CallbackQuery):
    """Начало оценки тренера"""
    workout_id = callback.data.split(":")[1]
    
    # Проверяем, нет ли уже оценки
    has_rating = await has_rating_for_workout(workout_id)
    if has_rating:
        await callback.answer("Ты уже оценил эту тренировку!", show_alert=True)
        await callback.message.delete()
        return
    
    # Инициализируем временные оценки
    user_id = callback.from_user.id
    temp_ratings[user_id] = {
        "workout_id": workout_id,
        "pro": 0,
        "presentation": 0,
        "friendly": 0
    }
    
    await callback.message.edit_text(
        "🌟 <b>Оценка тренера</b>\n\n"
        "<b>1. Профессионализм</b>\n"
        "Насколько грамотно тренер провел тренировку?",
        reply_markup=get_rating_stars("pro", workout_id, 0),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("rate_pro:"))
async def rate_pro(callback: types.CallbackQuery):
    """Оценка профессионализма"""
    _, workout_id, value = callback.data.split(":")
    user_id = callback.from_user.id
    
    if user_id not in temp_ratings:
        await callback.answer("Сессия истекла, начни заново", show_alert=True)
        return
    
    temp_ratings[user_id]["pro"] = int(value)
    
    await callback.message.edit_text(
        "🌟 <b>Оценка тренера</b>\n\n"
        "<b>2. Подача материала</b>\n"
        "Насколько понятно и интересно тренер объяснял?",
        reply_markup=get_rating_stars("presentation", workout_id, 0),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("rate_presentation:"))
async def rate_presentation(callback: types.CallbackQuery):
    """Оценка подачи"""
    _, workout_id, value = callback.data.split(":")
    user_id = callback.from_user.id
    
    if user_id not in temp_ratings:
        await callback.answer("Сессия истекла, начни заново", show_alert=True)
        return
    
    temp_ratings[user_id]["presentation"] = int(value)
    
    await callback.message.edit_text(
        "🌟 <b>Оценка тренера</b>\n\n"
        "<b>3. Дружелюбность</b>\n"
        "Насколько комфортно и приятно было заниматься?",
        reply_markup=get_rating_stars("friendly", workout_id, 0),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("rate_friendly:"))
async def rate_friendly(callback: types.CallbackQuery):
    """Оценка дружелюбности"""
    _, workout_id, value = callback.data.split(":")
    user_id = callback.from_user.id
    
    if user_id not in temp_ratings:
        await callback.answer("Сессия истекла, начни заново", show_alert=True)
        return
    
    temp_ratings[user_id]["friendly"] = int(value)
    
    # Все оценки собраны, показываем итог
    ratings = temp_ratings[user_id]
    
    await callback.message.edit_text(
        "🌟 <b>Проверь свои оценки:</b>\n\n"
        f"Профессионализм: {'★' * ratings['pro']}{'☆' * (5 - ratings['pro'])}\n"
        f"Подача: {'★' * ratings['presentation']}{'☆' * (5 - ratings['presentation'])}\n"
        f"Дружелюбность: {'★' * ratings['friendly']}{'☆' * (5 - ratings['friendly'])}\n\n"
        f"Всё верно?",
        reply_markup=get_rating_stars("confirm", workout_id, 5),  # 5 означает "подтверждено"
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("rate_confirm:"))
async def confirm_rating(callback: types.CallbackQuery, bot: Bot):
    """Подтверждение и сохранение оценки"""
    workout_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    if user_id not in temp_ratings:
        await callback.answer("Сессия истекла, начни заново", show_alert=True)
        return
    
    ratings = temp_ratings[user_id]
    
    if ratings["pro"] == 0 or ratings["presentation"] == 0 or ratings["friendly"] == 0:
        await callback.answer("Заполни все оценки!", show_alert=True)
        return
    
    # Получаем данные о тренировке
    workout = await get_workout_by_id(workout_id)
    if not workout:
        await callback.answer("Тренировка не найдена", show_alert=True)
        return
    
    profile = await get_profile(user_id)
    
    # Сохраняем оценку
    rating = await create_rating(
        workout_id=workout_id,
        user_id=profile["id"],
        coach_id=workout["coach_id"],
        pro=ratings["pro"],
        presentation=ratings["presentation"],
        friendly=ratings["friendly"]
    )
    
    if rating:
        # Получаем данные тренера
        coach = await get_coach(workout["coach_id"])
        
        # Уведомление админам
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"⭐️ <b>Новая оценка тренеру!</b>\n\n"
                    f"👤 Участник: {profile['full_name']}\n"
                    f"👟 Тренер: {coach['full_name']}\n"
                    f"📅 Дата: {workout['sunday_date']}\n\n"
                    f"Профессионализм: {'★' * ratings['pro']}\n"
                    f"Подача: {'★' * ratings['presentation']}\n"
                    f"Дружелюбность: {'★' * ratings['friendly']}",
                    parse_mode="HTML"
                )
            except:
                pass
        
        await callback.message.edit_text(
            "✅ <b>Спасибо за оценку!</b>\n\n"
            "Твое мнение очень важно для нас! 🙏",
            parse_mode="HTML"
        )
        
        # Очищаем временные данные
        del temp_ratings[user_id]
    else:
        await callback.answer("Ошибка при сохранении", show_alert=True)
    
    await callback.answer()


@router.callback_query(lambda c: c.data == "rate_cancel")
async def cancel_rating(callback: types.CallbackQuery):
    """Отмена оценки"""
    user_id = callback.from_user.id
    if user_id in temp_ratings:
        del temp_ratings[user_id]
    
    await callback.message.edit_text("❌ Оценка отменена")
    await callback.answer()
