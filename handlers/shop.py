import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from storage import get_user, save_user, use_promocode
import config

logger = logging.getLogger(__name__)

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /shop command - show the shop."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    # Show shop categories
    keyboard = [
        [InlineKeyboardButton("🔴 Покеболы", callback_data="shop_category_pokeballs")],
        [InlineKeyboardButton("👨‍🏫 Тренеры", callback_data="shop_category_trainers")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🛒 *Магазин Покемонов*\n\n"
        f"Ваш баланс: {user.balance} монет\n\n"
        f"Выберите категорию:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle shop-related callback queries."""
    query = update.callback_query
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    try:
        # Extract the action from the callback data
        parts = query.data.split("_")
        action = parts[1]
        
        await query.answer()
        
        if action == "category":
            # Show items in a category
            category = parts[2]
            await show_shop_category(query, context, user, category)
            
        elif action == "buy":
            # Buy an item
            category = parts[2]
            item_id = parts[3]
            
            if category == "pokeballs":
                # Проверяем, есть ли в callback_data количество покеболов
                if len(parts) > 4:
                    quantity = int(parts[4])
                    await buy_pokeball(query, context, user, item_id, quantity)
                else:
                    await buy_pokeball(query, context, user, item_id, 1)
            elif category == "trainers":
                await buy_trainer(query, context, user, item_id)
            
        elif action == "back":
            # Go back to the main shop menu
            await shop_callback_reset(query, user)
            
    except Exception as e:
        logger.error(f"Ошибка в обратном вызове магазина: {e}")
        await query.edit_message_text(f"Произошла ошибка: {str(e)}")

async def shop_callback_reset(query, user):
    """Reset to the main shop menu."""
    # Show shop categories
    keyboard = [
        [InlineKeyboardButton("🔴 Покеболы", callback_data="shop_category_pokeballs")],
        [InlineKeyboardButton("👨‍🏫 Тренеры", callback_data="shop_category_trainers")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🛒 *Магазин Покемонов*\n\n"
        f"Ваш баланс: {user.balance} монет\n\n"
        f"Выберите категорию:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def show_shop_category(query, context, user, category):
    """Show items in a shop category."""
    if category == "pokeballs":
        # Show Pokeballs
        message = f"🔴 *Покеболы*\n\nВаш баланс: {user.balance} монет\n\n"
        
        for ball_id, ball_data in config.POKEBALLS.items():
            message += f"{ball_data['name']}: {ball_data['cost']} монет\n"
            message += f"Бонус к шансу поимки: +{int(ball_data['catch_rate_bonus'] * 100)}%\n\n"
        
        keyboard = []
        for ball_id, ball_data in config.POKEBALLS.items():
            # Кнопки для покупки разного количества
            row = [
                InlineKeyboardButton(
                    f"1× {ball_data['name']}",
                    callback_data=f"shop_buy_pokeballs_{ball_id}_1"
                ),
                InlineKeyboardButton(
                    f"5× {ball_data['name']}",
                    callback_data=f"shop_buy_pokeballs_{ball_id}_5"
                )
            ]
            keyboard.append(row)
            
            row2 = [
                InlineKeyboardButton(
                    f"10× {ball_data['name']}",
                    callback_data=f"shop_buy_pokeballs_{ball_id}_10"
                ),
                InlineKeyboardButton(
                    f"25× {ball_data['name']}",
                    callback_data=f"shop_buy_pokeballs_{ball_id}_25"
                )
            ]
            keyboard.append(row2)
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="shop_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif category == "trainers":
        # Show Trainers
        message = f"👨‍🏫 *Тренеры*\n\nВаш баланс: {user.balance} монет\n\n"
        
        for trainer_id, trainer_data in config.TRAINERS.items():
            # Skip SARNER if requirements are not met
            if trainer_id == "sarner":
                league_req = trainer_data.get("requirements", {}).get("league", 0)
                pokemon_req = trainer_data.get("requirements", {}).get("pokemon", [])
                
                if user.league < league_req:
                    continue
                
                # Check if user has all required Pokemon
                has_all_pokemon = True
                for pokemon_name in pokemon_req:
                    if not any(p.name.lower() == pokemon_name.lower() for p in user.pokemons):
                        has_all_pokemon = False
                        break
                
                if not has_all_pokemon:
                    continue
            
            # Display trainer info
            message += f"{trainer_data['name']}: {trainer_data['cost']} монет\n"
            message += f"Бонус силы: +{int(trainer_data.get('power_bonus', 0) * 100)}%\n"
            
            if "attack_bonus" in trainer_data:
                message += f"Бонус атаки: +{int(trainer_data['attack_bonus'] * 100)}%\n"
            
            if "health_bonus" in trainer_data:
                message += f"Бонус здоровья: +{int(trainer_data['health_bonus'] * 100)}%\n"
            
            if "coin_reward" in trainer_data:
                message += f"Награда в монетах: {trainer_data['coin_reward']}\n"
            
            if "requirements" in trainer_data:
                req = trainer_data["requirements"]
                if "league" in req:
                    message += f"Требуемая лига: {req['league']}\n"
                if "pokemon" in req:
                    message += f"Требуемые Покемоны: {', '.join(p.capitalize() for p in req['pokemon'])}\n"
            
            message += "\n"
        
        keyboard = []
        for trainer_id, trainer_data in config.TRAINERS.items():
            # Skip SARNER if requirements are not met
            if trainer_id == "sarner":
                league_req = trainer_data.get("requirements", {}).get("league", 0)
                pokemon_req = trainer_data.get("requirements", {}).get("pokemon", [])
                
                if user.league < league_req:
                    continue
                
                # Check if user has all required Pokemon
                has_all_pokemon = True
                for pokemon_name in pokemon_req:
                    if not any(p.name.lower() == pokemon_name.lower() for p in user.pokemons):
                        has_all_pokemon = False
                        break
                
                if not has_all_pokemon:
                    continue
            
            # Add button for the trainer
            keyboard.append([
                InlineKeyboardButton(
                    f"Купить {trainer_data['name']} ({trainer_data['cost']} монет)",
                    callback_data=f"shop_buy_trainers_{trainer_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="shop_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def buy_pokeball(query, context, user, ball_id, quantity=1):
    """Buy multiple Pokeballs.
    
    Args:
        query: The callback query
        context: The context
        user: The user buying the Pokeball
        ball_id: The ID of the Pokeball to buy
        quantity: The number of Pokeballs to buy (default: 1)
    """
    if ball_id not in config.POKEBALLS:
        await query.edit_message_text("Выбран неверный Покебол.")
        return
    
    ball_data = config.POKEBALLS[ball_id]
    unit_cost = ball_data["cost"]
    total_cost = unit_cost * quantity
    
    # Проверка наличия достаточного количества монет
    if user.balance < total_cost:
        await query.edit_message_text(
            f"❌ У вас недостаточно монет для покупки {quantity}× {ball_data['name']}.\n\n"
            f"Ваш баланс: {user.balance} монет\n"
            f"Стоимость: {total_cost} монет ({unit_cost} × {quantity})",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="shop_category_pokeballs")
            ]])
        )
        return
    
    # Вычитаем стоимость и добавляем покеболы
    user.balance -= total_cost
    
    # Добавляем покеболы в инвентарь пользователя
    user.pokeballs[ball_id] = user.pokeballs.get(ball_id, 0) + quantity
    
    # Сохраняем изменения
    save_user(user)
    
    # Формируем правильное склонение слова "монета"
    coin_form = "монет"
    if total_cost % 10 == 1 and total_cost % 100 != 11:
        coin_form = "монету"
    elif 2 <= total_cost % 10 <= 4 and (total_cost % 100 < 10 or total_cost % 100 >= 20):
        coin_form = "монеты"
    
    # Формируем правильное склонение слова "покебол"
    ball_form = ball_data["name"]
    
    await query.edit_message_text(
        f"✅ Вы купили {quantity}× {ball_data['name']} за {total_cost} {coin_form}!\n\n"
        f"Ваш новый баланс: {user.balance} монет\n"
        f"Теперь у вас {user.pokeballs.get(ball_id, 0)} {ball_form}.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Назад", callback_data="shop_category_pokeballs")
        ]])
    )

async def buy_trainer(query, context, user, trainer_id):
    """Buy a Trainer."""
    if trainer_id not in config.TRAINERS:
        await query.edit_message_text("Выбран неверный Тренер.")
        return
    
    trainer_data = config.TRAINERS[trainer_id]
    cost = trainer_data["cost"]
    
    # Check if the user already has this trainer
    if user.trainer and user.trainer.lower() == trainer_id:
        # User already has this trainer, check if they can upgrade it
        if "upgrade_cost" in trainer_data:
            upgrade_cost = trainer_data["upgrade_cost"]
            if user.balance < upgrade_cost:
                await query.edit_message_text(
                    f"❌ У вас недостаточно монет для улучшения {trainer_data['name']}.\n\n"
                    f"Ваш баланс: {user.balance} монет\n"
                    f"Стоимость улучшения: {upgrade_cost} монет",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Назад", callback_data="shop_category_trainers")
                    ]])
                )
                return
            
            # Deduct the cost and upgrade the trainer
            user.balance -= upgrade_cost
            user.trainer_level += 1
            
            # Save the user
            save_user(user)
            
            await query.edit_message_text(
                f"✅ Вы улучшили {trainer_data['name']} до уровня {user.trainer_level} за {upgrade_cost} монет!\n\n"
                f"Ваш новый баланс: {user.balance} монет",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Назад", callback_data="shop_category_trainers")
                ]])
            )
            return
        else:
            await query.edit_message_text(
                f"❌ У вас уже есть {trainer_data['name']} и вы не можете улучшить его дальше.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Назад", callback_data="shop_category_trainers")
                ]])
            )
            return
    
    if user.balance < cost:
        await query.edit_message_text(
            f"❌ У вас недостаточно монет для покупки {trainer_data['name']}.\n\n"
            f"Ваш баланс: {user.balance} монет\n"
            f"Стоимость: {cost} монет",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="shop_category_trainers")
            ]])
        )
        return
    
    # Check if user meets the requirements for special trainers
    if "requirements" in trainer_data:
        req = trainer_data["requirements"]
        if "league" in req and user.league < req["league"]:
            await query.edit_message_text(
                f"❌ Вам нужно быть в Лиге {req['league']} для покупки {trainer_data['name']}.\n\n"
                f"Ваша текущая лига: {user.league}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Назад", callback_data="shop_category_trainers")
                ]])
            )
            return
        
        if "pokemon" in req:
            missing_pokemon = []
            for pokemon_name in req["pokemon"]:
                if not any(p.name.lower() == pokemon_name.lower() for p in user.pokemons):
                    missing_pokemon.append(pokemon_name.capitalize())
            
            if missing_pokemon:
                await query.edit_message_text(
                    f"❌ У вас нет следующих Покемонов, необходимых для покупки {trainer_data['name']}:\n\n"
                    f"{', '.join(missing_pokemon)}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Назад", callback_data="shop_category_trainers")
                    ]])
                )
                return
    
    # Deduct the cost and add the trainer
    user.balance -= cost
    user.trainer = trainer_id
    user.trainer_level = 1
    
    # If the trainer gives a coin reward, add it
    coin_reward_message = ""
    if "coin_reward" in trainer_data:
        coin_reward = trainer_data["coin_reward"]
        user.balance += coin_reward
        coin_reward_message = f"\n\n✨ Бонус! Вы получили {coin_reward} монет!"
    
    # Save the user
    save_user(user)
    
    await query.edit_message_text(
        f"✅ Вы купили {trainer_data['name']} за {cost} монет!{coin_reward_message}\n\n"
        f"Ваш новый баланс: {user.balance} монет",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Назад", callback_data="shop_category_trainers")
        ]])
    )

async def promocode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /promocode command - redeem a promocode."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    # Check if the command has arguments
    if not context.args:
        await update.message.reply_text(
            "Пожалуйста, укажите промокод для активации. Использование: /promocode ВАШКОД",
            parse_mode="Markdown"
        )
        return
    
    # Get the promocode
    code = context.args[0]
    
    # Try to use the promocode
    success, reward_type, reward_description = use_promocode(user_id, code)
    
    if success:
        # Формируем сообщение в зависимости от типа награды
        message = f"✅ Промокод *{code}* успешно активирован!\n\n"
        
        if reward_type == "coins":
            message += f"Вы получили {reward_description}.\n"
            message += f"Ваш новый баланс: {user.balance} монет"
        
        elif reward_type == "pokemon":
            message += f"Вы получили {reward_description}!"
        
        elif reward_type == "trainer":
            message += f"Вы получили {reward_description}!"
        
        elif reward_type == "custom_pokemon":
            message += f"Вы получили {reward_description}!"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"❌ Неверный промокод *{code}*, истек срок действия, или вы уже использовали его.",
            parse_mode="Markdown"
        )
