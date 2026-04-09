import asyncio
import logging
from flask import Flask, request, abort
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from aiogram.utils import executor

from config import BOT_TOKEN, WEBHOOK_PATH, WEBHOOK_HOST
from bot.handlers import start, workout, rating, admin

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Flask приложение
app = Flask(__name__)


@app.route('/')
def index():
    """Главная страница"""
    return "🤖 Letski Bot is running!"


@app.route('/')
def index():
    return "🤖 Letski Bot is running!"


@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    if not WEBHOOK_HOST:
        return "❌ WEBHOOK_HOST не задан"
    
    webhook_url = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
    
    async def _set():
        await bot.delete_webhook()
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
    if request.headers.get('content-type') != 'application/json':
        abort(400)
    
    update_data = request.get_json()
    update = types.Update.to_object(update_data)
    
    async def process():
        await dp.process_update(update)
    
    asyncio.run(process())
    return 'OK'


@app.route('/webapp')
def webapp():
    """Мини-приложение (заглушка, потом отдадим HTML)"""
    return "Web App будет здесь"


# Для локального тестирования
if __name__ == '__main__':
    # Импортируем хендлеры здесь, чтобы они зарегистрировались
    import bot.handlers.start
    import bot.handlers.workout
    import bot.handlers.rating
    import bot.handlers.admin
    
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
