from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

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


async def update_profile_streak(telegram_id: int, streak: int):
    """Обновить серию пользователя (триггер в БД сделает это автоматически, но оставим для ручного)"""
    supabase.table("profiles").update({"sunday_streak": streak}).eq("telegram_id", telegram_id).execute()


# ========== ТРЕНЕРЫ ==========
async def get_all_coaches():
    """Получить список всех тренеров"""
    result = supabase.table("coaches").select("*").order("full_name").execute()
    return result.data


async def get_coach(coach_id: str):
    """Получить тренера по ID"""
    result = supabase.table("coaches").select("*").eq("id", coach_id).execute()
    return result.data[0] if result.data else None


# ========== РАСПИСАНИЕ ==========
async def get_sunday_schedule(sunday_date: str):
    """Получить расписание на конкретное воскресенье"""
    result = supabase.table("sunday_schedule").select("*, coaches(*)").eq("sunday_date", sunday_date).execute()
    return result.data[0] if result.data else None


async def update_sunday_coach(sunday_date: str, coach_id: str):
    """Обновить тренера на воскресенье"""
    result = supabase.table("sunday_schedule").update({"coach_id": coach_id}).eq("sunday_date", sunday_date).execute()
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


async def get_upcoming_sundays_without_coach():
    """Получить будущие воскресенья без назначенного тренера"""
    from datetime import date
    today = date.today().isoformat()
    result = supabase.table("sunday_schedule").select("*").gte("sunday_date", today).is_("coach_id", "null").execute()
    return result.data


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
    return len(result.data) > 0


# ========== БЕЙДЖИ ==========
async def get_user_badges(user_id: str):
    """Получить бейджи пользователя"""
    result = supabase.table("badges").select("*").eq("user_id", user_id).execute()
    return result.data


# ========== ПРИЗЫ ==========
async def get_random_prize_for_user(user_id: str):
    """Получить случайный приз (без повторов)"""
    result = supabase.rpc("get_random_prize_for_user", {"p_user_id": user_id}).execute()
    return result.data[0] if result.data else None


async def award_prize(user_id: str, prize_id: str, awarded_for: str):
    """Выдать приз пользователю"""
    data = {
        "user_id": user_id,
        "prize_id": prize_id,
        "awarded_for": awarded_for
    }
    result = supabase.table("user_prizes").insert(data).execute()
    return result.data[0] if result.data else None


async def get_user_prizes(user_id: str):
    """Получить призы пользователя"""
    result = supabase.table("user_prizes").select("*, prizes_pool(*)").eq("user_id", user_id).execute()
    return result.data


# ========== РЕЙТИНГИ ==========
async def get_rating_by_km():
    """Рейтинг по километражу"""
    result = supabase.table("rating_by_km").select("*").limit(50).execute()
    return result.data


async def get_rating_by_workouts():
    """Рейтинг по количеству тренировок"""
    result = supabase.table("rating_by_workouts").select("*").limit(50).execute()
    return result.data


async def get_rating_by_streak():
    """Рейтинг по серии"""
    result = supabase.table("rating_by_streak").select("*").limit(50).execute()
    return result.data


# ========== СТАТИСТИКА ==========
async def get_user_full_stats(user_id: str):
    """Полная статистика пользователя для Web App"""
    result = supabase.table("user_full_stats").select("*").eq("id", user_id).execute()
    return result.data[0] if result.data else None
