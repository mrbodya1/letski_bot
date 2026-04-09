import os
import asyncio
import logging
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


# Импортируем хендлеры
import bot.handlers.start
import bot.handlers.workout
import bot.handlers.rating
import bot.handlers.admin


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
