import logging
import uuid
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
from storage import (
    get_user, save_user, create_promocode, add_custom_pokemon, add_pokemon_to_user,
    get_all_users, get_custom_pokemon
)
from models.pokemon import Pokemon
from pokemon_api import get_pokemon_data_sync

logger = logging.getLogger(__name__)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /admin command - show admin panel if user is an admin."""
    user_id = update.effective_user.id
    
    # Check if the user is an admin
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к панели администратора.")
        return
    
    # Create the admin panel keyboard
    keyboard = [
        [InlineKeyboardButton("🧠 Создать уникального покемона", callback_data="admin_create_pokemon")],
        [InlineKeyboardButton("🎁 Выдать покемона игроку", callback_data="admin_give_pokemon")],
        [InlineKeyboardButton("💰 Изменить баланс пользователя", callback_data="admin_change_balance")],
        [InlineKeyboardButton("🎁 Создать промокод", callback_data="admin_create_promocode")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👑 *Панель администратора*\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from the admin panel."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Check if the user is an admin
    if user_id not in config.ADMIN_IDS:
        await query.answer("⛔ У вас нет доступа к панели администратора.")
        return
    
    await query.answer()
    
    action = query.data
    
    if action == "admin_create_pokemon":
        # Start the process of creating a custom Pokemon
        context.user_data["admin_state"] = "create_pokemon_name"
        await query.edit_message_text(
            "🧠 *Создание уникального покемона*\n\n"
            "Введите название покемона:",
            parse_mode="Markdown"
        )
    
    elif action == "admin_change_balance":
        # Start the process of changing a user's balance
        context.user_data["admin_state"] = "change_balance_user_id"
        await query.edit_message_text(
            "💰 *Изменение баланса пользователя*\n\n"
            "Введите ID пользователя:",
            parse_mode="Markdown"
        )
    
    elif action == "admin_create_promocode":
        # Start the process of creating a promocode
        context.user_data["admin_state"] = "create_promocode_code"
        await query.edit_message_text(
            "🎁 *Создание промокода*\n\n"
            "Введите код промокода:",
            parse_mode="Markdown"
        )
    
    elif action == "admin_give_pokemon":
        # Start the process of giving a Pokemon to a user
        context.user_data["admin_state"] = "give_pokemon_username"
        await query.edit_message_text(
            "🎁 *Выдача покемона игроку*\n\n"
            "Введите @username пользователя Telegram (начиная с символа @):",
            parse_mode="Markdown"
        )
        
    elif action == "admin_back":
        # Go back to the main admin panel
        keyboard = [
            [InlineKeyboardButton("🧠 Создать уникального покемона", callback_data="admin_create_pokemon")],
            [InlineKeyboardButton("🎁 Выдать покемона игроку", callback_data="admin_give_pokemon")],
            [InlineKeyboardButton("💰 Изменить баланс пользователя", callback_data="admin_change_balance")],
            [InlineKeyboardButton("🎁 Создать промокод", callback_data="admin_create_promocode")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👑 *Панель администратора*\n\n"
            "Выберите действие:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    # Обработка выбора типа награды для промокода
    elif action.startswith("admin_promocode_type_"):
        reward_type = action.replace("admin_promocode_type_", "")
        
        if reward_type == "coins":
            # Запрашиваем количество монет
            context.user_data["admin_state"] = "create_promocode_reward_coins"
            
            await query.edit_message_text(
                "💰 *Создание промокода - Монеты*\n\n"
                "Введите количество монет для награды:",
                parse_mode="Markdown"
            )
            
        elif reward_type == "pokemon":
            # Запрашиваем название покемона
            context.user_data["admin_state"] = "create_promocode_reward_pokemon"
            
            await query.edit_message_text(
                "🐲 *Создание промокода - Покемон*\n\n"
                "Введите название покемона для награды:",
                parse_mode="Markdown"
            )
            
        elif reward_type == "trainer":
            # Запрашиваем ID тренера
            context.user_data["admin_state"] = "create_promocode_reward_trainer"
            
            # Формируем список доступных тренеров
            trainer_list = "\n".join([f"- {trainer_id}: {trainer['name']}" for trainer_id, trainer in config.TRAINERS.items()])
            
            await query.edit_message_text(
                "👨‍🏫 *Создание промокода - Тренер*\n\n"
                f"Доступные тренеры:\n{trainer_list}\n\n"
                "Введите ID тренера из списка:",
                parse_mode="Markdown"
            )
            
        elif reward_type == "custom_pokemon":
            # Запрашиваем ID уникального покемона
            context.user_data["admin_state"] = "create_promocode_reward_custom_pokemon"
            
            await query.edit_message_text(
                "🧠 *Создание промокода - Уникальный покемон*\n\n"
                "Введите ID уникального покемона для награды:",
                parse_mode="Markdown"
            )
    
    # Обработка выбора количества покемонов для промокода
    elif action.startswith("admin_promocode_pokemon_amount_"):
        amount = int(action.replace("admin_promocode_pokemon_amount_", ""))
        pokemon_name = context.user_data["promocode_pokemon_name"]
        code = context.user_data["promocode_code"]
        
        # Создаем промокод с указанным количеством покемонов
        promocode = create_promocode(
            code=code, 
            reward_type="pokemon", 
            reward_value=pokemon_name, 
            reward_amount=amount,
            created_by=user_id,
            description=f"Промокод на получение покемона {pokemon_name.capitalize()} (x{amount})"
        )
        
        await query.edit_message_text(
            f"✅ Промокод *{code}* успешно создан!\n\n"
            f"Тип награды: Покемон\n"
            f"Покемон: {pokemon_name.capitalize()}\n"
            f"Количество: {amount}\n"
            f"Создан администратором: {user_id}",
            parse_mode="Markdown"
        )
        
        # Clear the admin state
        del context.user_data["admin_state"]
        del context.user_data["promocode_code"]
        del context.user_data["promocode_pokemon_name"]

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle messages in admin mode and return whether the message was handled."""
    user_id = update.effective_user.id
    
    # Check if the user is in admin mode
    if user_id not in config.ADMIN_IDS or "admin_state" not in context.user_data:
        return False
    
    admin_state = context.user_data["admin_state"]
    message_text = update.message.text
    
    if admin_state == "create_pokemon_name":
        # Save the Pokemon name
        context.user_data["custom_pokemon_name"] = message_text
        context.user_data["admin_state"] = "create_pokemon_type"
        
        await update.message.reply_text(
            f"Название покемона: *{message_text}*\n\n"
            "Введите тип(ы) покемона (через запятую, например, 'огонь, летающий'):",
            parse_mode="Markdown"
        )
        return True
        
    elif admin_state == "create_pokemon_type":
        # Save the Pokemon type
        context.user_data["custom_pokemon_type"] = message_text
        context.user_data["admin_state"] = "create_pokemon_image"
        
        await update.message.reply_text(
            f"Тип покемона: *{message_text}*\n\n"
            "Введите URL изображения покемона (или просто нажмите Enter, чтобы оставить пустым):",
            parse_mode="Markdown"
        )
        return True
        
    elif admin_state == "create_pokemon_image":
        # Save the Pokemon image URL
        context.user_data["custom_pokemon_image_url"] = message_text if message_text != "" else None
        context.user_data["admin_state"] = "create_pokemon_stats"
        
        await update.message.reply_text(
            "Введите характеристики покемона в формате атака,защита,озд (например, 100,80,150):",
            parse_mode="Markdown"
        )
        return True
            
    elif admin_state == "create_pokemon_stats":
        # Parse the stats
        try:
            stats = message_text.split(",")
            attack = int(stats[0].strip())
            defense = int(stats[1].strip())
            hp = int(stats[2].strip())
            
            # Create the custom Pokemon
            name = context.user_data["custom_pokemon_name"]
            types = [t.strip() for t in context.user_data["custom_pokemon_type"].split(",")]
            image_url = context.user_data["custom_pokemon_image_url"]
            
            pokemon_data = {
                "id": str(uuid.uuid4()),
                "name": name,
                "types": types,
                "image_url": image_url,
                "stats": {
                    "attack": attack,
                    "defense": defense,
                    "hp": hp
                },
                "custom": True
            }
            
            # Сохраняем пользовательского покемона
            pokemon_id = add_custom_pokemon(pokemon_data)
            
            # Создаем объект покемона для добавления в коллекцию администратора
            custom_pokemon = Pokemon.create_custom_pokemon(
                name=name,
                types=types,
                attack=attack,
                defense=defense,
                hp=hp,
                image_url=image_url
            )
            
            # Добавляем покемона администратору (3 штуки)
            admin_msg = ""
            admin_user = get_user(user_id)
            
            # Добавляем 3 копии покемона администратору
            for i in range(3):
                # Обходим ограничение на максимальное количество одинаковых покемонов
                admin_user.pokemons.append(custom_pokemon)
                admin_user.caught_pokemon_count += 1
            
            # Сохраняем обновленные данные администратора
            save_user(admin_user)
            admin_msg = "\n\n✅ Покемон также был добавлен в вашу коллекцию (3 шт.)!"
            
            await update.message.reply_text(
                f"✅ Пользовательский покемон *{name}* успешно создан!\n\n"
                f"ID: `{pokemon_id}`\n"
                f"Тип: {', '.join(types)}\n"
                f"Характеристики: Атака {attack}, Защита {defense}, ОЗ {hp}{admin_msg}",
                parse_mode="Markdown"
            )
            
            # Clear the admin state
            del context.user_data["admin_state"]
            del context.user_data["custom_pokemon_name"]
            del context.user_data["custom_pokemon_type"]
            del context.user_data["custom_pokemon_image_url"]
            
        except (ValueError, IndexError) as e:
            await update.message.reply_text(
                f"❌ Неверный формат характеристик: {str(e)}\n\n"
                "Пожалуйста, введите характеристики в формате атака,защита,озд (например, 100,80,150):",
                parse_mode="Markdown"
            )
        return True
    
    elif admin_state == "change_balance_user_id":
        # Parse the user ID
        try:
            target_user_id = int(message_text)
            target_user = get_user(target_user_id)
            
            if target_user is None:
                await update.message.reply_text(
                    "❌ Пользователь с указанным ID не найден.\n\n"
                    "Введите ID существующего пользователя:",
                    parse_mode="Markdown"
                )
                return True
            
            context.user_data["target_user_id"] = target_user_id
            context.user_data["admin_state"] = "change_balance_amount"
            
            await update.message.reply_text(
                f"Пользователь найден: ID {target_user_id}\n"
                f"Текущий баланс: {target_user.balance} монет\n\n"
                "Введите новый баланс или изменение (используйте + или - для изменения):",
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат ID пользователя. Введите числовой ID:",
                parse_mode="Markdown"
            )
        return True
    
    elif admin_state == "change_balance_amount":
        # Parse the balance change
        try:
            target_user_id = context.user_data["target_user_id"]
            target_user = get_user(target_user_id)
            
            if message_text.startswith("+") or message_text.startswith("-"):
                # Relative change
                change = int(message_text)
                new_balance = target_user.balance + change
                
                if new_balance < 0:
                    new_balance = 0
                
                action = "увеличен" if change > 0 else "уменьшен"
                change_abs = abs(change)
            else:
                # Absolute change
                new_balance = int(message_text)
                
                if new_balance < 0:
                    new_balance = 0
                
                change = new_balance - target_user.balance
                action = "изменен"
                change_abs = abs(change)
            
            # Update the user's balance
            target_user.balance = new_balance
            save_user(target_user)
            
            if change != 0:
                await update.message.reply_text(
                    f"✅ Баланс пользователя (ID {target_user_id}) {action} на {change_abs} монет.\n"
                    f"Новый баланс: {new_balance} монет.",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"ℹ️ Баланс пользователя (ID {target_user_id}) не изменился.\n"
                    f"Текущий баланс: {new_balance} монет.",
                    parse_mode="Markdown"
                )
            
            # Clear the admin state
            del context.user_data["admin_state"]
            del context.user_data["target_user_id"]
            
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат баланса. Введите число или число с + или -:",
                parse_mode="Markdown"
            )
        return True
    
    elif admin_state == "create_promocode_code":
        # Save the promocode
        context.user_data["promocode_code"] = message_text
        context.user_data["admin_state"] = "create_promocode_type"
        
        # Создаем клавиатуру с выбором типа награды
        keyboard = [
            [InlineKeyboardButton("💰 Монеты", callback_data="admin_promocode_type_coins")],
            [InlineKeyboardButton("🐲 Обычный покемон", callback_data="admin_promocode_type_pokemon")],
            [InlineKeyboardButton("👨‍🏫 Тренер", callback_data="admin_promocode_type_trainer")],
            [InlineKeyboardButton("🧠 Уникальный покемон", callback_data="admin_promocode_type_custom_pokemon")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Код промокода: *{message_text}*\n\n"
            "Выберите тип награды:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return True
        
    elif admin_state == "create_promocode_reward_coins":
        # Parse the reward
        try:
            reward_value = int(message_text)
            
            if reward_value <= 0:
                await update.message.reply_text(
                    "❌ Награда должна быть положительным числом.\n\n"
                    "Введите положительное число:",
                    parse_mode="Markdown"
                )
                return True
            
            code = context.user_data["promocode_code"]
            
            # Create the promocode
            promocode = create_promocode(
                code=code, 
                reward_type="coins", 
                reward_value=reward_value, 
                created_by=user_id,
                description=f"Промокод на {reward_value} монет"
            )
            
            await update.message.reply_text(
                f"✅ Промокод *{code}* успешно создан!\n\n"
                f"Тип награды: Монеты\n"
                f"Величина: {reward_value} монет\n"
                f"Создан администратором: {user_id}",
                parse_mode="Markdown"
            )
            
            # Clear the admin state
            del context.user_data["admin_state"]
            del context.user_data["promocode_code"]
            
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат награды. Введите число:",
                parse_mode="Markdown"
            )
        return True
    
    elif admin_state == "create_promocode_reward_pokemon":
        # Получаем название покемона и проверяем его существование
        pokemon_name = message_text.strip().lower()
        
        # Проверка на существование покемона
        pokemon_data = get_pokemon_data_sync(pokemon_name)
        if not pokemon_data:
            await update.message.reply_text(
                f"❌ Покемон '{pokemon_name}' не найден.\n\n"
                "Введите корректное имя покемона:",
                parse_mode="Markdown"
            )
            return True
            
        # Создаем клавиатуру с выбором количества
        keyboard = [
            [
                InlineKeyboardButton("1", callback_data="admin_promocode_pokemon_amount_1"),
                InlineKeyboardButton("2", callback_data="admin_promocode_pokemon_amount_2"),
                InlineKeyboardButton("3", callback_data="admin_promocode_pokemon_amount_3")
            ],
            [
                InlineKeyboardButton("5", callback_data="admin_promocode_pokemon_amount_5"),
                InlineKeyboardButton("10", callback_data="admin_promocode_pokemon_amount_10")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Сохраняем данные покемона
        context.user_data["promocode_pokemon_name"] = pokemon_name
        
        await update.message.reply_text(
            f"Выбран покемон: *{pokemon_name.capitalize()}*\n\n"
            "Выберите количество покемонов для промокода:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return True
        
    elif admin_state == "create_promocode_reward_trainer":
        # Проверяем существование тренера
        trainer_id = message_text.strip().lower()
        
        if trainer_id not in config.TRAINERS:
            # Покажем список доступных тренеров
            trainer_list = "\n".join([f"- {trainer_id}" for trainer_id in config.TRAINERS.keys()])
            
            await update.message.reply_text(
                f"❌ Тренер '{trainer_id}' не найден.\n\n"
                f"Доступные тренеры:\n{trainer_list}\n\n"
                "Введите ID тренера из списка:",
                parse_mode="Markdown"
            )
            return True
            
        code = context.user_data["promocode_code"]
        trainer_name = config.TRAINERS[trainer_id]["name"]
        
        # Создаем промокод для тренера
        promocode = create_promocode(
            code=code, 
            reward_type="trainer", 
            reward_value=trainer_id, 
            created_by=user_id,
            description=f"Промокод на получение тренера {trainer_name}"
        )
        
        await update.message.reply_text(
            f"✅ Промокод *{code}* успешно создан!\n\n"
            f"Тип награды: Тренер\n"
            f"Тренер: {trainer_name}\n"
            f"Создан администратором: {user_id}",
            parse_mode="Markdown"
        )
        
        # Clear the admin state
        del context.user_data["admin_state"]
        del context.user_data["promocode_code"]
        return True
        
    elif admin_state == "create_promocode_reward_custom_pokemon":
        # Получаем ID уникального покемона
        custom_pokemon_id = message_text.strip()
        
        # Проверка на существование уникального покемона
        pokemon_data = get_custom_pokemon(custom_pokemon_id)
        if not pokemon_data:
            await update.message.reply_text(
                f"❌ Уникальный покемон с ID '{custom_pokemon_id}' не найден.\n\n"
                "Введите корректный ID уникального покемона:",
                parse_mode="Markdown"
            )
            return True
            
        code = context.user_data["promocode_code"]
        pokemon_name = pokemon_data["name"]
        
        # Создаем промокод для уникального покемона
        promocode = create_promocode(
            code=code, 
            reward_type="custom_pokemon", 
            reward_value=custom_pokemon_id, 
            created_by=user_id,
            description=f"Промокод на получение уникального покемона {pokemon_name}"
        )
        
        await update.message.reply_text(
            f"✅ Промокод *{code}* успешно создан!\n\n"
            f"Тип награды: Уникальный покемон\n"
            f"Покемон: {pokemon_name} (ID: {custom_pokemon_id})\n"
            f"Создан администратором: {user_id}",
            parse_mode="Markdown"
        )
        
        # Clear the admin state
        del context.user_data["admin_state"]
        del context.user_data["promocode_code"]
        return True
        
    elif admin_state == "give_pokemon_username":
        # Проверяем формат username
        if not message_text.startswith('@'):
            await update.message.reply_text(
                "❌ Неверный формат username. Введите @username пользователя Telegram:",
                parse_mode="Markdown"
            )
            return True
            
        username = message_text[1:]  # Удаляем символ @
        context.user_data["target_username"] = username
        
        # Поиск пользователя по username
        found_user = None
        try:
            # Загружаем всех пользователей
            all_users = get_all_users()
            
            for user_id, user_data in all_users.items():
                # Проверяем наличие поля username в данных пользователя
                if hasattr(user_data, 'username') and user_data.username and user_data.username.lower() == username.lower():
                    found_user = user_data
                    context.user_data["target_user_id"] = int(user_id)
                    break
                    
            if found_user is None:
                await update.message.reply_text(
                    f"❌ Пользователь с username @{username} не найден в базе данных бота.\n\n"
                    "Пользователь должен хотя бы раз начать общение с ботом командой /start",
                    parse_mode="Markdown"
                )
                return True
                
            # Переходим к выбору покемона для выдачи
            context.user_data["admin_state"] = "give_pokemon_name"
            
            await update.message.reply_text(
                f"✅ Пользователь @{username} найден!\n\n"
                "Введите название покемона, которого вы хотите выдать пользователю\n"
                "(можно ввести несколько имен через запятую для выдачи нескольких покемонов):",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователя: {e}")
            await update.message.reply_text(
                f"❌ Произошла ошибка при поиске пользователя: {str(e)}\n\n"
                "Пожалуйста, повторите попытку позже.",
                parse_mode="Markdown"
            )
            # Сбрасываем состояние
            del context.user_data["admin_state"]
            if "target_username" in context.user_data:
                del context.user_data["target_username"]
                
        return True
        
    elif admin_state == "give_pokemon_name":
        pokemon_names = [name.strip() for name in message_text.split(',')]
        target_username = context.user_data["target_username"]
        target_user_id = context.user_data["target_user_id"]
        target_user = get_user(target_user_id)
        
        if target_user is None:
            await update.message.reply_text(
                f"❌ Ошибка: пользователь с ID {target_user_id} не найден.",
                parse_mode="Markdown"
            )
            # Сбрасываем состояние
            del context.user_data["admin_state"]
            del context.user_data["target_username"]
            del context.user_data["target_user_id"]
            return True
        
        successful = []
        failed = []
        
        for pokemon_name in pokemon_names:
            try:
                # Получаем данные покемона
                try:
                    # Пытаемся получить данные из API напрямую (асинхронно)
                    from pokemon_api import get_pokemon_data
                    pokemon_data = await get_pokemon_data(pokemon_name.lower())
                    
                    if pokemon_data:
                        # Если данные получены, создаем покемона
                        pokemon = Pokemon.create_from_data(pokemon_data)
                    else:
                        # Проверяем, может быть это кастомный покемон
                        custom_pokemons = get_custom_pokemon(pokemon_name)
                        if custom_pokemons:
                            # Используем первого найденного кастомного покемона
                            pokemon_data = next(iter(custom_pokemons.values()))
                            pokemon = Pokemon.from_dict(pokemon_data)
                        else:
                            pokemon = None
                except Exception as e:
                    logger.error(f"Ошибка при получении данных покемона {pokemon_name}: {e}")
                    custom_pokemons = get_custom_pokemon(pokemon_name)
                    if custom_pokemons:
                        # Используем первого найденного кастомного покемона
                        pokemon_data = next(iter(custom_pokemons.values()))
                        pokemon = Pokemon.from_dict(pokemon_data)
                    else:
                        pokemon = None
                
                if pokemon is None:
                    failed.append(f"{pokemon_name} (не найден)")
                    continue
                
                # Добавляем покемона пользователю
                if add_pokemon_to_user(target_user_id, pokemon):
                    successful.append(pokemon_name)
                else:
                    failed.append(f"{pokemon_name} (ошибка добавления)")
                    
            except Exception as e:
                logger.error(f"Ошибка при выдаче покемона {pokemon_name}: {e}")
                failed.append(f"{pokemon_name} (ошибка: {str(e)})")
        
        # Формируем сообщение о результате
        result_message = f"📊 *Результат выдачи покемонов пользователю @{target_username}:*\n\n"
        
        if successful:
            result_message += "✅ Успешно выдано:\n"
            for name in successful:
                result_message += f"- {name}\n"
        
        if failed:
            if successful:
                result_message += "\n"
            result_message += "❌ Не удалось выдать:\n"
            for name in failed:
                result_message += f"- {name}\n"
        
        await update.message.reply_text(
            result_message,
            parse_mode="Markdown"
        )
        
        # Сбрасываем состояние
        del context.user_data["admin_state"]
        del context.user_data["target_username"]
        del context.user_data["target_user_id"]
        
        return True
    
    return False
