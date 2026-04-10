import os
import random
from datetime import date
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Инициализация клиента Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ========== ПРОФИЛИ ==========
async def get_profile(telegram_id: int):
    """Получить профиль по telegram_id"""
    result = supabase.table("profiles").select("*").eq("telegram_id", telegram_id).execute()
    return result.data[0] if result.data else None


async def create_profile(telegram_id: int, username: str, full_name: str, gender: str):
    """Создать новый профиль"""
    data = {
        "telegram_id": telegram_id,
        "username": username,
        "full_name": full_name,
        "gender": gender
    }
    result = supabase.table("profiles").insert(data).execute()
    return result.data[0] if result.data else None


# ========== ТРЕНЕРЫ ==========
async def get_all_coaches():
    """Получить список всех тренеров"""
    result = supabase.table("coaches").select("*").order("full_name").execute()
    return result.data if result.data else []


async def get_coach(coach_id: str):
    """Получить тренера по ID"""
    result = supabase.table("coaches").select("*").eq("id", coach_id).execute()
    return result.data[0] if result.data else None


# ========== РАСПИСАНИЕ ==========
async def get_sunday_schedule(sunday_date: str):
    """Получить расписание на конкретное воскресенье"""
    result = supabase.table("sunday_schedule").select("*, coaches(*)").eq("sunday_date", sunday_date).execute()
    return result.data[0] if result.data else None


async def create_sunday_schedule(sunday_date: str, coach_id: str = None, format_: str = None, location: str = None):
    """Создать запись в расписании"""
    data = {
        "sunday_date": sunday_date,
        "coach_id": coach_id,
        "format": format_,
        "location": location
    }
    result = supabase.table("sunday_schedule").insert(data).execute()
    return result.data[0] if result.data else None


async def update_sunday_coach(sunday_date: str, coach_id: str):
    """Обновить тренера на воскресенье"""
    result = supabase.table("sunday_schedule").update({"coach_id": coach_id}).eq("sunday_date", sunday_date).execute()
    return result.data[0] if result.data else None


async def get_upcoming_sundays_without_coach():
    """Получить будущие воскресенья без тренера"""
    today = date.today().isoformat()
    result = supabase.table("sunday_schedule").select("*").gte("sunday_date", today).is_("coach_id", "null").execute()
    return result.data if result.data else []


# ========== ТРЕНИРОВКИ ==========
async def create_workout(user_id: str, coach_id: str, sunday_date: str, distance_km: float, duration_min: int, photo_id: str = None):
    """Создать запись о тренировке"""
    data = {
        "user_id": user_id,
        "coach_id": coach_id,
        "sunday_date": sunday_date,
        "distance_km": distance_km,
        "duration_min": duration_min,
        "photo_id": photo_id
    }
    result = supabase.table("workouts").insert(data).execute()
    return result.data[0] if result.data else None


async def get_user_workout_for_sunday(user_id: str, sunday_date: str):
    """Проверить, есть ли уже тренировка у пользователя в это воскресенье"""
    result = supabase.table("workouts").select("*").eq("user_id", user_id).eq("sunday_date", sunday_date).execute()
    return result.data[0] if result.data else None


async def get_workout_by_id(workout_id: str):
    """Получить тренировку по ID"""
    result = supabase.table("workouts").select("*").eq("id", workout_id).execute()
    return result.data[0] if result.data else None


async def update_workout_repost(workout_id: str, repost_message_id: int):
    """Обновить ID репоста в общем чате"""
    supabase.table("workouts").update({"repost_message_id": repost_message_id}).eq("id", workout_id).execute()


# ========== ОЦЕНКИ ==========
async def create_rating(workout_id: str, user_id: str, coach_id: str, pro: int, presentation: int, friendly: int, comment: str = None):
    """Создать оценку тренера"""
    data = {
        "workout_id": workout_id,
        "user_id": user_id,
        "coach_id": coach_id,
        "rating_pro": pro,
        "rating_presentation": presentation,
        "rating_friendly": friendly,
        "comment": comment
    }
    result = supabase.table("coach_ratings").insert(data).execute()
    return result.data[0] if result.data else None


async def has_rating_for_workout(workout_id: str):
    """Проверить, есть ли уже оценка за эту тренировку"""
    result = supabase.table("coach_ratings").select("id").eq("workout_id", workout_id).execute()
    return len(result.data) > 0 if result.data else False


# ========== ПРИЗЫ ==========
async def get_random_prize_for_user(user_id: str):
    """Получить случайный приз (без повторов)"""
    # Все активные призы
    all_prizes = supabase.table("prizes_pool").select("*").eq("is_active", True).execute()
    
    if not all_prizes.data:
        return None
    
    # Уже выданные пользователю
    user_prizes = supabase.table("user_prizes").select("prize_id").eq("user_id", user_id).execute()
    used_ids = [up["prize_id"] for up in user_prizes.data] if user_prizes.data else []
    
    available = [p for p in all_prizes.data if p["id"] not in used_ids]
    
    if not available:
        return None
    
    return random.choice(available)


async def award_prize(user_id: str, prize_id: str, awarded_for: str):
    """Выдать приз пользователю"""
    data = {
        "user_id": user_id,
        "prize_id": prize_id,
        "awarded_for": awarded_for
    }
    result = supabase.table("user_prizes").insert(data).execute()
    return result.data[0] if result.data else None


# ========== РЕЙТИНГИ ==========
async def get_rating_by_km():
    """Рейтинг по километражу"""
    result = supabase.table("rating_by_km").select("*").limit(50).execute()
    return result.data if result.data else []

# ========== БЕЙДЖИ ==========
async def get_user_badges(user_id: str):
    """Получить бейджи пользователя"""
    result = supabase.table("badges").select("*").eq("user_id", user_id).execute()
    return result.data if result.data else []


# ========== ПРИЗЫ ==========
async def get_all_active_prizes():
    """Получить все активные призы"""
    result = supabase.table("prizes_pool").select("*").eq("is_active", True).execute()
    return result.data if result.data else []


async def get_user_prizes(user_id: str):
    """Получить призы пользователя с информацией о призе"""
    result = supabase.table("user_prizes").select("*, prizes_pool(*)").eq("user_id", user_id).execute()
    return result.data if result.data else []


# ========== РЕЙТИНГИ ==========
async def get_rating_by_workouts():
    """Рейтинг по количеству тренировок"""
    result = supabase.table("rating_by_workouts").select("*").limit(50).execute()
    return result.data if result.data else []


async def get_rating_by_streak():
    """Рейтинг по серии"""
    result = supabase.table("rating_by_streak").select("*").limit(50).execute()
    return result.data if result.data else []
