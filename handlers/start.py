# ********************************************************************
# СПЕЦИАЛЬНАЯ НАСТРОЙКА: Добавлена расширенная поддержка для группы с ID 2435502062
# В этой группе:
# 1. Расширен список команд для призыва покемонов
# 2. Расширен список команд для ловли покемонов
# 3. Увеличена вероятность появления покемонов до 10% (вместо 5% в обычных группах)
# 4. Увеличен шанс успешной поимки покемона:
#    - Базовый шанс поимки увеличен до 65% (вместо 50%)
#    - Уменьшен штраф за высокий CP
#    - Удвоен бонус за лигу
#    - Бонус от покеболов увеличен в 1.5 раза
#    - Минимальный порог шанса поимки составляет 40%
# 5. Добавлено расширенное логирование действий в этой группе
# ********************************************************************

import logging
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from storage import (
    get_user, add_pokemon_to_user, get_wild_pokemon,
    set_wild_pokemon, clear_wild_pokemon, is_wild_pokemon_available,
    mark_wild_pokemon_caught, save_user
)
from pokemon_api import get_pokemon_data, get_pokemon_image_url, get_all_pokemon
from models.pokemon import Pokemon
import config

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command - initialize the user and begin the game."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    # Обновляем username пользователя, если он доступен
    if update.effective_user.username:
        user.username = update.effective_user.username
        save_user(user)
    
    # Проверка был ли аккаунт недавно удален
    if not user.pokemons and hasattr(context, 'user_data') and context.user_data.get('account_deleted'):
        # Пользователь только что удалил аккаунт и создает новый
        welcome_msg = (
            f"👋 Добро пожаловать обратно, Тренер {update.effective_user.first_name}!\n\n"
            "Ваш аккаунт был успешно пересоздан. Теперь вы можете начать своё новое приключение в мире покемонов.\n\n"
            "Выберите своего стартового покемона:"
        )
        
        # Создаем клавиатуру для выбора стартового покемона
        keyboard = [
            [
                InlineKeyboardButton("🔥 Charmander", callback_data="starter_charmander"),
                InlineKeyboardButton("💧 Squirtle", callback_data="starter_squirtle"),
                InlineKeyboardButton("🌿 Bulbasaur", callback_data="starter_bulbasaur")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Очищаем флаг удаления аккаунта
        context.user_data['account_deleted'] = False
        
        await update.message.reply_text(welcome_msg, reply_markup=reply_markup)
        return
        
    # Check if the user already has Pokemon
    if user.pokemons:
        # User already started, show welcome back message
        welcome_msg = (
            f"С возвращением, Тренер {update.effective_user.first_name}!\n\n"
            f"У вас {len(user.pokemons)} Покемонов в коллекции.\n"
            f"Ваш баланс: {user.balance} монет\n\n"
            "Что бы вы хотели сделать?\n\n"
            "Команды:\n"
            "/info - Просмотр вашей статистики\n"
            "/pokedex - Открыть Покедекс\n"
            "/battle - Сразиться с другим тренером\n"
            "/shop - Посетить магазин\n"
            "/trade - Обменяться Покемонами с другими\n"
            "/evolution - Эволюционировать покемона\n"
            "/promocode - Активировать промокод\n"
            "/games - Играть в мини-игры и зарабатывать монеты\n"
            "/catch - Призвать покемона за монеты\n"
            "/delete_account - Удалить аккаунт\n\n"
            "Для призыва покемона можно также отправить: 'Призвать покемона'"
        )
        
        await update.message.reply_text(welcome_msg)
        return
    
    # New user, show welcome message and starter Pokemon selection
    welcome_msg = (
        f"Добро пожаловать в мир Покемонов, {update.effective_user.first_name}!\n\n"
        "Чтобы начать свое путешествие, вы должны выбрать своего первого Покемона.\n"
        "Выбирайте с умом, ведь он станет вашим спутником на протяжении всего приключения!"
    )
    
    # Create buttons for starter Pokemon
    keyboard = []
    for starter_id, starter_data in config.STARTER_POKEMON.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{starter_data['name']} ({starter_data['type']})",
                callback_data=f"starter_{starter_id}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup)

async def choose_starter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the selection of a starter Pokemon."""
    query = update.callback_query
    await query.answer()  # Важно: подтверждаем запрос, чтобы не было ожидания
    
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    try:
        # Извлекаем выбранного стартера
        selected_starter = query.data.split("_")[1]
        
        # Проверяем, есть ли у пользователя уже покемоны
        if user.pokemons:
            await query.edit_message_text("Вы уже начали свое путешествие!")
            return
        
        # Получаем данные о стартере
        starter_data = config.STARTER_POKEMON.get(selected_starter)
        if not starter_data:
            await query.edit_message_text("Неверный выбор покемона! Попробуйте еще раз.")
            return
        
        # Создаем покемона на основе выбора
        # Используем ID из конфигурации для более надежного запроса
        pokemon_id = starter_data["id"]
        
        # Добавляем информационное сообщение для пользователя
        await query.edit_message_text(f"Вы выбрали {starter_data['name']}! Создаем вашего первого покемона...")
        
        # Получаем данные покемона из API
        pokemon_data = await get_pokemon_data(str(pokemon_id))
        if not pokemon_data:
            await query.edit_message_text(f"Ошибка при получении данных о покемоне {starter_data['name']}. Попробуйте еще раз.")
            logger.error(f"Не удалось получить данные о покемоне с ID {pokemon_id}")
            return
        
        # Создаем объект покемона из полученных данных
        starter_pokemon = Pokemon.create_from_data(pokemon_data)
        if not starter_pokemon:
            await query.edit_message_text(f"Ошибка при создании покемона {starter_data['name']}. Попробуйте еще раз.")
            logger.error(f"Не удалось создать объект покемона из данных API для ID {pokemon_id}")
            return
        
        # Добавляем покемона пользователю
        user.pokemons.append(starter_pokemon)
        user.main_pokemon = starter_pokemon  # Устанавливаем как основного покемона
        user.caught_pokemon_count += 1
        save_user(user)
        
        # Получаем изображение покемона
        image_url = await get_pokemon_image_url(str(pokemon_id))
        
        success_message = (
            f"🎉 Поздравляем! Вы выбрали {starter_data['name']} в качестве стартового Покемона!\n\n"
            f"Тип: {starter_data['type']}\n"
            f"Атака: {starter_pokemon.attack}\n"
            f"Защита: {starter_pokemon.defense}\n"
            f"Здоровье: {starter_pokemon.hp}\n\n"
            f"Ваше путешествие начинается. Удачи, Тренер {update.effective_user.first_name}!\n\n"
            "Основные команды:\n"
            "/info - Просмотр вашей статистики\n"
            "/pokedex - Открыть Покедекс\n"
            "/battle - Сразиться с другим тренером\n"
            "/shop - Посетить магазин\n"
            "/trade - Обменяться Покемонами с другими\n"
            "/evolution - Эволюционировать покемона\n"
            "/promocode - Активировать промокод\n"
            "/games - Играть в мини-игры и зарабатывать монеты\n"
            "/catch - Призвать покемона за монеты\n"
            "/delete_account - Удалить аккаунт\n\n"
            "Для призыва покемона можно также отправить: 'Призвать покемона'"
        )
        
        # Отправляем сообщение с изображением
        if image_url:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_url,
                caption=success_message
            )
            # Обновляем оригинальное сообщение
            await query.edit_message_text("Вы успешно выбрали своего первого покемона!")
        else:
            # Если изображение не найдено, просто отправляем текстовое сообщение
            await query.edit_message_text(success_message)
        
        logger.info(f"Пользователь {user_id} успешно выбрал стартового покемона {starter_data['name']}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора стартового покемона: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при выборе покемона. Попробуйте еще раз с командой /start."
        )

async def catch_pokemon_attempt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка попытки поймать покемона с помощью команды /catch."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    logger.info(f"Попытка поймать покемона пользователем {user_id} в чате {chat_id}")
    
    # Проверяем, доступен ли покемон для поимки
    wild_pokemon = get_wild_pokemon(chat_id)
    if wild_pokemon:
        logger.info(f"Найден дикий покемон в чате {chat_id}: {wild_pokemon}")
    else:
        logger.info(f"Дикий покемон не найден в чате {chat_id}")
    
    if not is_wild_pokemon_available(chat_id):
        logger.info(f"Покемон в чате {chat_id} недоступен для ловли")
        await context.bot.send_message(
            chat_id=chat_id,
            text="❓ Здесь нет дикого покемона для ловли. Сначала призовите его с помощью команды /catch."
        )
        return
    
    # Получаем данные о покемоне
    wild_pokemon = get_wild_pokemon(chat_id)
    pokemon_data = wild_pokemon["data"]
    pokemon_name = pokemon_data["name"]
    
    # Отмечаем покемона как пойманного
    mark_wild_pokemon_caught(chat_id)
    
    # Создаем объект покемона
    pokemon = Pokemon.create_from_data(pokemon_data)
    
    # Получаем данные пользователя
    user = get_user(user_id)
    
    # Проверяем успешность ловли
    catch_success = calculate_catch_success(user, pokemon)
    
    # Отправляем ответное сообщение в зависимости от результата
    if catch_success:
        # Добавляем покемона в коллекцию пользователя
        if add_pokemon_to_user(user_id, pokemon):
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎉 Поздравляем, {update.effective_user.first_name}!\n\n"
                     f"Вы поймали **{pokemon_name.capitalize()}**!\n"
                     f"CP: {pokemon.calculate_cp()}\n\n"
                     f"Покемон добавлен в вашу коллекцию. Используйте /pokedex для просмотра ваших Покемонов.",
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Вы поймали **{pokemon_name.capitalize()}**, но у вас уже есть {config.MAX_SAME_POKEMON} таких!\n\n"
                     f"Попробуйте эволюционировать их с помощью /evolution {pokemon_name}",
                parse_mode="Markdown"
            )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"О нет! **{pokemon_name.capitalize()}** вырвался и убежал!\n\n"
                 f"Попробуйте использовать лучшие Покеболы из /shop, чтобы увеличить ваш шанс поимки.",
            parse_mode="Markdown"
        )
    
    # Очищаем данные о диком покемоне
    clear_wild_pokemon(chat_id)

async def spawn_wild_pokemon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Spawn a wild Pokemon in the chat."""
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    try:
        # Логирование начала процесса для улучшенной диагностики
        logger.info(f"Запрос на спавн покемона в чате {chat_id} (тип: {chat_type})")
        
        # Проверяем права бота в ЛЮБОМ групповом чате
        is_group = chat_type in ['group', 'supergroup', 'channel']
        
        if is_group:
            logger.info(f"Проверяем права бота в групповом чате {chat_id} (тип: {chat_type})")
            try:
                # Получаем информацию о чате
                chat_info = await context.bot.get_chat(chat_id)
                logger.info(f"Информация о чате {chat_id}: тип={chat_info.type}, заголовок={chat_info.title}")
                
                # Проверяем, может ли бот отправлять сообщения в этот чат
                bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
                logger.info(f"Статус бота в чате {chat_id}: {bot_member.status}")
                
                if bot_member.status in ['restricted', 'left', 'kicked']:
                    if bot_member.status == 'restricted' and not bot_member.can_send_messages:
                        logger.error(f"Бот не имеет прав отправлять сообщения в чате {chat_id}")
                        return
                    elif bot_member.status in ['left', 'kicked']:
                        logger.error(f"Бот не находится в чате {chat_id} (статус: {bot_member.status})")
                        return
                    
            except Exception as e:
                logger.error(f"Ошибка при проверке прав бота в чате {chat_id}: {e}")
                # Продолжаем несмотря на ошибку, возможно у бота есть права
        
        # Увеличим логирование для отладки
        logger.info(f"Начат процесс спавна покемона в чате {chat_id} (тип: {chat_type})")
        
        # Check if there's already a wild Pokemon in this chat
        if get_wild_pokemon(chat_id):
            logger.info(f"В чате {chat_id} уже есть дикий покемон, новый не спавним")
            return
        
        # Get a random Pokemon from the API
        all_pokemon = await get_all_pokemon(500)
        if not all_pokemon:
            logger.error("Не удалось получить список Покемонов из API")
            return
        
        random_pokemon = random.choice(all_pokemon)
        pokemon_name = random_pokemon["name"]
        
        # Get the Pokemon data
        pokemon_data = await get_pokemon_data(pokemon_name)
        if not pokemon_data:
            logger.error(f"Не удалось получить данные для Покемона {pokemon_name}")
            return
        
        # Get the Pokemon image
        image_url = await get_pokemon_image_url(pokemon_name)
        
        # Store the wild Pokemon in the chat
        set_wild_pokemon(chat_id, pokemon_data)
        
        # Логируем информацию о спавне
        logger.info(f"Спавн покемона {pokemon_name} в чате {chat_id} (тип: {chat_type})")
        
        # Send a message to the chat - улучшенный алгоритм для обоих типов чатов
        message = (
            f"🔥🔥🔥 ПОЯВИЛСЯ ДИКИЙ **{pokemon_name.capitalize()}**! 🔥🔥🔥\n\n"
            f"Быстрее! Используйте команду /catch, чтобы поймать его!\n"
            f"Вы также можете написать 'поймать' или 'ловлю'!\n"
            f"У вас есть только 60 секунд!"
        )
        
        # Для персональных чатов сделаем более скромное сообщение
        if chat_type == 'private':
            message = (
                f"🔥 Появился дикий **{pokemon_name.capitalize()}**!\n\n"
                f"Используйте команду /catch, чтобы поймать его!"
            )
        
        try:
            # Сначала пробуем отправить сообщение с изображением
            if image_url:
                try:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=image_url,
                        caption=message,
                        parse_mode="Markdown"
                    )
                    logger.info(f"Успешно отправлено сообщение с фото покемона {pokemon_name} в чат {chat_id}")
                except Exception as photo_error:
                    logger.error(f"Ошибка при отправке фото покемона {pokemon_name} в чат {chat_id}: {photo_error}")
                    # Если не удалось отправить фото, отправляем только текст
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode="Markdown"
                    )
                    logger.info(f"Отправлено текстовое сообщение о покемоне {pokemon_name} в чат {chat_id} после ошибки с фото")
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="Markdown"
                )
                logger.info(f"Отправлено текстовое сообщение о покемоне {pokemon_name} в чат {chat_id}")
            
            # Schedule cleanup after 1 minute
            asyncio.create_task(cleanup_wild_pokemon(context, chat_id))
            
        except Exception as message_error:
            logger.error(f"Критическая ошибка при отправке сообщения в чат {chat_id}: {message_error}")
            # В случае ошибки чистим данные о покемоне
            clear_wild_pokemon(chat_id)
            
    except Exception as e:
        logger.error(f"Общая ошибка при спавне покемона в чате {chat_id}: {e}")
        # Чистим на случай, если данные о покемоне уже были созданы
        try:
            clear_wild_pokemon(chat_id)
        except:
            pass

async def cleanup_wild_pokemon(context, chat_id):
    """Clean up a wild Pokemon after 1 minute if not caught."""
    await asyncio.sleep(60)  # Wait for 1 minute
    
    # Check if the Pokemon is still there and not caught
    wild_pokemon = get_wild_pokemon(chat_id)
    if wild_pokemon and not wild_pokemon.get("caught", False):
        # Clear the wild Pokemon
        clear_wild_pokemon(chat_id)
        
        # Send a message to the chat
        await context.bot.send_message(
            chat_id=chat_id,
            text="Дикий Покемон убежал!"
        )

async def catch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /catch для призыва или ловли покемона."""
    logger.info("Вызвана команда /catch")
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Получаем информацию о покемоне в чате для логирования
    wild_pokemon = get_wild_pokemon(chat_id)
    if wild_pokemon:
        logger.info(f"В чате {chat_id} есть дикий покемон: {wild_pokemon}")
        logger.info(f"Статус покемона: {'пойман' if wild_pokemon.get('caught', False) else 'не пойман'}")
        logger.info(f"Время появления: {wild_pokemon.get('timestamp', 0)}")
    else:
        logger.info(f"В чате {chat_id} нет дикого покемона")
    
    # Проверяем, есть ли доступный покемон для ловли
    if is_wild_pokemon_available(chat_id):
        logger.info(f"Пользователь {user_id} пытается поймать дикого покемона командой /catch")
        await catch_pokemon_attempt(update, context)
    else:
        # Если покемона нет, вызываем обычную логику призыва
        logger.info(f"Пользователь {user_id} пытается призвать покемона командой /catch")
        await _call_pokemon_logic(update, context)

async def call_pokemon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовой команды 'призвать покемона'."""
    logger.info("Вызвана текстовая команда призыва покемона")
    await _call_pokemon_logic(update, context)
    
async def _call_pokemon_logic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Общая логика призыва покемона за монеты."""
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        
        # Логирование начала запроса
        logger.info(f"Пользователь {user_id} вызывает команду призыва покемона в чате {chat_id} (тип: {chat_type})")
        
        # Проверка на наличие уже активного покемона
        if is_wild_pokemon_available(chat_id):
            logger.info(f"В чате {chat_id} уже есть дикий покемон, отклоняем запрос призыва")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❗ В этом чате уже есть дикий покемон! Поймайте его, прежде чем призывать нового."
            )
            return
        
        # Проверка прав в групповом чате
        if chat_type in ['group', 'supergroup']:
            try:
                bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
                if bot_member.status == 'restricted' and not bot_member.can_send_messages:
                    logger.error(f"Бот не имеет прав для отправки сообщений в чате {chat_id}")
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⚠️ Я не могу отправлять сообщения в этот чат. Пожалуйста, дайте мне права администратора."
                    )
                    return
            except Exception as e:
                logger.error(f"Ошибка при проверке прав бота в чате {chat_id}: {e}")
                # Продолжаем, но возможны проблемы
        
        # Получаем данные пользователя
        user = get_user(user_id)
        
        # Проверяем, есть ли у пользователя достаточно монет
        if user.balance < config.POKEMON_CALL_COST:
            logger.info(f"У пользователя {user_id} недостаточно монет: {user.balance}/{config.POKEMON_CALL_COST}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ У вас недостаточно монет для призыва Покемона.\n\n"
                     f"Ваш баланс: {user.balance} монет\n"
                     f"Стоимость призыва: {config.POKEMON_CALL_COST} монет\n\n"
                     f"Заработать монеты можно с помощью команды /games"
            )
            return
        
        # Вычитаем стоимость призыва
        user.balance -= config.POKEMON_CALL_COST
        save_user(user)
        logger.info(f"Пользователь {user_id} успешно заплатил {config.POKEMON_CALL_COST} монет, новый баланс: {user.balance}")
        
        try:
            # Отправляем сообщение о призыве в любом типе чата
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✨ Вы заплатили {config.POKEMON_CALL_COST} монет за призыв Покемона..."
            )
            
            # Призываем покемона
            logger.info(f"Запуск призыва покемона для пользователя {user_id} в чате {chat_id}")
            await spawn_wild_pokemon(update, context)
        except Exception as e:
            # Если произошла ошибка при призыве покемона, возвращаем деньги
            logger.error(f"Ошибка при призыве покемона: {e}")
            user.balance += config.POKEMON_CALL_COST
            save_user(user)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Произошла ошибка при призыве покемона. Ваши монеты возвращены."
            )
            
    except Exception as e:
        logger.error(f"Общая ошибка в функции призыва покемона: {e}")
        try:
            if update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Произошла неизвестная ошибка при призыве покемона. Пожалуйста, попробуйте позже."
                )
        except:
            pass

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка сообщений в групповых чатах."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type
    
    # Проверка на тип чата (должен быть групповой)
    if chat_type not in ['group', 'supergroup', 'channel']:
        logger.warning(f"handle_group_message вызван не для группового чата: {chat_type}")
        return
    
    # Дополнительное логирование для конкретной группы с ID -1002435502062
    if chat_id == -1002435502062:
        logger.info(f"[ВАЖНО] Сообщение в специальной группе -1002435502062 от пользователя {user_id}")
    
    # Получаем информацию о чате для диагностики проблем
    try:
        chat_info = await context.bot.get_chat(chat_id)
        logger.info(f"Информация о групповом чате {chat_id}: название={chat_info.title}, тип={chat_info.type}")
    except Exception as e:
        logger.error(f"Не удалось получить информацию о чате {chat_id}: {e}")
    
    # Если сообщения нет, просто выходим
    if not update.message or not update.message.text:
        return
        
    message_text = update.message.text.lower().strip()
    
    # Добавим логирование для отладки
    logger.info(f"Получено сообщение в групповом чате ID={chat_id} (тип: {chat_type}): {message_text}")
    
    # Для группы с ID -1002435502062 расширяем список команд и снижаем требования
    if chat_id == -1002435502062:
        # Для специальной группы принимаем любые сообщения с упоминанием покемонов
        if ("покемон" in message_text or 
            "поке" in message_text or 
            "призвать" in message_text or 
            "призыв" in message_text or
            "вызвать" in message_text or
            "pokemon" in message_text):
            
            logger.info(f"[ГРУППА -1002435502062] Пользователь {user_id} вызывает покемона специальной командой '{message_text}'")
            await _call_pokemon_logic(update, context)
            return
    
    # Проверяем команду призыва покемона, более широким набором шаблонов
    if (message_text.startswith("призвать покемон") or 
        message_text == "призвать" or 
        message_text == "покемон призыв" or
        message_text == "вызвать покемона" or
        message_text == "зови покемона" or
        message_text == "призови покемона" or
        message_text == "покемон" or
        message_text == "👾 покемон"):
        
        logger.info(f"Пользователь {user_id} вызывает покемона в групповом чате {chat_id}")
        await _call_pokemon_logic(update, context)
        return
    
    # Проверяем наличие активного покемона в чате
    wild_pokemon = get_wild_pokemon(chat_id)
    if wild_pokemon:
        logger.info(f"В чате {chat_id} есть дикий покемон: {wild_pokemon.get('data', {}).get('name', 'неизвестный')}")
    
    # Расширенный список команд для ловли покемона
    catch_commands = ["ловлю", "поймать", "catch", "ловить", "схватить", "ловля", 
                     "поймал", "лови его", "хватай", "лови", "бросить покебол"]
    
    # Для специальной группы -1002435502062 добавляем дополнительные команды ловли
    if chat_id == -1002435502062:
        # Расширенный список для специальной группы
        special_catch_commands = ["поймаю", "ловите", "захват", "беру", "моё", "мой", 
                                 "хочу", "нужен", "забираю", "словить", "словлю", 
                                 "ловушка", "выбираю", "я выбираю тебя", "покебол"]
        catch_commands.extend(special_catch_commands)
        
        # Более либеральная проверка для этой группы
        if any(catch_word in message_text for catch_word in catch_commands):
            if is_wild_pokemon_available(chat_id):
                logger.info(f"[ГРУППА -1002435502062] Пользователь {user_id} ловит покемона командой '{message_text}'")
                await handle_catch_attempt(update, context)
                return
            else:
                logger.info(f"[ГРУППА -1002435502062] Пользователь {user_id} пытался поймать покемона, но нет доступного")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="В этом чате нет дикого покемона для ловли. Сначала призовите его!"
                )
                return
    else:
        # Обычная проверка доступности покемона по сравнению слов для других групп
        for catch_word in catch_commands:
            if catch_word in message_text:
                if is_wild_pokemon_available(chat_id):
                    logger.info(f"Пользователь {user_id} пытается поймать покемона командой '{message_text}' в групповом чате {chat_id}")
                    # Если пользователь отправил команду ловли, обрабатываем попытку поймать покемона
                    await handle_catch_attempt(update, context)
                    return
                else:
                    logger.info(f"Пользователь {user_id} пытался поймать покемона, но в чате {chat_id} нет доступного покемона")
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="В этом чате нет дикого покемона для ловли. Сначала призовите его!"
                    )
                    return
    
    # Определяем вероятность спавна в зависимости от группы
    spawn_chance = 0.05  # Базовая вероятность для обычных групп (5%)
    
    # Для специальной группы увеличиваем вероятность до 10%
    if chat_id == -1002435502062:
        spawn_chance = 0.10
        logger.info(f"[ГРУППА -1002435502062] Повышенная вероятность спавна покемона: {spawn_chance * 100}%")
    
    # С увеличенной вероятностью запускаем спавн покемона
    if random.random() < spawn_chance:
        logger.info(f"Запуск случайного спавна покемона в групповом чате {chat_id}")
        await spawn_wild_pokemon(update, context)
        return

async def handle_catch_attempt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a user's attempt to catch a wild Pokemon or summon one."""
    # Проверяем, является ли это командой призыва
    if update.message.text and (update.message.text.lower() == "призвать покемона" or 
                               update.message.text.lower() == "призвать покемонa"):
        logger.info("Вызвана текстовая команда призыва покемона через handle_catch_attempt")
        await _call_pokemon_logic(update, context)
        return
    
    # Check if this is an admin message
    if "admin_state" in context.user_data:
        # Let the admin handler process this message
        from handlers.admin import handle_admin_message
        if await handle_admin_message(update, context):
            return
    
    # Check if this is a Pokedex search
    from handlers.pokedex import handle_pokedex_search
    if await handle_pokedex_search(update, context):
        return
    
    # Regular message, check if it's a catch attempt in group chat
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type
    
    # Добавим лог для отладки
    logger.info(f"Обработка сообщения для ловли покемона в чате {chat_id} (тип: {chat_type})")
    
    # Проверяем, доступен ли покемон для поимки в любом типе чата
    if is_wild_pokemon_available(chat_id):
        # Логируем инфо если покемон доступен
        logger.info(f"Дикий покемон доступен в чате {chat_id}")
        
        # Если это личный чат - позволяем ловить любым сообщением
        if chat_type == 'private':
            # Продолжаем ловлю
            logger.info(f"Пользователь {user_id} пытается поймать покемона в личном чате")
            pass
        # Для групповых чатов принимаем разные варианты команды ловли
        elif chat_type in ['group', 'supergroup'] and update.message.text:
            message_text = update.message.text.lower().strip()
            
            # Специальная обработка для группы -1002435502062
            if chat_id == -1002435502062:
                # Расширенный список для специальной группы
                special_catch_commands = ["поймаю", "ловите", "захват", "беру", "моё", "мой", 
                                         "хочу", "нужен", "забираю", "словить", "словлю", 
                                         "ловушка", "выбираю", "я выбираю тебя", "покебол",
                                         "ловлю", "поймать", "catch", "ловить", "схватить", "ловля", 
                                         "поймал", "лови его", "хватай", "лови", "бросить покебол"]
                
                # Более либеральная проверка для этой группы
                if any(catch_word in message_text for catch_word in special_catch_commands):
                    # Продолжаем ловлю в специальной группе
                    logger.info(f"[ГРУППА -1002435502062] Пользователь {user_id} пытается поймать покемона командой '{message_text}'")
                    pass
                else:
                    # Сообщение не подходит для ловли даже в специальной группе
                    logger.info(f"[ГРУППА -1002435502062] Сообщение '{message_text}' не подходит для ловли")
                    return
            # Обычные группы
            elif (message_text == "ловлю" or 
                message_text == "поймать" or 
                message_text == "catch" or
                message_text == "ловить" or
                message_text == "схватить"):
                # Продолжаем ловлю в обычном групповом чате
                logger.info(f"Пользователь {user_id} пытается поймать покемона в групповом чате командой '{message_text}'")
                pass
            else:
                # Для обычного группового чата, но сообщение не подходит для ловли
                logger.info(f"Сообщение '{message_text}' в чате {chat_id} не подходит для ловли")
                return
        else:
            # Другие типы чатов или сообщение отсутствует
            logger.info(f"Неподходящий тип чата или сообщение для ловли покемона")
            return
    # Для личных сообщений возможен случайный спавн покемона
    elif chat_type == 'private':
        # Случайный спавн с 5% вероятностью в личных чатах
        if random.random() < 0.05:
            logger.info(f"Случайный спавн покемона в личном чате {chat_id}")
            await spawn_wild_pokemon(update, context)
        return
    # В групповых чатах не обрабатываем другие сообщения
    else:
        return
    
    # A wild Pokemon is available, attempt to catch it
    wild_pokemon = get_wild_pokemon(chat_id)
    pokemon_data = wild_pokemon["data"]
    pokemon_name = pokemon_data["name"]
    
    # Mark the Pokemon as caught
    mark_wild_pokemon_caught(chat_id)
    
    # Create a Pokemon object
    pokemon = Pokemon.create_from_data(pokemon_data)
    
    # Get the user
    user = get_user(user_id)
    
    # Check if the catch is successful (based on Pokemon rarity, user's level, etc.)
    # Для специальной группы -1002435502062 повышаем шанс поимки
    if chat_id == -1002435502062:
        logger.info(f"[ГРУППА -1002435502062] Повышенный шанс поимки покемона для пользователя {user_id}")
        catch_success = calculate_catch_success(user, pokemon, special_group=True)
    else:
        catch_success = calculate_catch_success(user, pokemon)
    
    if catch_success:
        # Add the Pokemon to the user's collection
        if add_pokemon_to_user(user_id, pokemon):
            await update.message.reply_text(
                f"🎉 Поздравляем, {update.effective_user.first_name}!\n\n"
                f"Вы поймали **{pokemon_name.capitalize()}**!\n"
                f"CP: {pokemon.calculate_cp()}\n\n"
                f"Покемон добавлен в вашу коллекцию. Используйте /pokedex для просмотра ваших Покемонов.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"Вы поймали **{pokemon_name.capitalize()}**, но у вас уже есть {config.MAX_SAME_POKEMON} таких!\n\n"
                f"Попробуйте эволюционировать их с помощью /evolution {pokemon_name}",
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(
            f"О нет! **{pokemon_name.capitalize()}** вырвался и убежал!\n\n"
            f"Попробуйте использовать лучшие Покеболы из /shop, чтобы увеличить ваш шанс поимки.",
            parse_mode="Markdown"
        )
    
    # Clear the wild Pokemon
    clear_wild_pokemon(chat_id)

def calculate_catch_success(user, pokemon, special_group=False):
    """Calculate whether a catch attempt succeeds."""
    # Base catch rate (50%)
    base_catch_rate = 0.5
    
    # Для специальной группы увеличиваем базовый шанс до 65%
    if special_group:
        base_catch_rate = 0.65
        logger.info(f"[ГРУППА -1002435502062] Увеличен базовый шанс поимки до {base_catch_rate * 100}%")
    
    # Adjust based on Pokemon rarity/CP
    cp = pokemon.calculate_cp()
    cp_factor = max(0.1, 1 - (cp / 1000))  # Higher CP means lower chance
    
    # Для специальной группы уменьшаем штраф за высокий CP
    if special_group and cp_factor < 0.2:
        cp_factor = 0.2
        logger.info(f"[ГРУППА -1002435502062] Уменьшен штраф за высокий CP до {cp_factor}")
    
    # Adjust based on user's league
    league_bonus = (user.league - 1) * 0.05  # 5% bonus per league
    
    # Для специальной группы увеличиваем бонус за лигу вдвое
    if special_group:
        league_bonus *= 2
        logger.info(f"[ГРУППА -1002435502062] Удвоен бонус за лигу: {league_bonus}")
    
    # Adjust based on Pokeballs
    pokeball_bonus = 0
    for ball_id, count in user.pokeballs.items():
        if count > 0:
            # Use the best available Pokeball
            ball_data = config.POKEBALLS.get(ball_id, {})
            pokeball_bonus = ball_data.get("catch_rate_bonus", 0)
            
            # Для специальной группы увеличиваем бонус от покеболов
            if special_group:
                pokeball_bonus *= 1.5
                logger.info(f"[ГРУППА -1002435502062] Увеличен бонус от покебола в 1.5 раза: {pokeball_bonus}")
            
            # Remove one Pokeball from inventory
            user.pokeballs[ball_id] -= 1
            if user.pokeballs[ball_id] <= 0:
                del user.pokeballs[ball_id]
            
            save_user(user)
            break
    
    # Calculate final catch rate
    catch_rate = min(0.95, base_catch_rate + cp_factor + league_bonus + pokeball_bonus)
    
    # Для специальной группы добавляем минимальный порог шанса поимки
    if special_group and catch_rate < 0.4:
        catch_rate = 0.4
        logger.info(f"[ГРУППА -1002435502062] Установлен минимальный порог шанса поимки: {catch_rate}")
    
    # Если это специальная группа, логируем финальный шанс
    if special_group:
        logger.info(f"[ГРУППА -1002435502062] Финальный шанс поимки: {catch_rate * 100}%")
    
    # Return whether the catch succeeds
    return random.random() <= catch_rate
