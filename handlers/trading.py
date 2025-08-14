import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from storage import (
    get_user, start_trade, get_trade, add_pokemon_to_trade,
    remove_pokemon_from_trade, confirm_trade, save_user
)

logger = logging.getLogger(__name__)

async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /trade command - initiate a trade with another user."""
    # Check if the command is a reply to another user's message
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "💱 To initiate a trade, reply to another user's message with /trade"
        )
        return
    
    # Get the user IDs
    trader1_id = update.effective_user.id
    trader2_id = update.message.reply_to_message.from_user.id
    
    # Make sure the trade partner is not the bot or the same user
    if trader2_id == context.bot.id:
        await update.message.reply_text("🤖 You can't trade with me!")
        return
    
    if trader1_id == trader2_id:
        await update.message.reply_text("🙄 You can't trade with yourself!")
        return
    
    # Get the users
    trader1 = get_user(trader1_id)
    trader2 = get_user(trader2_id)
    
    # Check if the users have Pokemon
    if not trader1.pokemons:
        await update.message.reply_text("You don't have any Pokemon to trade!")
        return
    
    if not trader2.pokemons:
        await update.message.reply_text("Your trade partner doesn't have any Pokemon to trade!")
        return
    
    # Start a trade
    trade_id = start_trade(trader1_id, trader2_id)
    
    # Store the trade ID in the context
    context.user_data["current_trade"] = trade_id
    
    # Create a keyboard for the trade partner to accept or decline
    keyboard = [
        [
            InlineKeyboardButton("Accept", callback_data=f"trade_accept_{trade_id}"),
            InlineKeyboardButton("Decline", callback_data=f"trade_decline_{trade_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send a message to the trade partner
    trader1_name = update.effective_user.first_name
    await update.message.reply_to_message.reply_text(
        f"💱 {trader1_name} wants to trade Pokemon with you!\n"
        "Do you accept?",
        reply_markup=reply_markup
    )

async def trade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle trade-related callback queries."""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    try:
        # Extract the action and trade ID
        parts = data.split("_")
        action = parts[1]
        trade_id = parts[2] if len(parts) > 2 else None
        
        await query.answer()
        
        if action == "accept" and trade_id:
            # Get the trade
            trade = get_trade(trade_id)
            if not trade:
                await query.edit_message_text("This trade is no longer available.")
                return
            
            # Make sure this user is the trade partner
            if user_id != trade["user2_id"]:
                await query.edit_message_text("This trade request is not for you.")
                return
            
            # Update the trade status
            trade["status"] = "negotiating"
            
            # Get the users
            trader1 = get_user(trade["user1_id"])
            trader2 = get_user(trade["user2_id"])
            
            # Let the initiator know the trade was accepted
            await context.bot.send_message(
                chat_id=trade["user1_id"],
                text=f"🔄 {trader2.get_display_name()} has accepted your trade request!"
            )
            
            # Show trade interface to both users
            await show_trade_interface(context, trade_id, trade["user1_id"])
            await show_trade_interface(context, trade_id, trade["user2_id"])
            
            # Edit the original message
            await query.edit_message_text("You accepted the trade request. Check your private messages to continue the trade.")
            
        elif action == "decline" and trade_id:
            # Get the trade
            trade = get_trade(trade_id)
            if not trade:
                await query.edit_message_text("This trade is no longer available.")
                return
            
            # Make sure this user is the trade partner
            if user_id != trade["user2_id"]:
                await query.edit_message_text("This trade request is not for you.")
                return
            
            # Let the initiator know the trade was declined
            await context.bot.send_message(
                chat_id=trade["user1_id"],
                text=f"😔 {update.effective_user.first_name} has declined your trade request."
            )
            
            await query.edit_message_text("You declined the trade request.")
            
        elif action == "add" and trade_id:
            # Get the trade
            trade = get_trade(trade_id)
            if not trade:
                await query.edit_message_text("This trade is no longer available.")
                return
            
            # Make sure this user is in the trade
            if user_id != trade["user1_id"] and user_id != trade["user2_id"]:
                await query.edit_message_text("This trade is not for you.")
                return
            
            # Set up state to select a Pokemon to add
            context.user_data["trade_state"] = "add_pokemon"
            context.user_data["trade_id"] = trade_id
            
            # Show the user's Pokemon
            await show_pokemon_selection(query, user_id)
            
        elif action == "remove" and trade_id:
            # Get the trade
            trade = get_trade(trade_id)
            if not trade:
                await query.edit_message_text("This trade is no longer available.")
                return
            
            # Make sure this user is in the trade
            if user_id != trade["user1_id"] and user_id != trade["user2_id"]:
                await query.edit_message_text("This trade is not for you.")
                return
            
            # Determine which offer list to use
            offer_list = trade["user1_offer"] if user_id == trade["user1_id"] else trade["user2_offer"]
            
            # Check if there are any Pokemon to remove
            if not offer_list:
                await query.answer("You haven't added any Pokemon to the trade yet.")
                return
            
            # Set up state to select a Pokemon to remove
            context.user_data["trade_state"] = "remove_pokemon"
            context.user_data["trade_id"] = trade_id
            
            # Show the user's offered Pokemon
            await show_offered_pokemon_selection(query, trade, user_id)
            
        elif action == "confirm" and trade_id:
            # Get the trade
            trade = get_trade(trade_id)
            if not trade:
                await query.edit_message_text("This trade is no longer available.")
                return
            
            # Make sure this user is in the trade
            if user_id != trade["user1_id"] and user_id != trade["user2_id"]:
                await query.edit_message_text("This trade is not for you.")
                return
            
            # Confirm the trade for this user
            confirmed = confirm_trade(trade_id, user_id)
            
            if not confirmed:
                await query.answer("Failed to confirm trade.")
                return
            
            # Check if both users have confirmed
            trade = get_trade(trade_id)
            if trade["status"] == "completed":
                # Trade was completed
                await notify_trade_completed(context, trade)
            else:
                # Just this user confirmed
                await query.edit_message_text(
                    "You have confirmed the trade. Waiting for the other trainer to confirm...",
                    reply_markup=create_trade_interface_keyboard(trade, user_id, confirmed=True)
                )
                
                # Notify the other user
                other_user_id = trade["user2_id"] if user_id == trade["user1_id"] else trade["user1_id"]
                await context.bot.send_message(
                    chat_id=other_user_id,
                    text=f"{update.effective_user.first_name} has confirmed the trade. Please confirm to complete the trade."
                )
            
        elif action == "cancel" and trade_id:
            # Get the trade
            trade = get_trade(trade_id)
            if not trade:
                await query.edit_message_text("This trade is no longer available.")
                return
            
            # Make sure this user is in the trade
            if user_id != trade["user1_id"] and user_id != trade["user2_id"]:
                await query.edit_message_text("This trade is not for you.")
                return
            
            # Cancel the trade
            trade["status"] = "cancelled"
            
            # Notify both users
            await query.edit_message_text("You have cancelled the trade.")
            
            other_user_id = trade["user2_id"] if user_id == trade["user1_id"] else trade["user1_id"]
            await context.bot.send_message(
                chat_id=other_user_id,
                text=f"{update.effective_user.first_name} has cancelled the trade."
            )
            
        elif action == "select" and trade_id:
            # This is a Pokemon selection callback
            pokemon_idx = int(parts[3])
            
            # Get the trade
            trade = get_trade(trade_id)
            if not trade:
                await query.edit_message_text("This trade is no longer available.")
                return
            
            # Check the trade state
            trade_state = context.user_data.get("trade_state")
            
            if trade_state == "add_pokemon":
                # Add the selected Pokemon to the trade
                user = get_user(user_id)
                
                if pokemon_idx >= len(user.pokemons):
                    await query.answer("Invalid Pokemon selection.")
                    return
                
                selected_pokemon = user.pokemons[pokemon_idx]
                
                # Add the Pokemon to the trade
                added = add_pokemon_to_trade(trade_id, user_id, selected_pokemon.pokemon_id)
                
                if added:
                    await query.answer(f"Added {selected_pokemon.name} to the trade.")
                else:
                    await query.answer(f"Failed to add {selected_pokemon.name} to the trade.")
                
                # Clear the trade state
                del context.user_data["trade_state"]
                
                # Show the updated trade interface
                await show_trade_interface(context, trade_id, user_id)
                
                # Notify the other user
                other_user_id = trade["user2_id"] if user_id == trade["user1_id"] else trade["user1_id"]
                await context.bot.send_message(
                    chat_id=other_user_id,
                    text=f"{update.effective_user.first_name} added {selected_pokemon.name} to the trade."
                )
                
                # Update the other user's trade interface
                await show_trade_interface(context, trade_id, other_user_id)
                
            elif trade_state == "remove_pokemon":
                # Remove the selected Pokemon from the trade
                # Determine which offer list to use
                offer_list = trade["user1_offer"] if user_id == trade["user1_id"] else trade["user2_offer"]
                
                if pokemon_idx >= len(offer_list):
                    await query.answer("Invalid Pokemon selection.")
                    return
                
                # Get the Pokemon ID
                pokemon_id = offer_list[pokemon_idx]
                
                # Find the Pokemon name for notification
                user = get_user(user_id)
                pokemon_name = "Pokemon"
                for pokemon in user.pokemons:
                    if pokemon.pokemon_id == pokemon_id:
                        pokemon_name = pokemon.name
                        break
                
                # Remove the Pokemon from the trade
                removed = remove_pokemon_from_trade(trade_id, user_id, pokemon_id)
                
                if removed:
                    await query.answer(f"Removed {pokemon_name} from the trade.")
                else:
                    await query.answer(f"Failed to remove {pokemon_name} from the trade.")
                
                # Clear the trade state
                del context.user_data["trade_state"]
                
                # Show the updated trade interface
                await show_trade_interface(context, trade_id, user_id)
                
                # Notify the other user
                other_user_id = trade["user2_id"] if user_id == trade["user1_id"] else trade["user1_id"]
                await context.bot.send_message(
                    chat_id=other_user_id,
                    text=f"{update.effective_user.first_name} removed {pokemon_name} from the trade."
                )
                
                # Update the other user's trade interface
                await show_trade_interface(context, trade_id, other_user_id)
                
    except Exception as e:
        logger.error(f"Error in trade callback: {e}")
        await query.edit_message_text(f"An error occurred: {str(e)}")

async def show_trade_interface(context, trade_id, user_id):
    """Show the trade interface to a user."""
    trade = get_trade(trade_id)
    if not trade:
        return
    
    # Get the users
    trader1 = get_user(trade["user1_id"])
    trader2 = get_user(trade["user2_id"])
    
    # Determine which user is which in the trade
    if user_id == trade["user1_id"]:
        my_username = trader1.get_display_name()
        other_username = trader2.get_display_name()
        my_offer = trade["user1_offer"]
        other_offer = trade["user2_offer"]
        my_confirmed = trade["user1_confirmed"]
        other_confirmed = trade["user2_confirmed"]
    else:
        my_username = trader2.get_display_name()
        other_username = trader1.get_display_name()
        my_offer = trade["user2_offer"]
        other_offer = trade["user1_offer"]
        my_confirmed = trade["user2_confirmed"]
        other_confirmed = trade["user1_confirmed"]
    
    # Get the Pokemon objects
    my_pokemon = []
    for pokemon_id in my_offer:
        for pokemon in get_user(user_id).pokemons:
            if pokemon.pokemon_id == pokemon_id:
                my_pokemon.append(pokemon)
                break
    
    other_pokemon = []
    other_user_id = trade["user2_id"] if user_id == trade["user1_id"] else trade["user1_id"]
    for pokemon_id in other_offer:
        for pokemon in get_user(other_user_id).pokemons:
            if pokemon.pokemon_id == pokemon_id:
                other_pokemon.append(pokemon)
                break
    
    # Create the message
    message = f"🔄 *Trade with {other_username}*\n\n"
    
    # My offer
    message += f"*Your offer:*\n"
    if my_pokemon:
        for i, pokemon in enumerate(my_pokemon, start=1):
            message += f"{i}. {pokemon.name} (CP: {pokemon.calculate_cp()})\n"
    else:
        message += "No Pokemon offered yet.\n"
    
    # Their offer
    message += f"\n*{other_username}'s offer:*\n"
    if other_pokemon:
        for i, pokemon in enumerate(other_pokemon, start=1):
            message += f"{i}. {pokemon.name} (CP: {pokemon.calculate_cp()})\n"
    else:
        message += "No Pokemon offered yet.\n"
    
    # Confirmation status
    message += "\n*Status:*\n"
    message += f"You: {'✅ Confirmed' if my_confirmed else '❌ Not confirmed'}\n"
    message += f"{other_username}: {'✅ Confirmed' if other_confirmed else '❌ Not confirmed'}\n"
    
    # Create the keyboard
    keyboard = create_trade_interface_keyboard(trade, user_id)
    
    # Send or edit the message
    try:
        # Try to edit existing message if any
        if "trade_message_id" in context.user_data:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=context.user_data["trade_message_id"],
                text=message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            # Send a new message
            message_obj = await context.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            context.user_data["trade_message_id"] = message_obj.message_id
    except Exception as e:
        logger.error(f"Error showing trade interface: {e}")
        # Just send a new message if editing fails
        message_obj = await context.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        context.user_data["trade_message_id"] = message_obj.message_id

def create_trade_interface_keyboard(trade, user_id, confirmed=None):
    """Create the keyboard for the trade interface."""
    # Check if the user has confirmed the trade
    if confirmed is None:
        if user_id == trade["user1_id"]:
            confirmed = trade["user1_confirmed"]
        else:
            confirmed = trade["user2_confirmed"]
    
    keyboard = []
    
    if not confirmed:
        # Add buttons to add/remove Pokemon
        keyboard.append([
            InlineKeyboardButton("➕ Add Pokemon", callback_data=f"trade_add_{trade['trade_id']}"),
            InlineKeyboardButton("➖ Remove Pokemon", callback_data=f"trade_remove_{trade['trade_id']}")
        ])
        
        # Add confirm button
        keyboard.append([
            InlineKeyboardButton("✅ Confirm Trade", callback_data=f"trade_confirm_{trade['trade_id']}")
        ])
    
    # Always add cancel button
    keyboard.append([
        InlineKeyboardButton("❌ Cancel Trade", callback_data=f"trade_cancel_{trade['trade_id']}")
    ])
    
    return InlineKeyboardMarkup(keyboard)

async def show_pokemon_selection(query, user_id):
    """Show a Pokemon selection interface for trading."""
    user = get_user(user_id)
    
    # Create the message
    message = "Select a Pokemon to add to the trade:\n\n"
    
    # Create the keyboard
    keyboard = []
    trade_id = query.data.split("_")[2]
    
    for i, pokemon in enumerate(user.pokemons):
        button = InlineKeyboardButton(
            f"{pokemon.name} (CP: {pokemon.calculate_cp()})",
            callback_data=f"trade_select_{trade_id}_{i}"
        )
        keyboard.append([button])
    
    # Add cancel button
    keyboard.append([
        InlineKeyboardButton("❌ Cancel", callback_data=f"trade_add_cancel")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Edit the message
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup
    )

async def show_offered_pokemon_selection(query, trade, user_id):
    """Show a selection interface for Pokemon already offered in the trade."""
    # Determine which offer list to use
    offer_list = trade["user1_offer"] if user_id == trade["user1_id"] else trade["user2_offer"]
    
    # Get the user and their Pokemon
    user = get_user(user_id)
    
    # Create the message
    message = "Select a Pokemon to remove from the trade:\n\n"
    
    # Create the keyboard
    keyboard = []
    trade_id = query.data.split("_")[2]
    
    for i, pokemon_id in enumerate(offer_list):
        # Find the Pokemon in the user's collection
        for pokemon in user.pokemons:
            if pokemon.pokemon_id == pokemon_id:
                button = InlineKeyboardButton(
                    f"{pokemon.name} (CP: {pokemon.calculate_cp()})",
                    callback_data=f"trade_select_{trade_id}_{i}"
                )
                keyboard.append([button])
                break
    
    # Add cancel button
    keyboard.append([
        InlineKeyboardButton("❌ Cancel", callback_data=f"trade_remove_cancel")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Edit the message
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup
    )

async def notify_trade_completed(context, trade):
    """Notify both users that the trade has been completed."""
    # Get the users
    trader1 = get_user(trade["user1_id"])
    trader2 = get_user(trade["user2_id"])
    
    # Get the Pokemon objects for each side of the trade
    trader1_pokemon = []
    for pokemon_id in trade["user1_offer"]:
        for pokemon in trader1.pokemons:
            if pokemon.pokemon_id == pokemon_id:
                trader1_pokemon.append(pokemon)
                break
    
    trader2_pokemon = []
    for pokemon_id in trade["user2_offer"]:
        for pokemon in trader2.pokemons:
            if pokemon.pokemon_id == pokemon_id:
                trader2_pokemon.append(pokemon)
                break
    
    # Create the messages
    message1 = (
        "🎉 *Trade Completed!* 🎉\n\n"
        f"You traded with {trader2.get_display_name()}\n\n"
        f"*You gave:*\n"
    )
    for pokemon in trader1_pokemon:
        message1 += f"- {pokemon.name} (CP: {pokemon.calculate_cp()})\n"
    
    message1 += f"\n*You received:*\n"
    for pokemon in trader2_pokemon:
        message1 += f"- {pokemon.name} (CP: {pokemon.calculate_cp()})\n"
    
    message2 = (
        "🎉 *Trade Completed!* 🎉\n\n"
        f"You traded with {trader1.get_display_name()}\n\n"
        f"*You gave:*\n"
    )
    for pokemon in trader2_pokemon:
        message2 += f"- {pokemon.name} (CP: {pokemon.calculate_cp()})\n"
    
    message2 += f"\n*You received:*\n"
    for pokemon in trader1_pokemon:
        message2 += f"- {pokemon.name} (CP: {pokemon.calculate_cp()})\n"
    
    # Send the messages
    await context.bot.send_message(
        chat_id=trader1.user_id,
        text=message1,
        parse_mode="Markdown"
    )
    
    await context.bot.send_message(
        chat_id=trader2.user_id,
        text=message2,
        parse_mode="Markdown"
    )
