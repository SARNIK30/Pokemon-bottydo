import os

# Bot configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://your-app-url.repl.co")

# PokeAPI configuration
POKEAPI_BASE_URL = "https://pokeapi.co/api/v2"

# Admin user IDs (comma-separated list of Telegram user IDs)
ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "12345678").split(',')))

# Game configuration
STARTING_BALANCE = 3000
MAX_SAME_POKEMON = 3
POKEMON_CALL_COST = 1000

# Русские названия для стартовых покемонов
STARTER_POKEMON = {
    "charmander": {"id": 4, "name": "Чармандер", "type": "огонь"},
    "bulbasaur": {"id": 1, "name": "Бульбазавр", "type": "трава"},
    "squirtle": {"id": 7, "name": "Сквиртл", "type": "вода"}
}

# Тренеры (стоимость и бонусы)
TRAINERS = {
    "brock": {
        "name": "Брок",
        "cost": 200000,
        "power_bonus": 0.1,  # 10% увеличение силы
        "upgrade_cost": 200000
    },
    "misty": {
        "name": "Мисти",
        "cost": 500000,
        "power_bonus": 0.3,  # 30% увеличение силы
        "upgrade_cost": 500000
    },
    "ash": {
        "name": "Эш",
        "cost": 2000000,
        "power_bonus": 0.7,  # 70% увеличение силы
        "upgrade_cost": 2000000
    },
    "sarner": {
        "name": "САРНЕР",
        "cost": 777777777,
        "power_bonus": 5.0,  # 500% увеличение силы
        "attack_bonus": 5.0,  # 500% увеличение атаки
        "health_bonus": 5.0,  # 500% увеличение здоровья
        "coin_reward": 696969696,
        "requirements": {
            "pokemon": ["gengar", "charizard", "mewtwo"],
            "league": 5
        }
    }
}

# Требования и бонусы для лиг
LEAGUES = {
    1: {
        "pokemon_required": 0,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "health_bonus": 0
    },
    2: {
        "pokemon_required": 100,
        "attack_bonus": 50,
        "defense_bonus": 50,
        "health_bonus": 50
    },
    3: {
        "pokemon_required": 200,
        "attack_bonus": 100,
        "defense_bonus": 100,
        "health_bonus": 100
    },
    4: {
        "pokemon_required": 300,
        "attack_bonus": 200,
        "defense_bonus": 200,
        "health_bonus": 200
    },
    5: {
        "pokemon_required": 400,
        "attack_bonus": 500,
        "defense_bonus": 500,
        "health_bonus": 500
    }
}

# Предметы в магазине
POKEBALLS = {
    "pokeball": {
        "name": "Покебол",
        "cost": 500,
        "catch_rate_bonus": 0.1  # 10% увеличение шанса поимки
    },
    "greatball": {
        "name": "Грейтбол",
        "cost": 1000,
        "catch_rate_bonus": 0.2  # 20% увеличение шанса поимки
    },
    "ultraball": {
        "name": "Ультрабол",
        "cost": 2000,
        "catch_rate_bonus": 0.4  # 40% увеличение шанса поимки
    },
    "masterball": {
        "name": "Мастербол",
        "cost": 50000,
        "catch_rate_bonus": 1.0  # 100% шанс поимки (гарантированно)
    }
}
