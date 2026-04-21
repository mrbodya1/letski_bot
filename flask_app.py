import os
import asyncio
import logging
import threading
import time
from datetime import datetime
from flask import Flask, request, abort, send_from_directory
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import BOT_TOKEN, WEBHOOK_PATH, WEBHOOK_HOST

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация хранилища и бота
storage = MemoryStorage()
telegram_bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
Bot.set_current(telegram_bot)
dp = Dispatcher(telegram_bot, storage=storage)
Dispatcher.set_current(dp)
dp.middleware.setup(LoggingMiddleware())

# Flask приложение
app = Flask(__name__)

# Абсолютный путь к папке webapp
WEBAPP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webapp')


# ========== ОСНОВНЫЕ МАРШРУТЫ ==========
@app.route('/')
def index():
    return "🤖 Letski Bot is running!"


@app.route('/webapp')
def serve_webapp():
    logger.info(f"Serving webapp from: {WEBAPP_DIR}")
    if not os.path.exists(os.path.join(WEBAPP_DIR, 'index.html')):
        return f"❌ index.html не найден в {WEBAPP_DIR}", 404
    return send_from_directory(WEBAPP_DIR, 'index.html')


@app.route('/webapp/<path:filename>')
def serve_webapp_static(filename):
    return send_from_directory(WEBAPP_DIR, filename)


@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    if not WEBHOOK_HOST:
        return "❌ WEBHOOK_HOST не задан"
    
    webhook_url = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
    
    async def _set():
        await telegram_bot.delete_webhook()
        await telegram_bot.set_webhook(webhook_url)
        logger.info(f"Webhook set to {webhook_url}")
    
    asyncio.run(_set())
    return f"✅ Webhook установлен на {webhook_url}"


@app.route(WEBHOOK_PATH, methods=['POST'])
def telegram_webhook():
    if request.headers.get('content-type') != 'application/json':
        abort(400)
    
    update_data = request.get_json()
    update = types.Update.to_object(update_data)
    
    async def process():
        await dp.process_update(update)
    
    asyncio.run(process())
    return 'OK'


# ========== API ДЛЯ WEB APP ==========
@app.route('/api/profile')
def api_profile():
    """API для получения профиля пользователя"""
    user_id = request.args.get('user_id')
    if not user_id:
        return {"error": "user_id required"}, 400
    
    async def get_data():
        try:
            from bot.utils.supabase import get_profile, get_user_badges, get_user_prizes, get_workouts_by_telegram_id
            
            profile = await get_profile(int(user_id))
            if not profile:
                return {"error": "Profile not found"}, 404
            
            badges = await get_user_badges(profile["id"])
            prizes = await get_user_prizes(profile["id"])
            workouts = await get_workouts_by_telegram_id(int(user_id))
            
            for w in workouts:
                if w.get('distance_km') and w.get('duration_min'):
                    w['pace'] = w['duration_min'] / w['distance_km']
                else:
                    w['pace'] = 0
            
            return {
                "id": profile["id"],
                "full_name": profile["full_name"],
                "gender": profile["gender"],
                "role": profile.get("role", "user"),
                "sunday_streak": profile.get("sunday_streak", 0) or 0,
                "max_sunday_streak": profile.get("max_sunday_streak", 0) or 0,
                "total_sundays": profile.get("total_sundays", 0) or 0,
                "total_km": profile.get("total_km", 0) or 0,
                "badges": badges or [],
                "prizes": prizes or [],
                "workouts": workouts or []
            }
        except Exception as e:
            logger.error(f"Error in api_profile: {e}")
            return {"error": str(e)}, 500
    
    result = asyncio.run(get_data())
    return result


@app.route('/api/badges_catalog')
def api_badges_catalog():
    """API для получения каталога всех бейджей"""
    async def get_data():
        from bot.utils.supabase import get_badges_catalog
        badges = await get_badges_catalog()
        return {"badges": badges or []}
    
    result = asyncio.run(get_data())
    return result


@app.route('/api/rating')
def api_rating():
    """API для получения рейтинга"""
    rating_type = request.args.get('type', 'km')
    
    async def get_data():
        from bot.utils.supabase import get_rating_by_km, get_rating_by_workouts, get_rating_by_streak
        
        if rating_type == 'km':
            return await get_rating_by_km()
        elif rating_type == 'workouts':
            return await get_rating_by_workouts()
        elif rating_type == 'streak':
            return await get_rating_by_streak()
        else:
            return []
    
    result = asyncio.run(get_data())
    return {"rating": result or []}


@app.route('/api/prizes')
def api_prizes():
    """API для получения призов"""
    user_id = request.args.get('user_id')
    
    async def get_data():
        from bot.utils.supabase import get_all_active_prizes, get_user_prizes, get_profile
        
        all_prizes = await get_all_active_prizes()
        
        if user_id:
            profile = await get_profile(int(user_id))
            if profile:
                my_prizes = await get_user_prizes(profile["id"])
                my_prize_ids = [p["prize_id"] for p in my_prizes] if my_prizes else []
                
                available = [p for p in all_prizes if p["id"] not in my_prize_ids] if all_prizes else []
                return {"available": available, "my": my_prizes or []}
        
        return {"available": all_prizes or [], "my": []}
    
    result = asyncio.run(get_data())
    return result


# ========== API ДЛЯ ОТКРЫТИЯ ПРИЗА ==========
@app.route('/api/reveal_prize', methods=['POST'])
def api_reveal_prize():
    """Открыть приз (показать анимацию и получить реальный приз)"""
    data = request.get_json()
    user_prize_id = data.get('user_prize_id')
    
    if not user_prize_id:
        return {"error": "user_prize_id required"}, 400
    
    async def reveal():
        from bot.utils.supabase import supabase
        
        prize_data = supabase.table("user_prizes")\
            .select("*, prizes_pool(*)")\
            .eq("id", user_prize_id)\
            .execute()
        
        if not prize_data.data:
            return {"error": "Prize not found"}, 404
        
        prize = prize_data.data[0]
        
        if prize.get('is_revealed'):
            return {
                "success": True,
                "prize": prize['prizes_pool'],
                "promo_code": prize.get('promo_code')
            }
        
        supabase.table("user_prizes")\
            .update({"is_revealed": True})\
            .eq("id", user_prize_id)\
            .execute()
        
        return {
            "success": True,
            "prize": prize['prizes_pool'],
            "promo_code": prize.get('promo_code')
        }
    
    result = asyncio.run(reveal())
    return result


# ========== АДМИН-API ==========
def _is_admin_request(req):
    """Проверка, что запрос от админа"""
    user_id = req.args.get('user_id')
    if not user_id:
        return False
    
    async def check():
        from bot.utils.supabase import get_profile
        profile = await get_profile(int(user_id))
        return profile and profile.get('role') == 'admin'
    
    return asyncio.run(check())


@app.route('/api/admin/coaches')
def api_admin_coaches():
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    async def get_data():
        from bot.utils.supabase import get_all_coaches_admin
        return await get_all_coaches_admin()
    
    return asyncio.run(get_data())


@app.route('/api/admin/coaches', methods=['POST'])
def api_admin_create_coach():
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    data = request.get_json()
    full_name = data.get('full_name')
    telegram_id = data.get('telegram_id')
    
    if not full_name:
        return {"error": "full_name required"}, 400
    
    async def create():
        from bot.utils.supabase import create_coach
        return await create_coach(full_name, telegram_id)
    
    result = asyncio.run(create())
    return result if result else {"error": "Failed to create"}, 500


@app.route('/api/admin/coaches/<coach_id>', methods=['PATCH'])
def api_admin_update_coach(coach_id):
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    data = request.get_json()
    
    async def update():
        from bot.utils.supabase import update_coach
        return await update_coach(coach_id, data)
    
    result = asyncio.run(update())
    return result if result else {"error": "Failed to update"}, 500


@app.route('/api/admin/coaches/<coach_id>', methods=['DELETE'])
def api_admin_delete_coach(coach_id):
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    async def delete():
        from bot.utils.supabase import delete_coach
        return await delete_coach(coach_id)
    
    result = asyncio.run(delete())
    return {"success": True} if result else {"error": "Failed to delete"}, 500


@app.route('/api/admin/prizes')
def api_admin_prizes():
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    async def get_data():
        from bot.utils.supabase import get_all_prizes_admin
        return await get_all_prizes_admin()
    
    return asyncio.run(get_data())


@app.route('/api/admin/prizes', methods=['POST'])
def api_admin_create_prize():
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    data = request.get_json()
    
    async def create():
        from bot.utils.supabase import create_prize_full
        return await create_prize_full(data)
    
    result = asyncio.run(create())
    return result if result else {"error": "Failed to create"}, 500


@app.route('/api/admin/prizes/<prize_id>', methods=['PATCH'])
def api_admin_update_prize(prize_id):
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    data = request.get_json()
    
    async def update():
        from bot.utils.supabase import update_prize
        return await update_prize(prize_id, data)
    
    result = asyncio.run(update())
    return result if result else {"error": "Failed to update"}, 500


@app.route('/api/admin/prizes/<prize_id>', methods=['DELETE'])
def api_admin_delete_prize(prize_id):
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    async def delete():
        from bot.utils.supabase import delete_prize
        return await delete_prize(prize_id)
    
    result = asyncio.run(delete())
    return {"success": True} if result else {"error": "Failed to delete"}, 500


@app.route('/api/admin/badges')
def api_admin_badges():
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    async def get_data():
        from bot.utils.supabase import get_badges_catalog_full
        return await get_badges_catalog_full()
    
    return asyncio.run(get_data())


@app.route('/api/admin/badges', methods=['POST'])
def api_admin_create_badge():
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    data = request.get_json()
    
    async def create():
        from bot.utils.supabase import create_badge
        return await create_badge(data)
    
    result = asyncio.run(create())
    return result if result else {"error": "Failed to create"}, 500


@app.route('/api/admin/badges/<badge_id>', methods=['PATCH'])
def api_admin_update_badge(badge_id):
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    data = request.get_json()
    
    async def update():
        from bot.utils.supabase import update_badge
        return await update_badge(badge_id, data)
    
    result = asyncio.run(update())
    return result if result else {"error": "Failed to update"}, 500


@app.route('/api/admin/schedule')
def api_admin_schedule():
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    async def get_data():
        from bot.utils.supabase import get_schedule_admin
        return await get_schedule_admin()
    
    return asyncio.run(get_data())


@app.route('/api/admin/schedule', methods=['POST'])
def api_admin_create_schedule():
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    data = request.get_json()
    
    async def create():
        from bot.utils.supabase import upsert_schedule
        return await upsert_schedule(data)
    
    result = asyncio.run(create())
    return result if result else {"error": "Failed to create"}, 500


@app.route('/api/admin/schedule/<schedule_id>', methods=['DELETE'])
def api_admin_delete_schedule(schedule_id):
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    async def delete():
        from bot.utils.supabase import delete_schedule
        return await delete_schedule(schedule_id)
    
    result = asyncio.run(delete())
    return {"success": True} if result else {"error": "Failed to delete"}, 500


@app.route('/api/admin/users')
def api_admin_users():
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    async def get_data():
        from bot.utils.supabase import get_all_users_admin
        return await get_all_users_admin()
    
    return asyncio.run(get_data())


@app.route('/api/admin/users/<user_id>', methods=['PATCH'])
def api_admin_update_user(user_id):
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    data = request.get_json()
    
    async def update():
        from bot.utils.supabase import update_user_admin
        return await update_user_admin(user_id, data)
    
    result = asyncio.run(update())
    return result if result else {"error": "Failed to update"}, 500


@app.route('/api/admin/workouts')
def api_admin_workouts():
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    limit = request.args.get('limit', 50)
    
    async def get_data():
        from bot.utils.supabase import get_all_workouts_admin
        return await get_all_workouts_admin(int(limit))
    
    return asyncio.run(get_data())


@app.route('/api/admin/workouts/<workout_id>', methods=['DELETE'])
def api_admin_delete_workout(workout_id):
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    async def delete():
        from bot.utils.supabase import delete_workout_admin
        return await delete_workout_admin(workout_id)
    
    result = asyncio.run(delete())
    return {"success": True} if result else {"error": "Failed to delete"}, 500


@app.route('/api/admin/ratings')
def api_admin_ratings():
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    limit = request.args.get('limit', 50)
    
    async def get_data():
        from bot.utils.supabase import get_all_ratings_admin
        return await get_all_ratings_admin(int(limit))
    
    return asyncio.run(get_data())


@app.route('/api/admin/ratings/<rating_id>', methods=['DELETE'])
def api_admin_delete_rating(rating_id):
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    async def delete():
        from bot.utils.supabase import delete_rating_admin
        return await delete_rating_admin(rating_id)
    
    result = asyncio.run(delete())
    return {"success": True} if result else {"error": "Failed to delete"}, 500

@app.route('/api/admin/issued_prizes')
def api_admin_issued_prizes():
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    async def get_data():
        from bot.utils.supabase import get_all_issued_prizes_admin
        return await get_all_issued_prizes_admin()
    
    return asyncio.run(get_data())

@app.route('/api/admin/issued_prizes/<user_prize_id>/claim', methods=['PATCH'])
def api_admin_claim_prize(user_prize_id):
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    async def claim():
        from bot.utils.supabase import mark_prize_as_claimed
        return await mark_prize_as_claimed(user_prize_id)
    
    result = asyncio.run(claim())
    return {"success": True} if result else {"error": "Failed to update"}, 500

@app.route('/api/admin/stats')
def api_admin_stats():
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    async def get_data():
        from bot.utils.supabase import get_admin_stats
        return await get_admin_stats()
    
    return asyncio.run(get_data())

@app.route('/api/admin/schedule/<schedule_id>', methods=['PATCH'])
def api_admin_update_schedule(schedule_id):
    if not _is_admin_request(request):
        return {"error": "Unauthorized"}, 403
    
    data = request.get_json()
    
    async def update():
        from bot.utils.supabase import update_schedule_admin
        return await update_schedule_admin(schedule_id, data)
    
    result = asyncio.run(update())
    return result if result else {"error": "Failed to update"}, 500


# ========== ПЛАНИРОВЩИК ЕЖЕНЕДЕЛЬНОГО ОТЧЁТА ==========
def run_scheduler():
    """Фоновая задача для отправки еженедельного отчёта"""
    print("🕒 Планировщик запущен")
    last_report_date = None
    
    while True:
        now = datetime.now()
        today_str = now.date().isoformat()
        
        if now.weekday() == 0 and now.hour == 10 and now.minute == 0:
            if last_report_date != today_str:
                print(f"📤 Отправляю еженедельный отчёт за {today_str}...")
                try:
                    from bot.utils.supabase import send_weekly_report
                    asyncio.run(send_weekly_report())
                    last_report_date = today_str
                except Exception as e:
                    print(f"❌ Ошибка в планировщике: {e}")
            time.sleep(60)
        else:
            time.sleep(30)


scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()


# ========== ИМПОРТ ХЕНДЛЕРОВ ==========
import bot.handlers.start
import bot.handlers.workout
import bot.handlers.rating
import bot.handlers.admin


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
