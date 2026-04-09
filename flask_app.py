import asyncio
import logging
from flask import Flask, request, abort
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, WEBHOOK_PATH, WEBHOOK_HOST
from bot.handlers import start, workout, rating, admin

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Подключаем роутеры
dp.include_router(start.router)
dp.include_router(workout.router)
dp.include_router(rating.router)
dp.include_router(admin.router)

# Flask приложение
app = Flask(__name__)


@app.route('/')
def index():
    """Главная страница"""
    return "🤖 Letski Bot is running!"


@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Установка вебхука (вызови один раз после деплоя)"""
    if not WEBHOOK_HOST:
        return "❌ WEBHOOK_HOST не задан в .env"
    
    webhook_url = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
    
    async def _set():
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(webhook_url)
        logger.info(f"Webhook set to {webhook_url}")
    
    asyncio.run(_set())
    return f"✅ Webhook установлен на {webhook_url}"


@app.route('/delete_webhook', methods=['GET'])
def delete_webhook():
    """Удаление вебхука"""
    async def _delete():
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted")
    
    asyncio.run(_delete())
    return "✅ Webhook удален"


@app.route(WEBHOOK_PATH, methods=['POST'])
def telegram_webhook():
    """Прием обновлений от Telegram"""
    if request.headers.get('content-type') != 'application/json':
        abort(400)
    
    update_data = request.get_json()
    
    async def process():
        update = Update.model_validate(update_data)
        await dp.feed_update(bot, update)
    
    asyncio.run(process())
    return 'OK'


@app.route('/webapp')
def webapp():
    """Мини-приложение (заглушка, потом отдадим HTML)"""
    return "Web App будет здесь"


# Для локального тестирования
if __name__ == '__main__':
    app.run(debug=True, port=5000)
