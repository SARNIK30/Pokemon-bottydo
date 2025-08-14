import logging
import requests
import asyncio
import aiohttp
from typing import Dict, List, Optional
import config
import functools
import time

logger = logging.getLogger(__name__)

# Cache for Pokemon data to reduce API calls
pokemon_cache = {}
pokemon_species_cache = {}
evolution_chain_cache = {}
image_url_cache = {}
all_pokemon_cache = {}

# Use a single session for all requests
session = None

# Timeout settings (in seconds)
REQUEST_TIMEOUT = 5.0
CACHE_EXPIRY = 3600  # 1 hour

async def get_session():
    """Get or create a shared aiohttp session."""
    global session
    if session is None or session.closed:
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT))
    return session

async def get_pokemon_data(pokemon_id_or_name: str) -> Optional[Dict]:
    """Get Pokemon data from PokeAPI."""
    # Check cache first
    if pokemon_id_or_name in pokemon_cache:
        return pokemon_cache[pokemon_id_or_name]
    
    try:
        url = f"{config.POKEAPI_BASE_URL}/pokemon/{pokemon_id_or_name.lower()}"
        session = await get_session()
        async with session.get(url, timeout=REQUEST_TIMEOUT) as response:
            if response.status == 200:
                data = await response.json()
                # Cache the result
                pokemon_cache[pokemon_id_or_name] = data
                return data
            else:
                logger.error(f"Failed to fetch Pokemon {pokemon_id_or_name}: {response.status}")
                return None
    except asyncio.TimeoutError:
        logger.error(f"Timeout fetching Pokemon {pokemon_id_or_name}")
        return None
    except Exception as e:
        logger.error(f"Error fetching Pokemon data: {e}")
        return None

async def get_pokemon_species(pokemon_id_or_name: str) -> Optional[Dict]:
    """Get Pokemon species data from PokeAPI."""
    # Check cache first
    if pokemon_id_or_name in pokemon_species_cache:
        return pokemon_species_cache[pokemon_id_or_name]
    
    try:
        # First get the Pokemon to find the species URL
        pokemon_data = await get_pokemon_data(pokemon_id_or_name)
        if not pokemon_data:
            return None
        
        species_url = pokemon_data["species"]["url"]
        
        session = await get_session()
        async with session.get(species_url, timeout=REQUEST_TIMEOUT) as response:
            if response.status == 200:
                data = await response.json()
                # Cache the result
                pokemon_species_cache[pokemon_id_or_name] = data
                return data
            else:
                logger.error(f"Failed to fetch Pokemon species {pokemon_id_or_name}: {response.status}")
                return None
    except asyncio.TimeoutError:
        logger.error(f"Timeout fetching Pokemon species {pokemon_id_or_name}")
        return None
    except Exception as e:
        logger.error(f"Error fetching Pokemon species data: {e}")
        return None

async def get_evolution_chain(pokemon_id_or_name: str) -> Optional[Dict]:
    """Get Pokemon evolution chain from PokeAPI."""
    try:
        # First get the species data to find the evolution chain URL
        species_data = await get_pokemon_species(pokemon_id_or_name)
        if not species_data or "evolution_chain" not in species_data:
            return None
        
        evolution_url = species_data["evolution_chain"]["url"]
        
        # Check cache first
        if evolution_url in evolution_chain_cache:
            return evolution_chain_cache[evolution_url]
        
        session = await get_session()
        async with session.get(evolution_url, timeout=REQUEST_TIMEOUT) as response:
            if response.status == 200:
                data = await response.json()
                # Cache the result
                evolution_chain_cache[evolution_url] = data
                return data
            else:
                logger.error(f"Failed to fetch evolution chain for {pokemon_id_or_name}: {response.status}")
                return None
    except asyncio.TimeoutError:
        logger.error(f"Timeout fetching evolution chain for {pokemon_id_or_name}")
        return None
    except Exception as e:
        logger.error(f"Error fetching evolution chain data: {e}")
        return None

async def get_pokemon_image_url(pokemon_id_or_name: str) -> Optional[str]:
    """Get Pokemon official artwork URL."""
    # Check cache first
    if pokemon_id_or_name in image_url_cache:
        return image_url_cache[pokemon_id_or_name]
        
    try:
        pokemon_data = await get_pokemon_data(pokemon_id_or_name)
        if not pokemon_data:
            return None
        
        # Get the official artwork URL
        image_url = pokemon_data["sprites"]["other"]["official-artwork"]["front_default"]
        # Cache the result
        image_url_cache[pokemon_id_or_name] = image_url
        return image_url
    except Exception as e:
        logger.error(f"Error getting Pokemon image URL: {e}")
        return None

async def get_all_pokemon(limit: int = 500) -> List[Dict]:
    """Get a list of all Pokemon up to the limit."""
    # Check cache first
    cache_key = f"all_pokemon_{limit}"
    if cache_key in all_pokemon_cache:
        return all_pokemon_cache[cache_key]
        
    try:
        url = f"{config.POKEAPI_BASE_URL}/pokemon?limit={limit}"
        session = await get_session()
        async with session.get(url, timeout=REQUEST_TIMEOUT) as response:
            if response.status == 200:
                data = await response.json()
                # Cache the result
                all_pokemon_cache[cache_key] = data["results"]
                return data["results"]
            else:
                logger.error(f"Failed to fetch Pokemon list: {response.status}")
                return []
    except asyncio.TimeoutError:
        logger.error(f"Timeout fetching Pokemon list with limit {limit}")
        return []
    except Exception as e:
        logger.error(f"Error fetching Pokemon list: {e}")
        return []

async def get_pokemon_evolutions(pokemon_name: str) -> List[str]:
    """Get a list of possible evolutions for a Pokemon."""
    try:
        evolution_data = await get_evolution_chain(pokemon_name)
        if not evolution_data:
            return []
        
        evolutions = []
        
        # Extract all evolutions from the chain
        chain = evolution_data["chain"]
        
        # Function to recursively extract evolution names
        def extract_evolutions(chain_link):
            species_name = chain_link["species"]["name"]
            evolutions.append(species_name)
            
            for evolution in chain_link.get("evolves_to", []):
                extract_evolutions(evolution)
        
        extract_evolutions(chain)
        return evolutions
    except Exception as e:
        logger.error(f"Error getting Pokemon evolutions: {e}")
        return []

async def can_evolve(pokemon_name: str) -> Optional[str]:
    """Check if a Pokemon can evolve and return the evolution name if possible."""
    try:
        evolution_data = await get_evolution_chain(pokemon_name)
        if not evolution_data:
            return None
        
        # Find the pokemon in the evolution chain
        chain = evolution_data["chain"]
        current_evo = None
        next_evo = None
        
        def find_pokemon_in_chain(chain_link, target_name):
            nonlocal current_evo, next_evo
            
            species_name = chain_link["species"]["name"]
            
            if species_name == target_name.lower():
                current_evo = species_name
                if chain_link.get("evolves_to"):
                    next_evo = chain_link["evolves_to"][0]["species"]["name"]
                return True
            
            for evolution in chain_link.get("evolves_to", []):
                if find_pokemon_in_chain(evolution, target_name):
                    return True
            
            return False
        
        find_pokemon_in_chain(chain, pokemon_name.lower())
        
        return next_evo
    except Exception as e:
        logger.error(f"Error checking evolution for {pokemon_name}: {e}")
        return None

# Utility function to run an async function in a new event loop if needed
def run_async(async_func, *args, **kwargs):
    """Run an async function either in the current or a new event loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a new event loop for the synchronous context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(async_func(*args, **kwargs))
            finally:
                loop.close()
        else:
            # Use the existing event loop
            return loop.run_until_complete(async_func(*args, **kwargs))
    except RuntimeError:
        # No event loop exists, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            loop.close()

# Synchronous versions for use in some contexts
def get_pokemon_data_sync(pokemon_id_or_name: str) -> Optional[Dict]:
    """Synchronous version of get_pokemon_data."""
    return run_async(get_pokemon_data, pokemon_id_or_name)

def get_pokemon_species_sync(pokemon_id_or_name: str) -> Optional[Dict]:
    """Synchronous version of get_pokemon_species."""
    return run_async(get_pokemon_species, pokemon_id_or_name)

def get_evolution_chain_sync(pokemon_id_or_name: str) -> Optional[Dict]:
    """Synchronous version of get_evolution_chain."""
    return run_async(get_evolution_chain, pokemon_id_or_name)

def get_pokemon_image_url_sync(pokemon_id_or_name: str) -> Optional[str]:
    """Synchronous version of get_pokemon_image_url."""
    return run_async(get_pokemon_image_url, pokemon_id_or_name)

def get_all_pokemon_sync(limit: int = 500) -> List[Dict]:
    """Synchronous version of get_all_pokemon."""
    return run_async(get_all_pokemon, limit)

def get_pokemon_evolutions_sync(pokemon_name: str) -> List[str]:
    """Synchronous version of get_pokemon_evolutions."""
    return run_async(get_pokemon_evolutions, pokemon_name)

def can_evolve_sync(pokemon_name: str) -> Optional[str]:
    """Synchronous version of can_evolve."""
    return run_async(can_evolve, pokemon_name)
