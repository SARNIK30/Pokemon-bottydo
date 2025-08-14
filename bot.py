import logging
import os
import asyncio
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from telegram import Bot, Update
import config
from handlers import (
    start, admin, battle, pokedex, shop, 
    evolution, info, trading, test, games, account
)
from storage import initialize_data

# Настройка логирования
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=config.BOT_TOKEN)

# Инициализация приложения и передача токена вашего бота
application = Application.builder().token(config.BOT_TOKEN).build()

# Загрузка начальных данных
initialize_data()

def register_handlers():
    """Регистрация всех обработчиков команд и сообщений."""
    # Обработчики команд
    application.add_handler(CommandHandler("start", start.start_command))
    application.add_handler(CommandHandler("info", info.info_command))
    application.add_handler(CommandHandler("pokedex", pokedex.pokedex_command))
    application.add_handler(CommandHandler("battle", battle.battle_command))
    application.add_handler(CommandHandler("admin", admin.admin_command))
    application.add_handler(CommandHandler("shop", shop.shop_command))
    application.add_handler(CommandHandler("promocode", shop.promocode_command))
    application.add_handler(CommandHandler("evolution", evolution.evolution_command))
    application.add_handler(CommandHandler("trade", trading.trade_command))
    application.add_handler(CommandHandler("test", test.test_command))
    application.add_handler(CommandHandler("games", games.games_command))
    application.add_handler(CommandHandler("catch", start.catch_command))
    application.add_handler(CommandHandler("delete_account", account.delete_account_command))
    
    # Обработчики обратных вызовов
    application.add_handler(CallbackQueryHandler(start.choose_starter_callback, pattern=r'^starter_'))
    application.add_handler(CallbackQueryHandler(pokedex.pokedex_navigation_callback, pattern=r'^pokedex_'))
    application.add_handler(CallbackQueryHandler(shop.shop_callback, pattern=r'^shop_'))
    application.add_handler(CallbackQueryHandler(admin.admin_callback, pattern=r'^admin_'))
    application.add_handler(CallbackQueryHandler(battle.battle_callback, pattern=r'^battle_'))
    application.add_handler(CallbackQueryHandler(trading.trade_callback, pattern=r'^trade_'))
    application.add_handler(CallbackQueryHandler(test.test_callback, pattern=r'^test_'))
    application.add_handler(CallbackQueryHandler(games.games_callback, pattern=r'^game'))
    application.add_handler(CallbackQueryHandler(games.games_callback, pattern=r'^guess_'))
    application.add_handler(CallbackQueryHandler(games.games_callback, pattern=r'^quiz_'))
    application.add_handler(CallbackQueryHandler(account.delete_account_callback, pattern=r'^delete_account_'))
    
    # Обработчик команд призыва покемонов (работает во всех чатах)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & 
        (filters.Regex(r'^[Пп]ризвать покемона?$') | 
         filters.Regex(r'^[Пп]ризвать$') | 
         filters.Regex(r'^[Пп]окемон призыв$') | 
         filters.Regex(r'^[Вв]ызвать покемона?$') | 
         filters.Regex(r'^[Зз]ови покемона?$')), 
        start.call_pokemon
    ))
    
    # Обработчик для ловли покемонов в личных чатах
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        start.handle_catch_attempt
    ))
    
    # Обработчик команд для ловли покемонов в ЛЮБЫХ групповых чатах
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & 
        (filters.ChatType.GROUPS | filters.ChatType.GROUP | filters.ChatType.SUPERGROUP) &  # Совместимо с разными версиями API
        (filters.Regex(r'^[Лл]овлю$') | 
         filters.Regex(r'^[Пп]оймать$') | 
         filters.Regex(r'^[Cc]atch$') | 
         filters.Regex(r'^[Лл]овить$') | 
         filters.Regex(r'^[Сс]хватить$')),
        start.handle_catch_attempt
    ))
    
    # Обработчик остальных сообщений в ЛЮБЫХ групповых чатах
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & 
        (filters.ChatType.GROUPS | filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),  # Совместимо с разными версиями API
        start.handle_group_message
    ))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    logger.info("Все обработчики зарегистрированы")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирование ошибки и отправка сообщения пользователю."""
    logger.error(f"Исключение при обработке обновления: {context.error}")
    
    if update and isinstance(update, Update) and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
        )

async def setup_webhook():
    """Настройка вебхука для Telegram бота."""
    try:
        webhook_url = f"{config.WEBHOOK_URL}/{config.BOT_TOKEN}"
        await bot.set_webhook(webhook_url)
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Вебхук настроен по адресу {webhook_url}")
        logger.info(f"Информация о вебхуке: {webhook_info}")
    except Exception as e:
        logger.error(f"Не удалось настроить вебхук: {e}")
        
async def run_polling():
    """Запуск бота с использованием поллинга (для разработки)."""
    try:
        logger.info("Запуск бота с поллингом...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        logger.info("Поллинг бота успешно запущен")
        
        # Поддержка поллинга до прерывания
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Не удалось запустить поллинг: {e}")
    finally:
        # Правильное закрытие приложения при остановке
        logger.info("Остановка бота...")
        await application.stop()
        await application.shutdown()

# Регистрация всех обработчиков
register_handlers()
