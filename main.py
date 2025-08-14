import os
import logging
import asyncio
from flask import Flask, request, render_template, jsonify
from bot import bot, setup_webhook, application
import config
from telegram import Update

# Настройка логирования
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация Flask приложения
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "pokemon_bot_secret")

# Инициализация вебхука при запуске
try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_webhook())
except Exception as e:
    logger.error(f"Ошибка при настройке вебхука: {e}")

@app.route('/', methods=['GET'])
def index():
    """Индексная страница с информацией о боте."""
    return render_template('webhook.html', webhook_url=config.WEBHOOK_URL)

@app.route(f'/{config.BOT_TOKEN}', methods=['POST'])
def webhook():
    """Обработка входящих обновлений Telegram."""
    try:
        update_dict = request.get_json(force=True)
        logger.debug(f"Получено обновление: {update_dict}")
        
        # Преобразование в объект Telegram Update и обработка
        update = Update.de_json(update_dict, bot)
        
        # Использование asyncio для обработки обновления с помощью приложения
        async def process_update_async():
            await application.process_update(update)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_update_async())
        loop.close()
        
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"Ошибка при обработке обновления: {e}")
        return jsonify({"status": "error", "message": str(e)})

async def init_webhook():
    """Инициализация вебхука при запуске приложения"""
    await setup_webhook()
    
if __name__ == "__main__":
    # Настройка вебхука при запуске
    import asyncio
    asyncio.run(init_webhook())
    # Запуск веб-сервера
    app.run(host="0.0.0.0", port=5000, debug=True)
