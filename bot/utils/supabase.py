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

# ========== КАТАЛОГ БЕЙДЖЕЙ ==========
async def get_badges_catalog():
    """Получить все бейджи из каталога"""
    result = supabase.table("badges_catalog").select("*").order("created_at").execute()
    return result.data if result.data else []


async def get_active_badges_catalog():
    """Получить активные бейджи"""
    result = supabase.table("badges_catalog").select("*").eq("is_active", true).execute()
    return result.data if result.data else []


# ========== УПРАВЛЕНИЕ ПРИЗАМИ ==========
async def get_all_prizes_admin():
    """Получить все призы для админки"""
    result = supabase.table("prizes_pool").select("*").order("created_at", desc=True).execute()
    return result.data if result.data else []


async def create_prize(name: str, partner: str, prize_type: str, value: str, category: str, promo_code: str):
    """Создать новый приз"""
    data = {
        "name": name,
        "partner": partner,
        "type": prize_type,
        "value": value,
        "category": category,
        "promo_code": promo_code
    }
    result = supabase.table("prizes_pool").insert(data).execute()
    return result.data[0] if result.data else None


async def toggle_prize_active(prize_id: str):
    """Переключить активность приза"""
    # Получаем текущий статус
    current = supabase.table("prizes_pool").select("is_active, name").eq("id", prize_id).execute()
    if not current.data:
        return None
    
    new_status = not current.data[0]["is_active"]
    result = supabase.table("prizes_pool").update({"is_active": new_status}).eq("id", prize_id).execute()
    
    if result.data:
        return {"name": current.data[0]["name"], "is_active": new_status}
    return None


async def update_prize_quantity(prize_id: str, total: int):
    """Обновить количество призов"""
    result = supabase.table("prizes_pool").update({
        "total_quantity": total,
        "remaining_quantity": total
    }).eq("id", prize_id).execute()
    return result.data[0] if result.data else None


async def decrement_prize_quantity(prize_id: str):
    """Уменьшить оставшееся количество приза на 1"""
    current = supabase.table("prizes_pool").select("remaining_quantity").eq("id", prize_id).execute()
    if current.data and current.data[0]["remaining_quantity"] > 0:
        new_qty = current.data[0]["remaining_quantity"] - 1
        supabase.table("prizes_pool").update({"remaining_quantity": new_qty}).eq("id", prize_id).execute()
        return new_qty
    return 0


async def get_rating_by_streak():
    """Рейтинг по серии"""
    result = supabase.table("rating_by_streak").select("*").limit(50).execute()
    return result.data if result.data else []

async def create_prize_with_link(name: str, partner: str, prize_type: str, value: str, category: str, promo_code: str, link_url: str = None):
    """Создать новый приз со ссылкой"""
    data = {
        "name": name,
        "partner": partner,
        "type": prize_type,
        "value": value,
        "category": category,
        "promo_code": promo_code
    }
    if link_url:
        data["link_url"] = link_url
    
    result = supabase.table("prizes_pool").insert(data).execute()
    return result.data[0] if result.data else None
    
async def get_workouts_by_telegram_id(telegram_id: int):
    """Получить все тренировки пользователя по telegram_id"""
    # Сначала получаем profile_id
    profile = await get_profile(telegram_id)
    if not profile:
        return []
    
    result = supabase.table("workouts")\
        .select("*")\
        .eq("user_id", profile["id"])\
        .order("sunday_date", desc=True)\
        .execute()
    
    return result.data if result.data else []

# ========== УНИВЕРСАЛЬНАЯ ПРОВЕРКА БЕЙДЖЕЙ ==========
async def check_and_award_badges(user_id: str, stats: dict):
    print(f"🔍 Проверяем бейджи для user={user_id}, stats={stats}")
    
    catalog = supabase.table("badges_catalog").select("*").eq("is_active", True).execute()
    print(f"📦 Найдено бейджей в каталоге: {len(catalog.data) if catalog.data else 0}")
    
    earned = supabase.table("badges").select("badge_type").eq("user_id", user_id).execute()
    earned_types = {b['badge_type'] for b in earned.data} if earned.data else set()
    print(f"✅ Уже есть бейджи: {earned_types}")
    
    awarded = []
    
    for badge in catalog.data:
        if badge['badge_type'] in earned_types:
            continue
        
        should_award = False
        
        if badge['trigger_type'] == 'first_workout' and stats.get('total_workouts', 0) >= 1:
            should_award = True
        elif badge['trigger_type'] == 'streak' and stats.get('streak', 0) >= badge['trigger_value']:
            should_award = True
        elif badge['trigger_type'] == 'total_km' and stats.get('total_km', 0) >= badge['trigger_value']:
            should_award = True
        elif badge['trigger_type'] == 'total_workouts' and stats.get('total_workouts', 0) >= badge['trigger_value']:
            should_award = True
        
        if should_award:
            print(f"🎁 Выдаём бейдж: {badge['name']}")
            supabase.table("badges").insert({
                "user_id": user_id,
                "badge_type": badge['badge_type'],
                "awarded_at": "now()"
            }).execute()
            awarded.append(badge)
    
    print(f"🏅 Всего выдано бейджей: {len(awarded)}")
    return awarded


# ========== УНИВЕРСАЛЬНАЯ ВЫДАЧА ПРИЗОВ ==========
async def check_and_award_prize(user_id: str, total_workouts: int):
    """
    Выдаёт приз в зависимости от количества тренировок.
    Уровни: 4-9 (common), 10-16 (rare), 17-23 (epic), 24-29 (legendary)
    Возвращает (prize, level_name) или (None, None)
    """
    # Определяем уровень
    if 4 <= total_workouts <= 9:
        level = 'common'
        level_name = 'Базовый'
    elif 10 <= total_workouts <= 16:
        level = 'rare'
        level_name = 'Редкий'
    elif 17 <= total_workouts <= 23:
        level = 'epic'
        level_name = 'Эпический'
    elif 24 <= total_workouts <= 29:
        level = 'legendary'
        level_name = 'Легендарный'
    else:
        return None, None
    
    # Проверяем, не выдан ли уже приз этого уровня
    existing = supabase.table("user_prizes").select("*").eq("user_id", user_id).eq("awarded_for", f"level_{level}").execute()
    if existing.data:
        return None, None
    
    # Ищем приз нужного уровня
    prizes = supabase.table("prizes_pool").select("*").eq("is_active", True).eq("level", level).execute()
    
    if not prizes.data:
        # Если нет призов нужного уровня, берём любые активные
        prizes = supabase.table("prizes_pool").select("*").eq("is_active", True).execute()
    
    if not prizes.data:
        return None, None
    
    import random
    prize = random.choice(prizes.data)
    
    # Выдаём приз
    supabase.table("user_prizes").insert({
        "user_id": user_id,
        "prize_id": prize['id'],
        "awarded_for": f"level_{level}",
        "awarded_at": "now()",
        "is_claimed": False
    }).execute()
    
    return prize, level_name

# ========== АДМИН-ФУНКЦИИ ==========

async def get_all_coaches_admin():
    """Получить всех тренеров с полной информацией"""
    result = supabase.table("coaches").select("*").order("full_name").execute()
    return result.data if result.data else []


async def create_coach(full_name: str, telegram_id: int = None):
    """Создать нового тренера"""
    data = {"full_name": full_name}
    if telegram_id:
        data["telegram_id"] = telegram_id
    
    result = supabase.table("coaches").insert(data).execute()
    return result.data[0] if result.data else None


async def update_coach(coach_id: str, data: dict):
    """Обновить тренера"""
    allowed = ["full_name", "telegram_id"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    
    if not update_data:
        return None
    
    result = supabase.table("coaches").update(update_data).eq("id", coach_id).execute()
    return result.data[0] if result.data else None


async def delete_coach(coach_id: str):
    """Удалить тренера"""
    result = supabase.table("coaches").delete().eq("id", coach_id).execute()
    return True if result.data else False


async def get_all_prizes_admin():
    """Получить все призы (активные и неактивные)"""
    result = supabase.table("prizes_pool").select("*").order("created_at", desc=True).execute()
    return result.data if result.data else []


async def create_prize_full(data: dict):
    """Создать приз со всеми полями"""
    allowed = [
        "name", "description", "partner", "type", "value", "level", 
        "promo_code", "link_url", "is_active", "total_quantity", 
        "remaining_quantity", "category"
    ]
    insert_data = {k: v for k, v in data.items() if k in allowed and v is not None}
    
    if not insert_data.get("name"):
        return None
    
    # Генерируем промокод если не указан
    if not insert_data.get("promo_code"):
        import random
        import string
        insert_data["promo_code"] = f"LETSKI-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
    
    # Если количество не указано, ставим -1 (безлимитно)
    if "total_quantity" not in insert_data:
        insert_data["total_quantity"] = -1
        insert_data["remaining_quantity"] = -1
    elif insert_data.get("total_quantity") and "remaining_quantity" not in insert_data:
        insert_data["remaining_quantity"] = insert_data["total_quantity"]
    
    result = supabase.table("prizes_pool").insert(insert_data).execute()
    return result.data[0] if result.data else None


async def update_prize(prize_id: str, data: dict):
    """Обновить приз"""
    allowed = ["name", "description", "partner", "type", "value", "level", 
               "promo_code", "link_url", "is_active", "total_quantity", "remaining_quantity"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    
    if not update_data:
        return None
    
    result = supabase.table("prizes_pool").update(update_data).eq("id", prize_id).execute()
    return result.data[0] if result.data else None


async def delete_prize(prize_id: str):
    """Удалить приз (только если не выдан)"""
    # Проверяем, не выдан ли приз
    issued = supabase.table("user_prizes").select("id").eq("prize_id", prize_id).execute()
    if issued.data:
        return False  # Нельзя удалить выданный приз
    
    result = supabase.table("prizes_pool").delete().eq("id", prize_id).execute()
    return True if result.data else False


async def get_badges_catalog_full():
    """Получить полный каталог бейджей (включая неактивные)"""
    result = supabase.table("badges_catalog").select("*").order("created_at").execute()
    return result.data if result.data else []


async def update_badge(badge_id: str, data: dict):
    """Обновить бейдж"""
    allowed = ["name", "emoji", "description", "compliment", "trigger_type", 
               "trigger_value", "is_active"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    
    if not update_data:
        return None
    
    result = supabase.table("badges_catalog").update(update_data).eq("id", badge_id).execute()
    return result.data[0] if result.data else None


async def get_schedule_admin():
    """Получить расписание с информацией о тренерах"""
    result = supabase.table("sunday_schedule").select("*, coaches(full_name)").order("sunday_date", desc=True).limit(30).execute()
    return result.data if result.data else []


async def upsert_schedule(data: dict):
    """Создать или обновить расписание"""
    sunday_date = data.get("sunday_date")
    if not sunday_date:
        return None
    
    # Проверяем существование
    existing = supabase.table("sunday_schedule").select("id").eq("sunday_date", sunday_date).execute()
    
    insert_data = {
        "sunday_date": sunday_date,
        "coach_id": data.get("coach_id"),
        "format": data.get("format"),
        "location": data.get("location"),
        "start_time": data.get("start_time"),
        "description": data.get("description"),
        "status": data.get("status", "scheduled")
    }
    
    if existing.data:
        result = supabase.table("sunday_schedule").update(insert_data).eq("sunday_date", sunday_date).execute()
    else:
        result = supabase.table("sunday_schedule").insert(insert_data).execute()
    
    return result.data[0] if result.data else None


async def delete_schedule(schedule_id: str):
    """Удалить расписание"""
    result = supabase.table("sunday_schedule").delete().eq("id", schedule_id).execute()
    return True if result.data else False


async def get_all_users_admin():
    """Получить всех участников"""
    result = supabase.table("profiles").select("*").order("registered_at", desc=True).execute()
    return result.data if result.data else []


async def update_user_admin(user_id: str, data: dict):
    """Обновить участника (только админские поля)"""
    allowed = ["full_name", "role", "sunday_streak", "total_km", "total_sundays"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    
    if not update_data:
        return None
    
    result = supabase.table("profiles").update(update_data).eq("id", user_id).execute()
    return result.data[0] if result.data else None


async def get_all_workouts_admin(limit: int = 50):
    """Получить все тренировки"""
    result = supabase.table("workouts").select("*, profiles(full_name), coaches(full_name)").order("created_at", desc=True).limit(limit).execute()
    return result.data if result.data else []


async def delete_workout_admin(workout_id: str):
    """Удалить тренировку"""
    # Сначала получаем данные для обновления статистики
    workout = supabase.table("workouts").select("user_id, distance_km").eq("id", workout_id).execute()
    
    if workout.data:
        w = workout.data[0]
        # Уменьшаем статистику
        supabase.table("profiles").update({
            "total_sundays": supabase.raw("total_sundays - 1"),
            "total_km": supabase.raw(f"total_km - {w['distance_km']}")
        }).eq("id", w["user_id"]).execute()
    
    result = supabase.table("workouts").delete().eq("id", workout_id).execute()
    return True if result.data else False


async def get_all_ratings_admin(limit: int = 50):
    """Получить все оценки"""
    result = supabase.table("coach_ratings").select("*, profiles(full_name), coaches(full_name)").order("created_at", desc=True).limit(limit).execute()
    return result.data if result.data else []


async def delete_rating_admin(rating_id: str):
    """Удалить оценку"""
    result = supabase.table("coach_ratings").delete().eq("id", rating_id).execute()
    return True if result.data else False


async def get_admin_stats():
    """Получить статистику для админ-дашборда"""
    try:
        # Общее количество участников (всех)
        users = supabase.table("profiles").select("id", count="exact").execute()
        total_users = users.count if hasattr(users, 'count') else len(users.data) if users.data else 0
        
        # Тренировки
        workouts = supabase.table("workouts").select("id", count="exact").execute()
        total_workouts = workouts.count if hasattr(workouts, 'count') else len(workouts.data) if workouts.data else 0
        
        # Сумма км
        km_result = supabase.table("profiles").select("total_km").execute()
        total_km = sum(p.get("total_km", 0) for p in km_result.data) if km_result.data else 0
        
        # Топ тренеров
        top_coaches = supabase.table("coaches").select("full_name, avg_rating_pro, total_ratings").order("avg_rating_pro", desc=True).limit(3).execute()
        
        return {
            "total_users": total_users,
            "total_workouts": total_workouts,
            "total_km": round(total_km, 1),
            "top_coaches": top_coaches.data if top_coaches.data else []
        }
    except Exception as e:
        print(f"Error in get_admin_stats: {e}")
        return {"total_users": 0, "total_workouts": 0, "total_km": 0, "top_coaches": []}
