import os
from dotenv import load_dotenv

load_dotenv()

# ========== TELEGRAM ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
MAIN_CHAT_ID = int(os.getenv("MAIN_CHAT_ID", "0"))
ADMIN_IDS = [int(id_) for id_ in os.getenv("ADMIN_IDS", "").split(",") if id_]

# ========== SUPABASE ==========
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ========== WEBHOOK ==========
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "")
WEBHOOK_PATH = "/webhook"

# ========== НАСТРОЙКИ ==========
SUNDAY_WEEKDAY = 6  # 0=Пн, 6=Вс

# ========== БЕЙДЖИ (для обратной совместимости) ==========
STREAK_BADGES = {
    4: "streak_4",
    8: "streak_8",
    12: "streak_12"
}
