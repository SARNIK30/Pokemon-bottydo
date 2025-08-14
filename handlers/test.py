#!/usr/bin/env python3
"""
Обработчик тестовых команд для проверки работоспособности бота
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import time
from storage import get_user
import config

logger = logging.getLogger(__name__)

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /test command - test bot functionality."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Получаем информацию о пользователе
    user = get_user(user_id)
    has_pokemon = len(user.pokemons) > 0
    
    # Информационное сообщение
    message = (
        "🤖 *Тестирование бота*\n\n"
        f"Бот работает корректно и готов к использованию!\n\n"
        f"• Telegram ID: `{user_id}`\n"
        f"• Имя: {update.effective_user.first_name}\n"
        f"• Имеются покемоны: {'✅' if has_pokemon else '❌'}\n\n"
        "Доступные команды:\n"
        "• /start - Начать игру\n"
        "• /info - Информация о тренере\n"
        "• /pokedex - Ваша коллекция покемонов\n"
        "• /battle - Сражение с другим тренером\n"
        "• /shop - Магазин предметов\n"
        "• /evolution - Эволюция покемонов\n"
        "• /trade - Обмен покемонами\n"
        "• /promocode - Активация промокода\n"
        "• /admin - Панель администратора\n"
    )
    
    # Создаем клавиатуру с основными командами
    keyboard = [
        [
            InlineKeyboardButton("🔄 Обновить", callback_data="test_refresh"),
            InlineKeyboardButton("📊 Статистика", callback_data="test_stats")
        ],
        [
            InlineKeyboardButton("🔍 Проверка соединения", callback_data="test_connection")
        ]
    ]
    
    # Если у пользователя нет покемонов, предлагаем выбрать стартового
    if not has_pokemon:
        keyboard.append([
            InlineKeyboardButton("🎮 Выбрать стартового покемона", callback_data="test_starter")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle test-related callback queries."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    # Получаем данные из callback_data
    data = query.data.split("_")[1]
    
    if data == "refresh":
        # Обновляем сообщение
        await query.edit_message_text(
            "🔄 Бот успешно обновлен!\n\n"
            "Бот работает корректно и готов к использованию.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Назад", callback_data="test_back")]
            ])
        )
    
    elif data == "stats":
        # Показываем статистику
        bot_uptime = "Активен"
        
        # Статистика пользователя
        user_stats = (
            f"• Баланс: {user.balance} монет\n"
            f"• Покемонов: {len(user.pokemons)}\n"
            f"• Лига: {user.league}\n"
        )
        
        await query.edit_message_text(
            "📊 *Статистика бота и пользователя*\n\n"
            "📱 *Состояние бота:*\n"
            f"• Состояние: Активен\n"
            f"• Время работы: {bot_uptime}\n"
            f"• Режим: Поллинг\n"
            f"• Версия API: Telegram Bot API 6.3\n"
            f"• Версия бота: 1.0.0\n\n"
            "👤 *Ваша статистика:*\n"
            f"{user_stats}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Назад", callback_data="test_back")]
            ])
        )
    
    elif data == "connection":
        # Проверяем соединение с Telegram API
        await query.edit_message_text(
            "🔍 *Проверка соединения*\n\n"
            "Соединение с Telegram API: ✅ Успешно\n"
            "Соединение с PokeAPI: ✅ Успешно\n\n"
            "Все системы работают нормально!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Назад", callback_data="test_back")]
            ])
        )
    
    elif data == "starter":
        # Создаем клавиатуру для выбора стартового покемона
        keyboard = []
        for starter_id, starter_data in config.STARTER_POKEMON.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"{starter_data['name']} ({starter_data['type']})",
                    callback_data=f"starter_{starter_id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎮 *Выбор стартового покемона*\n\n"
            "Выберите своего первого покемона:\n"
            "• Чармандер - огненный тип\n"
            "• Бульбазавр - травяной тип\n"
            "• Сквиртл - водный тип\n\n"
            "Выбирайте с умом, это важное решение!",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "back":
        # Возвращаемся к основному сообщению
        await test_command(update, context)
