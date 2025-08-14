#!/usr/bin/env python3
"""
Скрипт для проверки статуса Telegram бота.
Проверяет наличие необходимых переменных окружения и доступность файла heartbeat.
"""

import os
import sys
import time
import datetime

def check_bot_token():
    """Проверка доступности BOT_TOKEN."""
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("[🔴] BOT_TOKEN недоступен или не настроен.")
        return False
    else:
        print(f"[🟢] BOT_TOKEN настроен (первые 5 символов: {token[:5]}...)")
        return True

def check_admin_ids():
    """Проверка доступности ADMIN_IDS."""
    admin_ids = os.environ.get("ADMIN_IDS")
    if not admin_ids:
        print("[🔴] ADMIN_IDS недоступен или не настроен.")
        return False
    else:
        print(f"[🟢] ADMIN_IDS настроен: {admin_ids}")
        return True

def check_webhook_url():
    """Проверка доступности WEBHOOK_URL."""
    webhook_url = os.environ.get("WEBHOOK_URL")
    if not webhook_url:
        print("[🔴] WEBHOOK_URL недоступен или не настроен.")
        return False
    else:
        print(f"[🟢] WEBHOOK_URL настроен: {webhook_url}")
        return True

def check_heartbeat_file():
    """Проверка наличия и актуальности файла heartbeat."""
    heartbeat_file = "bot_running.txt"
    if not os.path.exists(heartbeat_file):
        print(f"[🔴] Файл heartbeat '{heartbeat_file}' не найден. Бот, возможно, не запущен.")
        return False
    
    # Проверка времени последнего изменения файла
    file_mtime = os.path.getmtime(heartbeat_file)
    now = time.time()
    time_diff = now - file_mtime
    
    # Если файл не обновлялся более 30 минут, считаем, что бот не активен
    if time_diff > 1800:  # 30 минут
        print(f"[🔴] Файл heartbeat устарел. Последнее обновление: {datetime.datetime.fromtimestamp(file_mtime)}")
        print(f"[🔴] Прошло {time_diff:.0f} секунд с последнего обновления.")
        return False
    else:
        print(f"[🟢] Файл heartbeat актуален. Последнее обновление: {datetime.datetime.fromtimestamp(file_mtime)}")
        print(f"[🟢] Прошло {time_diff:.0f} секунд с последнего обновления.")
        return True

def check_bot_log():
    """Проверка наличия и свежести логов бота."""
    log_file = "pokemon_bot_workflow.log"
    if not os.path.exists(log_file):
        log_file = "pokemon_bot.log"
        if not os.path.exists(log_file):
            print(f"[🔴] Файлы логов не найдены.")
            return False
    
    # Проверка времени последнего изменения файла
    file_mtime = os.path.getmtime(log_file)
    now = time.time()
    time_diff = now - file_mtime
    
    # Если файл не обновлялся более 30 минут, считаем, что бот не активен
    if time_diff > 1800:  # 30 минут
        print(f"[🔴] Лог {log_file} устарел. Последнее обновление: {datetime.datetime.fromtimestamp(file_mtime)}")
        print(f"[🔴] Прошло {time_diff:.0f} секунд с последнего обновления.")
        return False
    else:
        print(f"[🟢] Лог {log_file} актуален. Последнее обновление: {datetime.datetime.fromtimestamp(file_mtime)}")
        print(f"[🟢] Прошло {time_diff:.0f} секунд с последнего обновления.")
        
        # Проверка последних записей в логе
        try:
            with open(log_file, 'r') as f:
                # Получаем последние 5 строк лога
                last_lines = list(f)[-5:]
                print("\nПоследние записи в логе:")
                for line in last_lines:
                    print(f"  {line.strip()}")
        except Exception as e:
            print(f"[🔴] Ошибка при чтении лога: {e}")
        
        return True

def main():
    """Основная функция проверки статуса бота."""
    print("===== Проверка статуса Telegram бота Pokémon =====")
    print(f"Текущее время: {datetime.datetime.now()}")
    print("\n1. Проверка переменных окружения:")
    
    token_ok = check_bot_token()
    admin_ids_ok = check_admin_ids()
    webhook_url_ok = check_webhook_url()
    
    print("\n2. Проверка состояния бота:")
    heartbeat_ok = check_heartbeat_file()
    log_ok = check_bot_log()
    
    # Общий статус
    print("\n===== Общий статус бота =====")
    if token_ok and admin_ids_ok and (heartbeat_ok or log_ok):
        print("[🟢] Бот, вероятно, работает нормально.")
    else:
        print("[🔴] Бот, вероятно, не работает или есть проблемы.")
        
        # Рекомендации по устранению проблем
        print("\nРекомендации:")
        if not token_ok or not admin_ids_ok or not webhook_url_ok:
            print("1. Проверьте наличие и правильность переменных окружения.")
        if not heartbeat_ok or not log_ok:
            print("2. Попробуйте перезапустить бота с помощью workflow:")
            print("   - Остановите текущий процесс бота")
            print("   - Запустите workflow 'pokemon_bot'")

if __name__ == "__main__":
    main()