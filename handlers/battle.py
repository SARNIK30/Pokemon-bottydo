import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from storage import (
    get_user, start_battle, get_battle, set_user_ready_for_battle,
    finish_battle
)
import config

logger = logging.getLogger(__name__)

async def battle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /battle command - initiate a battle with another user."""
    # Check if the command is a reply to another user's message
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "⚔️ To initiate a battle, reply to another user's message with /battle"
        )
        return
    
    # Get the user IDs
    challenger_id = update.effective_user.id
    opponent_id = update.message.reply_to_message.from_user.id
    
    # Make sure the opponent is not the bot or the same user
    if opponent_id == context.bot.id:
        await update.message.reply_text("🤖 You can't battle against me!")
        return
    
    if challenger_id == opponent_id:
        await update.message.reply_text("🙄 You can't battle against yourself!")
        return
    
    # Get the users
    challenger = get_user(challenger_id)
    opponent = get_user(opponent_id)
    
    # Check if the users have Pokemon
    if not challenger.pokemons:
        await update.message.reply_text("You don't have any Pokemon to battle with!")
        return
    
    if not opponent.pokemons:
        await update.message.reply_text("Your opponent doesn't have any Pokemon to battle with!")
        return
    
    # Start a battle
    battle_id = start_battle(challenger_id, opponent_id)
    
    # Store the battle ID in the context
    context.user_data["current_battle"] = battle_id
    
    # Create a keyboard for the opponent to accept or decline
    keyboard = [
        [
            InlineKeyboardButton("Accept", callback_data=f"battle_accept_{battle_id}"),
            InlineKeyboardButton("Decline", callback_data=f"battle_decline_{battle_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send a message to the opponent
    challenger_name = update.effective_user.first_name
    await update.message.reply_to_message.reply_text(
        f"⚔️ {challenger_name} has challenged you to a Pokemon battle!\n"
        "Do you accept?",
        reply_markup=reply_markup
    )

async def battle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle battle-related callback queries."""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    try:
        # Extract the action and battle ID
        parts = data.split("_")
        action = parts[1]
        battle_id = parts[2] if len(parts) > 2 else None
        
        await query.answer()
        
        if action == "accept" and battle_id:
            # Get the battle
            battle = get_battle(battle_id)
            if not battle:
                await query.edit_message_text("This battle is no longer available.")
                return
            
            # Make sure this user is the opponent
            if user_id != battle["user2_id"]:
                await query.edit_message_text("This battle challenge is not for you.")
                return
            
            # Mark the opponent as ready
            set_user_ready_for_battle(battle_id, user_id)
            
            # Get the users
            challenger = get_user(battle["user1_id"])
            opponent = get_user(battle["user2_id"])
            
            # Let the challenger know the battle was accepted
            await context.bot.send_message(
                chat_id=battle["user1_id"],
                text=f"🔥 {opponent.get_display_name()} has accepted your battle challenge!"
            )
            
            # Create keyboards for selecting Pokemon
            challenger_keyboard = create_pokemon_selection_keyboard(challenger, battle_id, "challenger")
            opponent_keyboard = create_pokemon_selection_keyboard(opponent, battle_id, "opponent")
            
            # Send messages to select Pokemon
            await context.bot.send_message(
                chat_id=battle["user1_id"],
                text="Select your Pokemon for battle:",
                reply_markup=challenger_keyboard
            )
            
            await query.edit_message_text(
                "You accepted the battle challenge! Select your Pokemon for battle:",
                reply_markup=opponent_keyboard
            )
            
        elif action == "decline" and battle_id:
            # Get the battle
            battle = get_battle(battle_id)
            if not battle:
                await query.edit_message_text("This battle is no longer available.")
                return
            
            # Make sure this user is the opponent
            if user_id != battle["user2_id"]:
                await query.edit_message_text("This battle challenge is not for you.")
                return
            
            # Let the challenger know the battle was declined
            await context.bot.send_message(
                chat_id=battle["user1_id"],
                text=f"😔 {update.effective_user.first_name} has declined your battle challenge."
            )
            
            await query.edit_message_text("You declined the battle challenge.")
            
        elif action == "select" and battle_id:
            # This is a Pokemon selection callback
            # Extract the role and Pokemon index
            role = parts[3]
            pokemon_index = int(parts[4])
            
            # Get the battle
            battle = get_battle(battle_id)
            if not battle:
                await query.edit_message_text("This battle is no longer available.")
                return
            
            # Make sure this user is in the battle
            if (role == "challenger" and user_id != battle["user1_id"]) or \
               (role == "opponent" and user_id != battle["user2_id"]):
                await query.edit_message_text("This battle is not for you.")
                return
            
            # Get the user and their Pokemon
            user = get_user(user_id)
            if pokemon_index >= len(user.pokemons):
                await query.edit_message_text("Invalid Pokemon selection.")
                return
            
            selected_pokemon = user.pokemons[pokemon_index]
            
            # Store the selected Pokemon in the battle
            if role == "challenger":
                battle["challenger_pokemon"] = selected_pokemon
                battle["user1_ready"] = True
            else:
                battle["opponent_pokemon"] = selected_pokemon
                battle["user2_ready"] = True
            
            await query.edit_message_text(f"You selected {selected_pokemon.name} for battle! Waiting for opponent...")
            
            # If both users have selected their Pokemon, start the battle
            if battle.get("user1_ready") and battle.get("user2_ready"):
                await execute_battle(context, battle_id)
                
    except Exception as e:
        logger.error(f"Error in battle callback: {e}")
        await query.edit_message_text(f"An error occurred: {str(e)}")

def create_pokemon_selection_keyboard(user, battle_id, role):
    """Create a keyboard for selecting Pokemon for battle."""
    keyboard = []
    for i, pokemon in enumerate(user.pokemons):
        button = InlineKeyboardButton(
            f"{pokemon.name} (CP: {pokemon.calculate_cp()})",
            callback_data=f"battle_select_{battle_id}_{role}_{i}"
        )
        keyboard.append([button])
    
    return InlineKeyboardMarkup(keyboard)

async def execute_battle(context, battle_id):
    """Execute a battle between two users."""
    # Get the battle
    battle = get_battle(battle_id)
    if not battle:
        return
    
    # Get the users and their Pokemon
    challenger = get_user(battle["user1_id"])
    opponent = get_user(battle["user2_id"])
    challenger_pokemon = battle["challenger_pokemon"]
    opponent_pokemon = battle["opponent_pokemon"]
    
    # Calculate Pokemon power with league and trainer bonuses
    challenger_power = calculate_battle_power(challenger, challenger_pokemon)
    opponent_power = calculate_battle_power(opponent, opponent_pokemon)
    
    # Determine the winner
    if challenger_power > opponent_power:
        winner_id = challenger.user_id
        loser_id = opponent.user_id
        winner_pokemon = challenger_pokemon
        loser_pokemon = opponent_pokemon
        winner_power = challenger_power
        loser_power = opponent_power
    else:
        winner_id = opponent.user_id
        loser_id = challenger.user_id
        winner_pokemon = opponent_pokemon
        loser_pokemon = challenger_pokemon
        winner_power = opponent_power
        loser_power = challenger_power
    
    # Calculate the reward (based on the difference in power)
    reward = calculate_battle_reward(winner_power, loser_power)
    
    # Finish the battle
    finish_battle(battle_id, winner_id, loser_id, reward)
    
    # Prepare the battle result message
    battle_result = (
        f"⚔️ *Battle Results* ⚔️\n\n"
        f"{challenger.get_display_name()}'s {challenger_pokemon.name} (Power: {challenger_power}) "
        f"VS {opponent.get_display_name()}'s {opponent_pokemon.name} (Power: {opponent_power})\n\n"
        f"🏆 Winner: {get_user(winner_id).get_display_name()}'s {winner_pokemon.name}\n"
        f"💰 Reward: {reward} coins\n\n"
        f"Better luck next time, {get_user(loser_id).get_display_name()}!"
    )
    
    # Send the result to both users
    await context.bot.send_message(
        chat_id=challenger.user_id,
        text=battle_result,
        parse_mode="Markdown"
    )
    
    if challenger.user_id != opponent.user_id:  # Avoid sending duplicate messages if it's the same user
        await context.bot.send_message(
            chat_id=opponent.user_id,
            text=battle_result,
            parse_mode="Markdown"
        )

def calculate_battle_power(user, pokemon):
    """Calculate a Pokemon's battle power with league and trainer bonuses."""
    # Get the base Pokemon power (CP)
    base_power = pokemon.calculate_cp()
    
    # Apply league bonuses
    league_data = config.LEAGUES.get(user.league, config.LEAGUES[1])
    attack_bonus = league_data.get("attack_bonus", 0)
    defense_bonus = league_data.get("defense_bonus", 0)
    health_bonus = league_data.get("health_bonus", 0)
    
    # Apply trainer bonuses if the user has a trainer
    trainer_bonus = 1.0
    if user.trainer:
        trainer_data = config.TRAINERS.get(user.trainer.lower(), {})
        trainer_bonus += trainer_data.get("power_bonus", 0)
    
    # Calculate total power
    total_power = base_power * trainer_bonus
    
    # Add stat bonuses
    total_power += (attack_bonus + defense_bonus + health_bonus)
    
    return int(total_power)

def calculate_battle_reward(winner_power, loser_power):
    """Calculate the reward for winning a battle."""
    # Base reward
    base_reward = 500
    
    # Bonus based on power difference (with a cap)
    power_difference = max(0, winner_power - loser_power)
    power_bonus = min(1000, power_difference / 10)
    
    # Random factor (80% to 120% of the calculated reward)
    random_factor = random.uniform(0.8, 1.2)
    
    total_reward = int((base_reward + power_bonus) * random_factor)
    return total_reward
