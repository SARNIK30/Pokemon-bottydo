import logging
from telegram import Update
from telegram.ext import ContextTypes
from storage import get_user, get_user_pokemon, save_user
from pokemon_api import can_evolve
from models.pokemon import Pokemon

logger = logging.getLogger(__name__)

async def evolution_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /evolution command - evolve a Pokemon."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    # Check if the command has arguments
    if not context.args:
        await update.message.reply_text(
            "Please provide a Pokemon name to evolve. Usage: /evolution Charmander",
            parse_mode="Markdown"
        )
        return
    
    # Get the Pokemon name
    pokemon_name = context.args[0].lower()
    
    # Get the user's Pokemon with this name
    user_pokemon = get_user_pokemon(user_id, pokemon_name)
    
    # Check if the user has enough of this Pokemon
    if len(user_pokemon) < 3:
        await update.message.reply_text(
            f"❌ You need 3 {pokemon_name.capitalize()} to evolve, but you only have {len(user_pokemon)}.",
            parse_mode="Markdown"
        )
        return
    
    # Check if the Pokemon can evolve
    evolution_name = await can_evolve(pokemon_name)
    if not evolution_name:
        await update.message.reply_text(
            f"❌ {pokemon_name.capitalize()} cannot evolve further.",
            parse_mode="Markdown"
        )
        return
    
    # Create the evolved Pokemon
    evolved_pokemon = Pokemon.create_from_name(evolution_name)
    if not evolved_pokemon:
        await update.message.reply_text(
            f"❌ Error creating evolved Pokemon {evolution_name.capitalize()}.",
            parse_mode="Markdown"
        )
        return
    
    # Remove 3 of the base Pokemon
    removed_count = 0
    pokemon_ids_to_remove = []
    for pokemon in user.pokemons:
        if pokemon.name.lower() == pokemon_name and removed_count < 3:
            pokemon_ids_to_remove.append(pokemon.pokemon_id)
            removed_count += 1
    
    for pokemon_id in pokemon_ids_to_remove:
        user.pokemons = [p for p in user.pokemons if p.pokemon_id != pokemon_id]
    
    # Add the evolved Pokemon
    user.pokemons.append(evolved_pokemon)
    
    # Save the user
    save_user(user)
    
    # Get the evolution stats
    cp = evolved_pokemon.calculate_cp()
    
    await update.message.reply_text(
        f"✨ Congratulations! Your 3 {pokemon_name.capitalize()} evolved into {evolved_pokemon.name}! ✨\n\n"
        f"CP: {cp}\n"
        f"Type: {', '.join(evolved_pokemon.types)}\n\n"
        f"Your new {evolved_pokemon.name} has been added to your collection.",
        parse_mode="Markdown"
    )
