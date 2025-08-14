import logging
from telegram import Update
from telegram.ext import ContextTypes
from storage import get_user
from pokemon_api import get_pokemon_image_url
import config

logger = logging.getLogger(__name__)

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /info command - show user info."""
    # Check if the command is a reply to another user's message
    if update.message.reply_to_message:
        # Get info for the replied user
        target_user_id = update.message.reply_to_message.from_user.id
        target_user_name = update.message.reply_to_message.from_user.first_name
        
        # Show the info for the target user
        await show_user_info(update, context, target_user_id, target_user_name)
    else:
        # Show info for the current user
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        await show_user_info(update, context, user_id, user_name)

async def show_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, user_name: str) -> None:
    """Show info for a specific user."""
    user = get_user(user_id)
    
    # Prepare the info message
    info_message = f"ℹ️ *Информация о тренере {user_name}*\n\n"
    
    # League info
    league_data = config.LEAGUES.get(user.league, config.LEAGUES[1])
    info_message += f"🏆 *Лига:* {user.league}\n"
    info_message += f"- Бонус атаки: +{league_data['attack_bonus']}\n"
    info_message += f"- Бонус защиты: +{league_data['defense_bonus']}\n"
    info_message += f"- Бонус здоровья: +{league_data['health_bonus']}\n\n"
    
    # Pokemon count
    info_message += f"🔢 *Покемонов поймано:* {user.caught_pokemon_count}\n"
    info_message += f"🔢 *Уникальных видов Покемонов:* {len(set(p.name for p in user.pokemons))}\n\n"
    
    # Balance
    info_message += f"💰 *Баланс:* {user.balance} монет\n\n"
    
    # Trainer info
    if user.trainer:
        trainer_data = config.TRAINERS.get(user.trainer.lower(), {})
        trainer_name = trainer_data.get("name", user.trainer)
        trainer_level = user.trainer_level
        power_bonus = trainer_data.get("power_bonus", 0) * 100
        
        info_message += f"👨‍🏫 *Тренер:* {trainer_name} (Уровень {trainer_level})\n"
        info_message += f"- Бонус силы: +{power_bonus}%\n\n"
    else:
        info_message += "👨‍🏫 *Тренер:* Нет\n\n"
    
    # Main Pokemon info
    if user.main_pokemon:
        pokemon = user.main_pokemon
        cp = pokemon.calculate_cp()
        
        info_message += f"⭐ *Основной Покемон:* {pokemon.name}\n"
        info_message += f"- CP: {cp}\n"
        info_message += f"- Тип: {', '.join(pokemon.types)}\n"
        info_message += f"- Атака: {pokemon.attack}\n"
        info_message += f"- Защита: {pokemon.defense}\n"
        info_message += f"- HP: {pokemon.hp}\n"
    else:
        info_message += "⭐ *Основной Покемон:* Нет\n"
    
    # Если у пользователя есть основной покемон, пробуем получить его изображение
    if user.main_pokemon:
        # Попробуем получить изображение покемона
        image_url = None
        try:
            # Если у покемона есть собственное изображение, используем его
            if hasattr(user.main_pokemon, 'image_url') and user.main_pokemon.image_url:
                image_url = user.main_pokemon.image_url
            else:
                # Иначе получаем изображение из API
                image_url = await get_pokemon_image_url(user.main_pokemon.name)
            
            # Если изображение найдено, отправляем его с информацией
            if image_url:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=image_url,
                    caption=info_message,
                    parse_mode="Markdown"
                )
                return
        except Exception as e:
            logger.error(f"Ошибка при получении изображения покемона: {e}")
    
    # Если у пользователя нет основного покемона или произошла ошибка при получении изображения,
    # отправляем только текстовое сообщение
    await update.message.reply_text(
        info_message,
        parse_mode="Markdown"
    )
