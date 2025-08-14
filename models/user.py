from typing import List, Dict, Any, Optional
import uuid
from models.pokemon import Pokemon

class User:
    """Represents a user (player) in the game."""
    
    def __init__(
        self,
        user_id: int,
        balance: int = 3000,
        pokemons: Optional[List[Pokemon]] = None,
        main_pokemon: Optional[Pokemon] = None,
        caught_pokemon_count: int = 0,
        trainer: Optional[str] = None,
        trainer_level: int = 0,
        league: int = 1,
        pokeballs: Optional[Dict[str, int]] = None,
        used_promocodes: Optional[List[str]] = None,
        username: Optional[str] = None
    ):
        self.user_id = user_id
        self.balance = balance
        self.pokemons = pokemons if pokemons is not None else []
        self.main_pokemon = main_pokemon
        self.caught_pokemon_count = caught_pokemon_count
        self.trainer = trainer
        self.trainer_level = trainer_level
        self.league = league
        self.pokeballs = pokeballs if pokeballs is not None else {}
        self.used_promocodes = used_promocodes if used_promocodes is not None else []
        self.username = username
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the User to a dictionary for storage."""
        return {
            "user_id": self.user_id,
            "balance": self.balance,
            "pokemons": [pokemon.to_dict() for pokemon in self.pokemons],
            "main_pokemon": self.main_pokemon.to_dict() if self.main_pokemon else None,
            "caught_pokemon_count": self.caught_pokemon_count,
            "trainer": self.trainer,
            "trainer_level": self.trainer_level,
            "league": self.league,
            "pokeballs": self.pokeballs,
            "used_promocodes": self.used_promocodes,
            "username": self.username
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create a User from a dictionary."""
        pokemons = [Pokemon.from_dict(p) for p in data.get("pokemons", [])]
        
        main_pokemon = None
        main_pokemon_data = data.get("main_pokemon")
        if main_pokemon_data:
            main_pokemon = Pokemon.from_dict(main_pokemon_data)
        
        return cls(
            user_id=data.get("user_id"),
            balance=data.get("balance", 3000),
            pokemons=pokemons,
            main_pokemon=main_pokemon,
            caught_pokemon_count=data.get("caught_pokemon_count", 0),
            trainer=data.get("trainer"),
            trainer_level=data.get("trainer_level", 0),
            league=data.get("league", 1),
            pokeballs=data.get("pokeballs", {}),
            used_promocodes=data.get("used_promocodes", []),
            username=data.get("username")
        )
    
    def get_display_name(self) -> str:
        """Get the display name for the user."""
        return self.username or f"User {self.user_id}"
    
    def get_unique_pokemon_count(self) -> int:
        """Get the count of unique Pokemon species owned by the user."""
        unique_pokemon = set(pokemon.name.lower() for pokemon in self.pokemons)
        return len(unique_pokemon)
    
    def get_pokemon_by_id(self, pokemon_id: str) -> Optional[Pokemon]:
        """Get a Pokemon by its ID."""
        for pokemon in self.pokemons:
            if pokemon.pokemon_id == pokemon_id:
                return pokemon
        return None
