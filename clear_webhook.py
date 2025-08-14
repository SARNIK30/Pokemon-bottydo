import asyncio
import os
from telegram.ext import ApplicationBuilder

async def clear_webhook():
    """Очистка вебхука для Telegram бота."""
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        print("ERROR: BOT_TOKEN не найден в переменных окружения.")
        return
    
    application = ApplicationBuilder().token(bot_token).build()
    await application.bot.delete_webhook()
    print("Webhook успешно удален.")

if __name__ == "__main__":
    asyncio.run(clear_webhook())
