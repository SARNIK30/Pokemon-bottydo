#!/usr/bin/env python3
"""
Обработчик команд, связанных с аккаунтом пользователя
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from storage import get_user, delete_user

logger = logging.getLogger(__name__)

async def delete_account_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /delete_account - удаление аккаунта пользователя."""
    user_id = update.effective_user.id
    
    # Создаем клавиатуру для подтверждения
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить аккаунт", callback_data="delete_account_confirm"),
            InlineKeyboardButton("❌ Нет, отмена", callback_data="delete_account_cancel")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ *Вы уверены, что хотите удалить свой аккаунт?*\n\n"
        "Это действие удалит всех ваших покемонов, монеты и прогресс. "
        "Вы сможете начать заново, используя команду /start.\n\n"
        "Пожалуйста, подтвердите ваше решение:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def delete_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-запросов для удаления аккаунта."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    await query.answer()
    
    if query.data == "delete_account_confirm":
        # Удаляем аккаунт пользователя
        success = delete_user(user_id)
        
        if success:
            logger.info(f"Пользователь {user_id} удалил свой аккаунт")
            
            # Устанавливаем флаг удаления аккаунта для последующего использования в start_command
            if hasattr(context, 'user_data'):
                context.user_data['account_deleted'] = True
                logger.info(f"Установлен флаг удаления аккаунта для пользователя {user_id}")
            
            await query.edit_message_text(
                "✅ Ваш аккаунт был успешно удален.\n\n"
                "Спасибо за игру! Если вы решите вернуться, просто используйте команду /start, "
                "чтобы создать новый аккаунт.",
                parse_mode="Markdown"
            )
        else:
            logger.error(f"Не удалось удалить аккаунт пользователя {user_id}")
            await query.edit_message_text(
                "❌ Произошла ошибка при удалении аккаунта. Пожалуйста, попробуйте позже.",
                parse_mode="Markdown"
            )
    elif query.data == "delete_account_cancel":
        # Отмена удаления
        logger.info(f"Пользователь {user_id} отменил удаление аккаунта")
        await query.edit_message_text(
            "✅ Удаление аккаунта отменено. Ваш аккаунт и все данные сохранены.",
            parse_mode="Markdown"
        )