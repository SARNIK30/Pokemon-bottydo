from typing import Dict, Any, Optional

class Trainer:
    """Represents a Pokemon Trainer that can be purchased for bonuses."""
    
    def __init__(
        self,
        name: str,
        trainer_id: str,
        cost: int,
        power_bonus: float = 0.0,
        attack_bonus: float = 0.0,
        defense_bonus: float = 0.0,
        health_bonus: float = 0.0,
        upgrade_cost: Optional[int] = None,
        requirements: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.trainer_id = trainer_id
        self.cost = cost
        self.power_bonus = power_bonus
        self.attack_bonus = attack_bonus
        self.defense_bonus = defense_bonus
        self.health_bonus = health_bonus
        self.upgrade_cost = upgrade_cost
        self.requirements = requirements or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the Trainer to a dictionary for storage."""
        return {
            "name": self.name,
            "trainer_id": self.trainer_id,
            "cost": self.cost,
            "power_bonus": self.power_bonus,
            "attack_bonus": self.attack_bonus,
            "defense_bonus": self.defense_bonus,
            "health_bonus": self.health_bonus,
            "upgrade_cost": self.upgrade_cost,
            "requirements": self.requirements
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trainer':
        """Create a Trainer from a dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            trainer_id=data.get("trainer_id", "unknown"),
            cost=data.get("cost", 0),
            power_bonus=data.get("power_bonus", 0.0),
            attack_bonus=data.get("attack_bonus", 0.0),
            defense_bonus=data.get("defense_bonus", 0.0),
            health_bonus=data.get("health_bonus", 0.0),
            upgrade_cost=data.get("upgrade_cost"),
            requirements=data.get("requirements", {})
        )
    
    def calculate_bonus_at_level(self, level: int) -> Dict[str, float]:
        """Calculate bonuses at a specific trainer level."""
        # Base bonuses
        bonuses = {
            "power": self.power_bonus,
            "attack": self.attack_bonus,
            "defense": self.defense_bonus,
            "health": self.health_bonus
        }
        
        # Apply level scaling (10% increase per level)
        if level > 1:
            for key in bonuses:
                bonuses[key] = bonuses[key] * (1 + 0.1 * (level - 1))
        
        return bonuses
