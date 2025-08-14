"""
Модуль с мини-играми для заработка денег в Покемон боте.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from storage import get_user, save_user, get_all_users

# Словарь для хранения времени последнего использования игры каждым пользователем
# Формат: {user_id: {game_name: datetime}}
user_cooldowns = {}

# Время ожидания между играми в секундах
GAME_COOLDOWNS = {
    "dice": 3600,  # 1 час
    "slots": 1800,  # 30 минут
    "guess_number": 600,  # 10 минут
    "pokemon_quiz": 1200,  # 20 минут
    "daily": 86400,  # 24 часа
}

# Активные игры "Угадай число"
active_guess_games = {}

# Активные игры "Покемон-викторина"
active_quiz_games = {}


async def games_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /games - показывает меню игр."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    # Создаем клавиатуру с доступными играми
    keyboard = [
        [
            InlineKeyboardButton("🎲 Кости", callback_data="game_dice"),
            InlineKeyboardButton("🎰 Слоты", callback_data="game_slots")
        ],
        [
            InlineKeyboardButton("🔢 Угадай число", callback_data="game_guess_number"),
            InlineKeyboardButton("❓ Покемон-викторина", callback_data="game_pokemon_quiz")
        ],
        [
            InlineKeyboardButton("💰 Ежедневный бонус", callback_data="game_daily")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎮 *Мини-игры*\n\n"
        f"Здесь вы можете поиграть в различные игры и заработать монеты!\n"
        f"Текущий баланс: {user.balance} 💰\n\n"
        f"Выберите игру:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def games_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки в меню игр."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user(user_id)
    
    # Определяем, какая игра выбрана
    if query.data == "game_dice":
        await handle_dice_game(query, user)
    elif query.data == "game_slots":
        await handle_slots_game(query, user)
    elif query.data == "game_guess_number":
        await handle_guess_number_game(query, user)
    elif query.data == "game_pokemon_quiz":
        await handle_pokemon_quiz(query, user, context)
    elif query.data == "game_daily":
        await handle_daily_bonus(query, user)
    elif query.data.startswith("guess_"):
        _, number = query.data.split("_")
        await process_guess_number(query, user, int(number))
    elif query.data.startswith("quiz_"):
        _, answer_index = query.data.split("_")
        await process_pokemon_quiz_answer(query, user, int(answer_index))
    elif query.data == "games_menu":
        # Возврат в основное меню игр
        await query.edit_message_text(
            f"🎮 *Мини-игры*\n\n"
            f"Здесь вы можете поиграть в различные игры и заработать монеты!\n"
            f"Текущий баланс: {user.balance} 💰\n\n"
            f"Выберите игру:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎲 Кости", callback_data="game_dice"),
                    InlineKeyboardButton("🎰 Слоты", callback_data="game_slots")
                ],
                [
                    InlineKeyboardButton("🔢 Угадай число", callback_data="game_guess_number"),
                    InlineKeyboardButton("❓ Покемон-викторина", callback_data="game_pokemon_quiz")
                ],
                [
                    InlineKeyboardButton("💰 Ежедневный бонус", callback_data="game_daily")
                ]
            ]),
            parse_mode="Markdown"
        )


async def handle_dice_game(query, user):
    """Игра в кости."""
    user_id = user.user_id
    
    # Проверяем кулдаун
    if is_on_cooldown(user_id, "dice"):
        cooldown_remaining = get_cooldown_remaining(user_id, "dice")
        await query.edit_message_text(
            f"⏳ Вы недавно уже играли в кости!\n"
            f"Подождите еще {format_time_remaining(cooldown_remaining)} для следующей игры.\n\n"
            f"Текущий баланс: {user.balance} 💰",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Назад к играм", callback_data="games_menu")]
            ])
        )
        return
    
    # Генерируем случайное число от 1 до 6
    dice_result = random.randint(1, 6)
    
    # Рассчитываем выигрыш
    winnings = dice_result * 10
    user.balance += winnings
    save_user(user)
    
    # Устанавливаем кулдаун
    set_cooldown(user_id, "dice")
    
    # Отображаем результат
    dice_emoji = "🎲"
    await query.edit_message_text(
        f"{dice_emoji} *Игра в кости*\n\n"
        f"Вы бросили: *{dice_result}*\n"
        f"Выигрыш: *{winnings}* 💰\n\n"
        f"Текущий баланс: {user.balance} 💰\n"
        f"Следующая игра будет доступна через 1 час.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Назад к играм", callback_data="games_menu")]
        ]),
        parse_mode="Markdown"
    )


async def handle_slots_game(query, user):
    """Игра в слоты."""
    user_id = user.user_id
    
    # Проверяем кулдаун
    if is_on_cooldown(user_id, "slots"):
        cooldown_remaining = get_cooldown_remaining(user_id, "slots")
        await query.edit_message_text(
            f"⏳ Вы недавно уже играли в слоты!\n"
            f"Подождите еще {format_time_remaining(cooldown_remaining)} для следующей игры.\n\n"
            f"Текущий баланс: {user.balance} 💰",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Назад к играм", callback_data="games_menu")]
            ])
        )
        return
    
    # Символы для слотов
    symbols = ["🍇", "🍊", "🍒", "🍋", "🍉", "🍓", "💎"]
    weights = [20, 20, 20, 15, 15, 8, 2]  # Вероятности выпадения
    
    # Генерируем результаты
    result = random.choices(symbols, weights=weights, k=3)
    
    # Определяем выигрыш
    winnings = 0
    result_text = " | ".join(result)
    
    if result[0] == result[1] == result[2]:
        # Джекпот - все три символа совпадают
        if result[0] == "💎":
            winnings = 500  # Специальный джекпот для бриллиантов
        else:
            winnings = 100
        result_description = f"*ДЖЕКПОТ!* Три одинаковых символа! +{winnings} 💰"
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        # Два совпадающих символа
        if (result[0] == "💎" and result[1] == "💎") or (result[1] == "💎" and result[2] == "💎") or (result[0] == "💎" and result[2] == "💎"):
            winnings = 100  # Специальный выигрыш для двух бриллиантов
        else:
            winnings = 20
        result_description = f"*Удача!* Два одинаковых символа! +{winnings} 💰"
    elif "💎" in result:
        # Есть хотя бы один бриллиант
        diamond_count = result.count("💎")
        winnings = 10 * diamond_count
        result_description = f"*Неплохо!* {diamond_count} бриллиант(ов)! +{winnings} 💰"
    else:
        # Ничего не совпало
        winnings = 0
        result_description = "*Не повезло!* Попробуйте еще раз."
    
    # Обновляем баланс
    user.balance += winnings
    save_user(user)
    
    # Устанавливаем кулдаун
    set_cooldown(user_id, "slots")
    
    # Отображаем результат
    await query.edit_message_text(
        f"🎰 *Игра в слоты*\n\n"
        f"*[ {result_text} ]*\n\n"
        f"{result_description}\n\n"
        f"Текущий баланс: {user.balance} 💰\n"
        f"Следующая игра будет доступна через 30 минут.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Назад к играм", callback_data="games_menu")]
        ]),
        parse_mode="Markdown"
    )


async def handle_guess_number_game(query, user):
    """Игра 'Угадай число'."""
    user_id = user.user_id
    
    # Проверяем кулдаун
    if is_on_cooldown(user_id, "guess_number"):
        cooldown_remaining = get_cooldown_remaining(user_id, "guess_number")
        await query.edit_message_text(
            f"⏳ Вы недавно уже играли в 'Угадай число'!\n"
            f"Подождите еще {format_time_remaining(cooldown_remaining)} для следующей игры.\n\n"
            f"Текущий баланс: {user.balance} 💰",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Назад к играм", callback_data="games_menu")]
            ])
        )
        return
    
    # Генерируем случайное число от 1 до 10
    secret_number = random.randint(1, 10)
    active_guess_games[user_id] = secret_number
    
    # Создаем клавиатуру с числами
    keyboard = []
    row = []
    for i in range(1, 11):
        row.append(InlineKeyboardButton(str(i), callback_data=f"guess_{i}"))
        if i % 5 == 0:
            keyboard.append(row)
            row = []
    
    keyboard.append([InlineKeyboardButton("« Назад к играм", callback_data="games_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отображаем игру
    await query.edit_message_text(
        f"🔢 *Угадай число*\n\n"
        f"Я загадал число от 1 до 10. Попробуйте угадать!\n\n"
        f"За правильный ответ вы получите 50 монет.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def process_guess_number(query, user, guessed_number):
    """Обработка ответа в игре 'Угадай число'."""
    user_id = user.user_id
    
    # Проверяем, есть ли активная игра
    if user_id not in active_guess_games:
        await query.edit_message_text(
            "Ошибка: игра не найдена. Пожалуйста, начните новую игру.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Назад к играм", callback_data="games_menu")]
            ])
        )
        return
    
    secret_number = active_guess_games[user_id]
    del active_guess_games[user_id]  # Удаляем игру после хода
    
    # Определяем результат
    if guessed_number == secret_number:
        # Победа
        winnings = 50
        user.balance += winnings
        result_text = f"🎉 *Правильно!*\nЗагаданное число: {secret_number}\nВы выиграли {winnings} 💰"
    else:
        # Проигрыш
        result_text = f"❌ *Неверно!*\nЗагаданное число было: {secret_number}\nПопробуйте еще раз позже."
    
    # Устанавливаем кулдаун
    set_cooldown(user_id, "guess_number")
    save_user(user)
    
    # Отображаем результат
    await query.edit_message_text(
        f"🔢 *Угадай число*\n\n"
        f"{result_text}\n\n"
        f"Текущий баланс: {user.balance} 💰\n"
        f"Следующая игра будет доступна через 10 минут.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Назад к играм", callback_data="games_menu")]
        ]),
        parse_mode="Markdown"
    )


async def handle_pokemon_quiz(query, user, context):
    """Игра 'Покемон-викторина'."""
    user_id = user.user_id
    
    # Проверяем кулдаун
    if is_on_cooldown(user_id, "pokemon_quiz"):
        cooldown_remaining = get_cooldown_remaining(user_id, "pokemon_quiz")
        await query.edit_message_text(
            f"⏳ Вы недавно уже играли в 'Покемон-викторину'!\n"
            f"Подождите еще {format_time_remaining(cooldown_remaining)} для следующей игры.\n\n"
            f"Текущий баланс: {user.balance} 💰",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Назад к играм", callback_data="games_menu")]
            ])
        )
        return
    
    # Загружаем данные для викторины из контекста
    quiz_data = await generate_pokemon_quiz()
    active_quiz_games[user_id] = quiz_data
    
    # Создаем клавиатуру с вариантами ответов
    keyboard = []
    for i, option in enumerate(quiz_data["options"]):
        keyboard.append([InlineKeyboardButton(option, callback_data=f"quiz_{i}")])
    
    keyboard.append([InlineKeyboardButton("« Назад к играм", callback_data="games_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отображаем вопрос
    await query.edit_message_text(
        f"❓ *Покемон-викторина*\n\n"
        f"{quiz_data['question']}\n\n"
        f"За правильный ответ вы получите 80 монет.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def generate_pokemon_quiz() -> Dict:
    """Генерирует случайный вопрос для покемон-викторины."""
    # Список типов вопросов
    question_types = [
        "type_question",
        "evolution_question",
        "generation_question",
        "ability_question"
    ]
    
    # Выбираем случайный тип вопроса
    question_type = random.choice(question_types)
    
    # Генерируем вопрос на основе выбранного типа
    if question_type == "type_question":
        # Вопрос о типе покемона
        pokemon_types = [
            "Огненный", "Водный", "Травяной", "Электрический", 
            "Ледяной", "Боевой", "Ядовитый", "Земляной", 
            "Летающий", "Психический", "Насекомый", "Каменный", 
            "Призрачный", "Драконий", "Темный", "Стальной", "Волшебный"
        ]
        
        pokemon_list = [
            ("Пикачу", "Электрический"),
            ("Чармандер", "Огненный"),
            ("Бульбазавр", "Травяной"),
            ("Сквиртл", "Водный"),
            ("Джиглипафф", "Волшебный"),
            ("Генгар", "Призрачный"),
            ("Драгонайт", "Драконий"),
            ("Магикарп", "Водный"),
            ("Мьюту", "Психический"),
            ("Снорлакс", "Нормальный")
        ]
        
        # Выбираем случайного покемона
        pokemon, correct_type = random.choice(pokemon_list)
        
        # Генерируем варианты ответов
        options = [correct_type]
        while len(options) < 4:
            random_type = random.choice(pokemon_types)
            if random_type not in options:
                options.append(random_type)
        
        # Перемешиваем варианты
        random.shuffle(options)
        
        # Определяем правильный ответ
        correct_answer = options.index(correct_type)
        
        return {
            "question": f"Какого типа покемон {pokemon}?",
            "options": options,
            "correct_answer": correct_answer
        }
    
    elif question_type == "evolution_question":
        # Вопрос об эволюции покемона
        evolution_pairs = [
            ("Пикачу", "Райчу"),
            ("Чармандер", "Чармелеон"),
            ("Бульбазавр", "Ивизавр"),
            ("Сквиртл", "Вартортл"),
            ("Гастли", "Хонтер"),
            ("Иви", "Вапореон"),
            ("Абра", "Кадабра"),
            ("Магикарп", "Гиарадос"),
            ("Дратини", "Драгонэйр"),
            ("Поливаг", "Поливирл")
        ]
        
        # Выбираем случайную пару эволюций
        base_pokemon, evolved_pokemon = random.choice(evolution_pairs)
        
        # Генерируем неправильные варианты
        all_evolved = [pair[1] for pair in evolution_pairs]
        wrong_options = [evo for evo in all_evolved if evo != evolved_pokemon]
        options = [evolved_pokemon] + random.sample(wrong_options, 3)
        
        # Перемешиваем варианты
        random.shuffle(options)
        
        # Определяем правильный ответ
        correct_answer = options.index(evolved_pokemon)
        
        return {
            "question": f"В какого покемона эволюционирует {base_pokemon}?",
            "options": options,
            "correct_answer": correct_answer
        }
    
    elif question_type == "generation_question":
        # Вопрос о поколении покемона
        generation_data = [
            ("Пикачу", "Первое"),
            ("Чикорита", "Второе"),
            ("Мадкип", "Третье"),
            ("Чимчар", "Четвертое"),
            ("Ошавотт", "Пятое"),
            ("Фрокки", "Шестое"),
            ("Роулет", "Седьмое"),
            ("Скорбанни", "Восьмое")
        ]
        
        # Выбираем случайного покемона
        pokemon, correct_gen = random.choice(generation_data)
        
        # Генерируем варианты ответов
        generations = ["Первое", "Второе", "Третье", "Четвертое", "Пятое", "Шестое", "Седьмое", "Восьмое"]
        options = [correct_gen]
        while len(options) < 4:
            random_gen = random.choice(generations)
            if random_gen not in options:
                options.append(random_gen)
        
        # Перемешиваем варианты
        random.shuffle(options)
        
        # Определяем правильный ответ
        correct_answer = options.index(correct_gen)
        
        return {
            "question": f"К какому поколению относится покемон {pokemon}?",
            "options": options,
            "correct_answer": correct_answer
        }
    
    else:  # ability_question
        # Вопрос о способности покемона
        ability_data = [
            ("Пикачу", "Статическое электричество"),
            ("Чармандер", "Солнечная сила"),
            ("Бульбазавр", "Хлорофилл"),
            ("Сквиртл", "Шелковый панцирь"),
            ("Генгар", "Левитация"),
            ("Слоубро", "Собственный темп"),
            ("Мачамп", "Непробиваемый"),
            ("Алаказам", "Внутренний фокус"),
            ("Гиарадос", "Запугивание"),
            ("Драгонайт", "Мультисила")
        ]
        
        # Выбираем случайного покемона
        pokemon, correct_ability = random.choice(ability_data)
        
        # Генерируем варианты ответов
        all_abilities = [data[1] for data in ability_data]
        options = [correct_ability]
        wrong_options = [ability for ability in all_abilities if ability != correct_ability]
        options.extend(random.sample(wrong_options, 3))
        
        # Перемешиваем варианты
        random.shuffle(options)
        
        # Определяем правильный ответ
        correct_answer = options.index(correct_ability)
        
        return {
            "question": f"Какая способность у покемона {pokemon}?",
            "options": options,
            "correct_answer": correct_answer
        }


async def process_pokemon_quiz_answer(query, user, answer_index):
    """Обработка ответа в игре 'Покемон-викторина'."""
    user_id = user.user_id
    
    # Проверяем, есть ли активная игра
    if user_id not in active_quiz_games:
        await query.edit_message_text(
            "Ошибка: викторина не найдена. Пожалуйста, начните новую игру.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Назад к играм", callback_data="games_menu")]
            ])
        )
        return
    
    quiz_data = active_quiz_games[user_id]
    correct_answer = quiz_data["correct_answer"]
    del active_quiz_games[user_id]  # Удаляем игру после ответа
    
    # Определяем результат
    if answer_index == correct_answer:
        # Правильный ответ
        winnings = 80
        user.balance += winnings
        result_text = f"🎉 *Правильно!*\nВы выиграли {winnings} 💰"
    else:
        # Неправильный ответ
        correct_option = quiz_data["options"][correct_answer]
        result_text = f"❌ *Неверно!*\nПравильный ответ: {correct_option}"
    
    # Устанавливаем кулдаун и сохраняем данные пользователя
    set_cooldown(user_id, "pokemon_quiz")
    save_user(user)
    
    # Отображаем результат
    await query.edit_message_text(
        f"❓ *Покемон-викторина*\n\n"
        f"{result_text}\n\n"
        f"Текущий баланс: {user.balance} 💰\n"
        f"Следующая игра будет доступна через 20 минут.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Назад к играм", callback_data="games_menu")]
        ]),
        parse_mode="Markdown"
    )


async def handle_daily_bonus(query, user):
    """Ежедневный бонус."""
    user_id = user.user_id
    
    # Проверяем кулдаун
    if is_on_cooldown(user_id, "daily"):
        cooldown_remaining = get_cooldown_remaining(user_id, "daily")
        await query.edit_message_text(
            f"⏳ Вы уже получили свой ежедневный бонус!\n"
            f"Следующий бонус будет доступен через {format_time_remaining(cooldown_remaining)}.\n\n"
            f"Текущий баланс: {user.balance} 💰",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Назад к играм", callback_data="games_menu")]
            ])
        )
        return
    
    # Начисляем бонус
    # Размер бонуса зависит от лиги игрока
    league_id = getattr(user, 'league', 0) or 0
    base_bonus = 100
    league_multiplier = 1 + (league_id * 0.2)  # Увеличиваем на 20% за каждую лигу
    bonus = int(base_bonus * league_multiplier)
    
    # Шанс на двойной бонус (10%)
    if random.random() < 0.1:
        bonus *= 2
        bonus_text = f"🎉 *ДВОЙНОЙ БОНУС!* Вы получили {bonus} 💰"
    else:
        bonus_text = f"🎁 Вы получили ежедневный бонус в размере {bonus} 💰"
    
    # Обновляем баланс
    user.balance += bonus
    save_user(user)
    
    # Устанавливаем кулдаун
    set_cooldown(user_id, "daily")
    
    # Отображаем результат
    await query.edit_message_text(
        f"💰 *Ежедневный бонус*\n\n"
        f"{bonus_text}\n\n"
        f"Текущий баланс: {user.balance} 💰\n"
        f"Приходите завтра за новым бонусом!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Назад к играм", callback_data="games_menu")]
        ]),
        parse_mode="Markdown"
    )


def is_on_cooldown(user_id: int, game_name: str) -> bool:
    """Проверяет, находится ли игра на кулдауне для пользователя."""
    if user_id not in user_cooldowns:
        return False
    
    if game_name not in user_cooldowns[user_id]:
        return False
    
    last_play_time = user_cooldowns[user_id][game_name]
    cooldown_seconds = GAME_COOLDOWNS.get(game_name, 0)
    
    return datetime.now() < last_play_time + timedelta(seconds=cooldown_seconds)


def get_cooldown_remaining(user_id: int, game_name: str) -> int:
    """Возвращает оставшееся время кулдауна в секундах."""
    if user_id not in user_cooldowns or game_name not in user_cooldowns[user_id]:
        return 0
    
    last_play_time = user_cooldowns[user_id][game_name]
    cooldown_seconds = GAME_COOLDOWNS.get(game_name, 0)
    cooldown_end = last_play_time + timedelta(seconds=cooldown_seconds)
    
    if datetime.now() >= cooldown_end:
        return 0
    
    return int((cooldown_end - datetime.now()).total_seconds())


def set_cooldown(user_id: int, game_name: str) -> None:
    """Устанавливает кулдаун для игры."""
    if user_id not in user_cooldowns:
        user_cooldowns[user_id] = {}
    
    user_cooldowns[user_id][game_name] = datetime.now()


def format_time_remaining(seconds: int) -> str:
    """Форматирует оставшееся время в читаемый вид."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours} ч. {minutes} мин."
    elif minutes > 0:
        return f"{minutes} мин. {seconds} сек."
    else:
        return f"{seconds} сек."