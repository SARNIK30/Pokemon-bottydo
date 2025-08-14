import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from storage import get_user
from pokemon_api import get_pokemon_data, get_pokemon_image_url, get_all_pokemon
import asyncio

logger = logging.getLogger(__name__)

# Количество покемонов на странице в Покедексе
POKEDEX_PAGE_SIZE = 10

async def pokedex_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /pokedex command - show the user's Pokedex."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    # Initialize Pokedex state
    context.user_data["pokedex_page"] = 1
    context.user_data["pokedex_mode"] = "all"  # "all" or "my"
    
    # Show the Pokedex
    await show_pokedex_page(update, context)

async def show_pokedex_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show a page in the Pokedex."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    page = context.user_data.get("pokedex_page", 1)
    mode = context.user_data.get("pokedex_mode", "all")
    
    # Определяем, есть ли выбранный покемон для отображения
    selected_pokemon = context.user_data.get("selected_pokemon", None)
    
    # Если у нас есть выбранный покемон, отобразим его информацию
    if selected_pokemon:
        # Удаляем выбранного покемона из контекста
        del context.user_data["selected_pokemon"]
        
        # Получаем URL изображения покемона
        if isinstance(selected_pokemon, dict):
            # Это покемон из общего списка
            pokemon_name = selected_pokemon.get("name", "").lower()
            image_url = await get_pokemon_image_url(pokemon_name)
            
            # Проверяем, есть ли у пользователя этот покемон
            has_pokemon = any(p.name.lower() == pokemon_name for p in user.pokemons)
            status = "✅ У вас есть этот Покемон!" if has_pokemon else "❌ У вас еще нет этого Покемона."
            
            # Получаем данные покемона
            pokemon_data = await get_pokemon_data(pokemon_name)
            
            if pokemon_data:
                # Извлекаем типы покемона
                types = [t["type"]["name"] for t in pokemon_data["types"]]
                
                # Извлекаем базовые характеристики
                stats = {stat["stat"]["name"]: stat["base_stat"] for stat in pokemon_data["stats"]}
                
                # Создаем сообщение с информацией о покемоне
                message = (
                    f"ℹ️ *Информация о Покемоне*\n\n"
                    f"*Имя:* {pokemon_name.capitalize()}\n"
                    f"*ID:* #{pokemon_data['id']}\n"
                    f"*Типы:* {', '.join(types)}\n\n"
                    f"*Базовые характеристики:*\n"
                    f"- HP: {stats.get('hp', 'Н/Д')}\n"
                    f"- Атака: {stats.get('attack', 'Н/Д')}\n"
                    f"- Защита: {stats.get('defense', 'Н/Д')}\n"
                    f"- Скорость: {stats.get('speed', 'Н/Д')}\n\n"
                    f"{status}"
                )
            else:
                message = f"ℹ️ *Информация о Покемоне*\n\n*Имя:* {pokemon_name.capitalize()}\n\n❌ Не удалось получить подробную информацию."
        else:
            # Это покемон пользователя
            pokemon = selected_pokemon
            image_url = await get_pokemon_image_url(pokemon.name.lower())
            
            # Создаем сообщение с информацией о покемоне
            message = (
                f"ℹ️ *Информация о Покемоне*\n\n"
                f"*Имя:* {pokemon.name}\n"
                f"*Типы:* {', '.join(pokemon.types)}\n"
                f"*CP:* {pokemon.calculate_cp()}\n\n"
                f"*Характеристики:*\n"
                f"- Атака: {pokemon.attack}\n"
                f"- Защита: {pokemon.defense}\n"
                f"- HP: {pokemon.hp}\n"
            )
            
            # Добавляем индикатор "Основной Покемон", если это основной покемон пользователя
            if user.main_pokemon and user.main_pokemon.pokemon_id == pokemon.pokemon_id:
                message += "\n⭐ Это ваш основной Покемон."
        
        # Создаем кнопку для возврата к Покедексу
        keyboard = [[InlineKeyboardButton("◀️ Назад к Покедексу", callback_data="pokedex_back")]]
        
        # Если это покемон пользователя, добавляем кнопку установки в качестве основного
        if not isinstance(selected_pokemon, dict) and not (user.main_pokemon and user.main_pokemon.pokemon_id == pokemon.pokemon_id):
            # Находим индекс покемона в списке покемонов пользователя
            pokemon_idx = next((i for i, p in enumerate(user.pokemons) if p.pokemon_id == pokemon.pokemon_id), None)
            if pokemon_idx is not None:
                keyboard.append([InlineKeyboardButton("⭐ Сделать основным Покемоном", callback_data=f"pokedex_main_{pokemon_idx}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Если у нас есть URL изображения, отправляем его вместе с сообщением
        if image_url:
            if update.callback_query:
                await update.callback_query.message.reply_photo(
                    photo=image_url,
                    caption=message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                await update.callback_query.message.delete()
            else:
                await update.message.reply_photo(
                    photo=image_url,
                    caption=message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
        else:
            # Просто отправляем сообщение, если у нас нет изображения
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
        return
    
    # Get the list of Pokemon based on mode
    if mode == "all":
        # Get all Pokemon from the API
        all_pokemon = await get_all_pokemon(500)
        pokemon_list = all_pokemon
        
        # Calculate pagination
        total_pages = (len(pokemon_list) + POKEDEX_PAGE_SIZE - 1) // POKEDEX_PAGE_SIZE
        start_idx = (page - 1) * POKEDEX_PAGE_SIZE
        end_idx = min(start_idx + POKEDEX_PAGE_SIZE, len(pokemon_list))
        
        # Get the Pokemon for this page
        page_pokemon = pokemon_list[start_idx:end_idx]
        
        # Create the message
        message = f"📚 *Покедекс* (Все Покемоны - Страница {page}/{total_pages})\n\n"
        
        # Add Pokemon to the message
        for i, pokemon in enumerate(page_pokemon, start=1):
            # Check if the user has this Pokemon
            has_pokemon = any(p.name.lower() == pokemon["name"].lower() for p in user.pokemons)
            status = "✅" if has_pokemon else "❌"
            message += f"{status} {i + start_idx}. {pokemon['name'].capitalize()}\n"
        
    else:  # mode == "my"
        # Get the user's Pokemon
        user_pokemon = user.pokemons
        
        # Calculate pagination
        total_pages = (len(user_pokemon) + POKEDEX_PAGE_SIZE - 1) // POKEDEX_PAGE_SIZE
        start_idx = (page - 1) * POKEDEX_PAGE_SIZE
        end_idx = min(start_idx + POKEDEX_PAGE_SIZE, len(user_pokemon))
        
        # Get the Pokemon for this page
        page_pokemon = user_pokemon[start_idx:end_idx]
        
        # Create the message
        message = f"📚 *Мои Покемоны* (Страница {page}/{total_pages or 1})\n\n"
        
        # Add Pokemon to the message
        for i, pokemon in enumerate(page_pokemon, start=1):
            cp = pokemon.calculate_cp()
            message += f"{i + start_idx}. {pokemon.name} (CP: {cp})\n"
    
    # Create navigation buttons
    keyboard = []
    
    # Add page navigation
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"pokedex_page_{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(" ", callback_data="pokedex_noop"))
    
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages or 1}", callback_data="pokedex_noop"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"pokedex_page_{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(" ", callback_data="pokedex_noop"))
    
    keyboard.append(nav_buttons)
    
    # Add mode toggle button
    toggle_text = "👤 Мои Покемоны" if mode == "all" else "🌍 Все Покемоны"
    toggle_data = "pokedex_mode_my" if mode == "all" else "pokedex_mode_all"
    keyboard.append([InlineKeyboardButton(toggle_text, callback_data=toggle_data)])
    
    # Add search button
    keyboard.append([InlineKeyboardButton("🔍 Поиск", callback_data="pokedex_search")])
    
    # Add view buttons for Pokemon
    if mode == "all" and page_pokemon:
        # Для каждого покемона в общем списке добавляем кнопку просмотра
        for i, pokemon in enumerate(page_pokemon, start=1):
            idx = i + start_idx - 1
            keyboard.append([
                InlineKeyboardButton(f"ℹ️ #{idx}: {pokemon['name'].capitalize()}", callback_data=f"pokedex_view_all_{idx}")
            ])
    elif mode == "my" and page_pokemon:
        # Для каждого покемона пользователя добавляем кнопки просмотра и установки в качестве основного
        for i, pokemon in enumerate(page_pokemon, start=1):
            idx = i + start_idx - 1
            keyboard.append([
                InlineKeyboardButton(f"ℹ️ #{i}: {pokemon.name}", callback_data=f"pokedex_view_{idx}"),
                InlineKeyboardButton("⭐ Основной", callback_data=f"pokedex_main_{idx}")
            ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send or edit the message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def pokedex_navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Pokedex navigation callbacks."""
    query = update.callback_query
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    try:
        # Extract the action from the callback data
        parts = query.data.split("_")
        action = parts[1]
        
        if action == "page":
            # Change the page
            context.user_data["pokedex_page"] = int(parts[2])
            await query.answer()
            await show_pokedex_page(update, context)
            
        elif action == "mode":
            # Change the mode (all or my)
            context.user_data["pokedex_mode"] = parts[2]
            context.user_data["pokedex_page"] = 1  # Reset to first page
            await query.answer()
            await show_pokedex_page(update, context)
            
        elif action == "search":
            # Set up search state
            context.user_data["pokedex_state"] = "search"
            await query.answer()
            await query.edit_message_text(
                "🔍 *Поиск по Покедексу*\n\n"
                "Пожалуйста, введите имя или ID Покемона, которого вы ищете:",
                parse_mode="Markdown"
            )
            
        elif action == "view":
            # Проверяем, просмотр какого типа покемона запрошен
            if parts[2] == "all":
                # Просмотр покемона из общего списка
                pokemon_idx = int(parts[3])
                mode = context.user_data.get("pokedex_mode", "all")
                page = context.user_data.get("pokedex_page", 1)
                
                # Получаем список всех покемонов
                all_pokemon = await get_all_pokemon(500)
                
                # Рассчитываем индексы для пагинации
                start_idx = (page - 1) * POKEDEX_PAGE_SIZE
                end_idx = min(start_idx + POKEDEX_PAGE_SIZE, len(all_pokemon))
                
                # Получаем покемонов для этой страницы
                page_pokemon = all_pokemon[start_idx:end_idx]
                
                # Убеждаемся, что покемон существует
                if pokemon_idx < 0 or pokemon_idx >= len(all_pokemon):
                    await query.answer("Такой покемон не найден!")
                    return
                
                # Находим покемона по индексу
                selected_pokemon = all_pokemon[pokemon_idx]
                
                # Сохраняем выбранного покемона в контексте
                context.user_data["selected_pokemon"] = selected_pokemon
                
                await query.answer()
                await show_pokedex_page(update, context)
            else:
                # Просмотр покемона пользователя
                pokemon_idx = int(parts[2])
                await query.answer()
                
                # Убеждаемся, что покемон существует
                if pokemon_idx < 0 or pokemon_idx >= len(user.pokemons):
                    await query.edit_message_text(
                        "❌ Этот Покемон больше не существует.",
                        parse_mode="Markdown"
                    )
                    return
                
                # Находим покемона по индексу
                pokemon = user.pokemons[pokemon_idx]
                
                # Сохраняем выбранного покемона в контексте
                context.user_data["selected_pokemon"] = pokemon
                
                await show_pokedex_page(update, context)
            
        elif action == "main":
            # Set a Pokemon as the main Pokemon
            pokemon_idx = int(parts[2])
            await query.answer()
            
            # Make sure the Pokemon exists
            if pokemon_idx < 0 or pokemon_idx >= len(user.pokemons):
                await query.edit_message_text(
                    "❌ Этот Покемон больше не существует.",
                    parse_mode="Markdown"
                )
                return
            
            pokemon = user.pokemons[pokemon_idx]
            
            # Set as main Pokemon
            user.main_pokemon = pokemon
            
            # Save the user
            from storage import save_user
            save_user(user)
            
            await query.answer(f"{pokemon.name} теперь ваш основной Покемон!")
            await show_pokedex_page(update, context)
            
        elif action == "back":
            # Go back to the Pokedex
            await query.answer("Возвращаемся к Покедексу")
            # Сбрасываем выбранного покемона, если он есть
            if "selected_pokemon" in context.user_data:
                del context.user_data["selected_pokemon"]
            
            # Обновляем режим и страницу Покедекса, если они сбросились
            if "pokedex_mode" not in context.user_data:
                context.user_data["pokedex_mode"] = "all"
            if "pokedex_page" not in context.user_data:
                context.user_data["pokedex_page"] = 1
                
            # Показываем страницу покедекса
            await show_pokedex_page(update, context)
            
        elif action == "noop":
            # No operation (dummy button)
            await query.answer()
            
    except Exception as e:
        logger.error(f"Ошибка в обратном вызове покедекса: {e}")
        logger.error(f"Подробная информация об ошибке: {traceback.format_exc()}")
        await query.answer(f"Ошибка: {str(e)}")

async def handle_pokedex_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle a search query for the Pokedex."""
    if "pokedex_state" not in context.user_data or context.user_data["pokedex_state"] != "search":
        return False
    
    # Clear the search state
    del context.user_data["pokedex_state"]
    
    search_query = update.message.text.lower()
    
    try:
        # Try to get Pokemon data from the API
        pokemon_data = await get_pokemon_data(search_query)
        
        if not pokemon_data:
            await update.message.reply_text(
                f"❌ Покемон с именем или ID '{search_query}' не найден.",
                parse_mode="Markdown"
            )
            return True
        
        # Создаем объект покемона в формате словаря для просмотра
        selected_pokemon = {
            "name": pokemon_data["name"],
            "id": pokemon_data["id"]
        }
        
        # Сохраняем выбранного покемона в контексте для отображения через show_pokedex_page
        context.user_data["selected_pokemon"] = selected_pokemon
        
        # Показываем информацию о покемоне с использованием существующей функции
        await show_pokedex_page(update, context)
        
    except Exception as e:
        logger.error(f"Ошибка при поиске Покемона: {e}")
        logger.error(f"Подробная информация об ошибке: {traceback.format_exc()}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при поиске '{search_query}': {str(e)}",
            parse_mode="Markdown"
        )
    
    return True
