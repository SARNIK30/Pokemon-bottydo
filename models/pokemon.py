import uuid
import logging
import random
from typing import List, Dict, Optional, Any
from pokemon_api import get_pokemon_data_sync, get_pokemon_image_url_sync

logger = logging.getLogger(__name__)

class Pokemon:
    """Represents a Pokemon in the game."""
    
    def __init__(
        self,
        pokemon_id: str,
        name: str,
        types: List[str],
        attack: int,
        defense: int,
        hp: int,
        image_url: Optional[str] = None,
        custom: bool = False
    ):
        self.pokemon_id = pokemon_id
        self.name = name
        self.types = types
        self.attack = attack
        self.defense = defense
        self.hp = hp
        self.image_url = image_url
        self.custom = custom
    
    def calculate_cp(self) -> int:
        """Calculate the Combat Power (CP) of the Pokemon."""
        # Simple CP formula: (Attack + Defense) * (HP / 10)
        cp = (self.attack + self.defense) * (self.hp / 10)
        return int(cp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the Pokemon to a dictionary for storage."""
        return {
            "pokemon_id": self.pokemon_id,
            "name": self.name,
            "types": self.types,
            "attack": self.attack,
            "defense": self.defense,
            "hp": self.hp,
            "image_url": self.image_url,
            "custom": self.custom
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Pokemon':
        """Create a Pokemon from a dictionary."""
        return cls(
            pokemon_id=data.get("pokemon_id", str(uuid.uuid4())),
            name=data.get("name", "Unknown"),
            types=data.get("types", []),
            attack=data.get("attack", 0),
            defense=data.get("defense", 0),
            hp=data.get("hp", 0),
            image_url=data.get("image_url"),
            custom=data.get("custom", False)
        )
    
    @classmethod
    def create_from_name(cls, pokemon_name: str) -> Optional['Pokemon']:
        """Create a Pokemon from its name by fetching data from the API."""
        try:
            # Get Pokemon data from the API
            pokemon_data = get_pokemon_data_sync(pokemon_name.lower())
            if not pokemon_data:
                logger.error(f"Failed to get data for Pokemon {pokemon_name}")
                return None
            
            return cls.create_from_data(pokemon_data)
            
        except Exception as e:
            logger.error(f"Error creating Pokemon from name {pokemon_name}: {e}")
            return None
    
    @classmethod
    def create_from_data(cls, pokemon_data: Dict[str, Any]) -> Optional['Pokemon']:
        """Create a Pokemon from API data."""
        try:
            # Extract Pokemon information
            pokemon_id = str(uuid.uuid4())
            name = pokemon_data["name"].capitalize()
            
            # Extract types
            types = [t["type"]["name"] for t in pokemon_data["types"]]
            
            # Extract stats
            stats = {stat["stat"]["name"]: stat["base_stat"] for stat in pokemon_data["stats"]}
            attack = stats.get("attack", random.randint(40, 100))
            defense = stats.get("defense", random.randint(40, 100))
            hp = stats.get("hp", random.randint(40, 100))
            
            # Get image URL
            image_url = None
            if "sprites" in pokemon_data and "other" in pokemon_data["sprites"]:
                if "official-artwork" in pokemon_data["sprites"]["other"]:
                    image_url = pokemon_data["sprites"]["other"]["official-artwork"]["front_default"]
            
            if not image_url:
                image_url = get_pokemon_image_url_sync(name.lower())
            
            # Create and return the Pokemon
            return cls(
                pokemon_id=pokemon_id,
                name=name,
                types=types,
                attack=attack,
                defense=defense,
                hp=hp,
                image_url=image_url
            )
            
        except Exception as e:
            logger.error(f"Error creating Pokemon from data: {e}")
            return None
    
    @classmethod
    def create_custom_pokemon(
        cls,
        name: str,
        types: List[str],
        attack: int,
        defense: int,
        hp: int,
        image_url: Optional[str] = None
    ) -> 'Pokemon':
        """Create a custom Pokemon."""
        return cls(
            pokemon_id=str(uuid.uuid4()),
            name=name,
            types=types,
            attack=attack,
            defense=defense,
            hp=hp,
            image_url=image_url,
            custom=True
        )
        
    @classmethod
    def from_pokeapi(cls, pokemon_data: Dict[str, Any]) -> 'Pokemon':
        """Create a Pokemon from the PokeAPI data."""
        try:
            # Extract Pokemon information
            pokemon_id = str(uuid.uuid4())
            name = pokemon_data["name"].capitalize()
            
            # Extract types
            types = [t["type"]["name"] for t in pokemon_data["types"]]
            
            # Extract stats
            stats = {stat["stat"]["name"]: stat["base_stat"] for stat in pokemon_data["stats"]}
            attack = stats.get("attack", random.randint(40, 100))
            defense = stats.get("defense", random.randint(40, 100))
            hp = stats.get("hp", random.randint(40, 100))
            
            # Get image URL
            image_url = None
            if "sprites" in pokemon_data and "other" in pokemon_data["sprites"]:
                if "official-artwork" in pokemon_data["sprites"]["other"]:
                    image_url = pokemon_data["sprites"]["other"]["official-artwork"].get("front_default")
            
            # Create and return the Pokemon
            return cls(
                pokemon_id=pokemon_id,
                name=name,
                types=types,
                attack=attack,
                defense=defense,
                hp=hp,
                image_url=image_url,
                custom=False
            )
        except Exception as e:
            logger.error(f"Error creating Pokemon from PokeAPI data: {e}")
            return None
