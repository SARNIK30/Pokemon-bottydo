from typing import Dict, Any

class League:
    """Represents a league in the game with requirements and bonuses."""
    
    def __init__(
        self,
        league_id: int,
        pokemon_required: int,
        attack_bonus: int = 0,
        defense_bonus: int = 0,
        health_bonus: int = 0,
        reward_multiplier: float = 1.0
    ):
        self.league_id = league_id
        self.pokemon_required = pokemon_required
        self.attack_bonus = attack_bonus
        self.defense_bonus = defense_bonus
        self.health_bonus = health_bonus
        self.reward_multiplier = reward_multiplier
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the League to a dictionary for storage."""
        return {
            "league_id": self.league_id,
            "pokemon_required": self.pokemon_required,
            "attack_bonus": self.attack_bonus,
            "defense_bonus": self.defense_bonus,
            "health_bonus": self.health_bonus,
            "reward_multiplier": self.reward_multiplier
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'League':
        """Create a League from a dictionary."""
        return cls(
            league_id=data.get("league_id", 1),
            pokemon_required=data.get("pokemon_required", 0),
            attack_bonus=data.get("attack_bonus", 0),
            defense_bonus=data.get("defense_bonus", 0),
            health_bonus=data.get("health_bonus", 0),
            reward_multiplier=data.get("reward_multiplier", 1.0)
        )
    
    @staticmethod
    def get_league_requirements(league_id: int) -> int:
        """Get the number of Pokemon required for a specific league."""
        league_requirements = {
            1: 0,    # League 1 requires 0 Pokemon
            2: 100,  # League 2 requires 100 Pokemon
            3: 200,  # League 3 requires 200 Pokemon
            4: 300,  # League 4 requires 300 Pokemon
            5: 400   # League 5 requires 400 Pokemon
        }
        return league_requirements.get(league_id, 0)
    
    @staticmethod
    def get_league_bonuses(league_id: int) -> Dict[str, int]:
        """Get the bonuses for a specific league."""
        league_bonuses = {
            1: {"attack": 0, "defense": 0, "health": 0},
            2: {"attack": 50, "defense": 50, "health": 50},
            3: {"attack": 100, "defense": 100, "health": 100},
            4: {"attack": 200, "defense": 200, "health": 200},
            5: {"attack": 500, "defense": 500, "health": 500}
        }
        return league_bonuses.get(league_id, {"attack": 0, "defense": 0, "health": 0})
