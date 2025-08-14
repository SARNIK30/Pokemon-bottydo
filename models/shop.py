from typing import Dict, Any, Optional
import time

class Item:
    """Represents an item that can be purchased in the shop."""
    
    def __init__(
        self,
        item_id: str,
        name: str,
        description: str,
        cost: int,
        category: str,
        effects: Optional[Dict[str, Any]] = None
    ):
        self.item_id = item_id
        self.name = name
        self.description = description
        self.cost = cost
        self.category = category
        self.effects = effects or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the Item to a dictionary for storage."""
        return {
            "item_id": self.item_id,
            "name": self.name,
            "description": self.description,
            "cost": self.cost,
            "category": self.category,
            "effects": self.effects
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Item':
        """Create an Item from a dictionary."""
        return cls(
            item_id=data.get("item_id", "unknown"),
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            cost=data.get("cost", 0),
            category=data.get("category", "misc"),
            effects=data.get("effects", {})
        )

class Promocode:
    """Represents a promocode that can be redeemed for rewards."""
    
    def __init__(
        self,
        code: str,
        reward_type: str = "coins",  # "coins", "pokemon", "trainer", "custom_pokemon"
        reward_value: Any = 0,       # Кол-во монет, имя покемона/тренера или ID уникального покемона
        reward_amount: int = 1,      # Количество наград (только для покемонов)
        created_by: int = 0,
        created_at: Optional[float] = None,
        expires_at: Optional[float] = None,
        max_uses: Optional[int] = None,
        use_count: int = 0,
        description: str = ""       # Описание промокода
    ):
        self.code = code
        self.reward_type = reward_type
        self.reward_value = reward_value
        self.reward_amount = reward_amount
        self.created_by = created_by
        self.created_at = created_at or time.time()
        self.expires_at = expires_at
        self.max_uses = max_uses
        self.use_count = use_count
        self.description = description
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the Promocode to a dictionary for storage."""
        return {
            "code": self.code,
            "reward_type": self.reward_type,
            "reward_value": self.reward_value,
            "reward_amount": self.reward_amount,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "max_uses": self.max_uses,
            "use_count": self.use_count,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Promocode':
        """Create a Promocode from a dictionary."""
        return cls(
            code=data.get("code", ""),
            reward_type=data.get("reward_type", "coins"),
            reward_value=data.get("reward_value", 0),
            reward_amount=data.get("reward_amount", 1),
            created_by=data.get("created_by", 0),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at"),
            max_uses=data.get("max_uses"),
            use_count=data.get("use_count", 0),
            description=data.get("description", "")
        )
    
    def is_valid(self) -> bool:
        """Check if the promocode is still valid."""
        # Check expiration
        if self.expires_at and time.time() > self.expires_at:
            return False
        
        # Check max uses
        if self.max_uses and self.use_count >= self.max_uses:
            return False
        
        return True
    
    def use(self) -> bool:
        """Mark the promocode as used once and return if it was successful."""
        if not self.is_valid():
            return False
        
        self.use_count += 1
        return True
        
    def get_reward_description(self) -> str:
        """Возвращает описание награды в понятном для пользователя виде."""
        if self.reward_type == "coins":
            return f"{self.reward_value} монет"
        elif self.reward_type == "pokemon":
            if self.reward_amount == 1:
                return f"Покемон {self.reward_value}"
            else:
                return f"{self.reward_amount}× Покемон {self.reward_value}"
        elif self.reward_type == "trainer":
            return f"Тренер {self.reward_value}"
        elif self.reward_type == "custom_pokemon":
            return f"Уникальный покемон (ID: {self.reward_value})"
        else:
            return "Неизвестная награда"
