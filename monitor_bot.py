#!/usr/bin/env python3
"""
Скрипт для мониторинга и автоматического перезапуска Telegram бота при необходимости.
Проверяет статус бота и перезапускает его, если бот не отвечает или не работает.
"""

import datetime
import logging
import os
import subprocess
import sys
import time

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("monitor_bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Константы
HEARTBEAT_FILE = "bot_running.txt"
BOT_RESTART_SCRIPT = "start_workflow_bot.sh"
MAX_HEARTBEAT_AGE = 600  # 10 минут
MONITOR_INTERVAL = 300  # 5 минут

def is_bot_running():
    """Проверяет, работает ли бот на основе файла heartbeat."""
    if not os.path.exists(HEARTBEAT_FILE):
        logger.warning("Файл heartbeat не найден. Бот не запущен.")
        return False
    
    try:
        stat = os.stat(HEARTBEAT_FILE)
        last_modified = stat.st_mtime
        now = time.time()
        age = now - last_modified
        
        if age > MAX_HEARTBEAT_AGE:
            logger.warning(f"Файл heartbeat устарел (возраст: {age:.1f} секунд, максимум: {MAX_HEARTBEAT_AGE}). Бот не отвечает.")
            return False
        
        # Проверим содержимое файла
        with open(HEARTBEAT_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                logger.warning("Файл heartbeat пуст. Возможно, бот не работает корректно.")
                return False
        
        logger.info(f"Бот работает (heartbeat возраст: {age:.1f} секунд).")
        return True
    except Exception as e:
        logger.error(f"Ошибка при проверке файла heartbeat: {e}")
        return False

def restart_bot():
    """Перезапускает бота при помощи скрипта."""
    logger.info("Попытка перезапуска бота...")
    try:
        # Остановить бота, если он ещё запущен (но не отвечает)
        subprocess.run(["bash", "stop_workflow_bot.sh"], check=False)
        time.sleep(5)  # Ждем немного перед запуском
        
        # Запустить бота заново
        subprocess.run(["bash", BOT_RESTART_SCRIPT], check=True)
        logger.info("Команда перезапуска бота выполнена успешно.")
        
        # Подождем немного и проверим, запустился ли бот
        time.sleep(30)
        if is_bot_running():
            logger.info("Бот успешно перезапущен и работает.")
            return True
        else:
            logger.error("Бот не запустился после перезапуска.")
            return False
    except Exception as e:
        logger.error(f"Ошибка при перезапуске бота: {e}")
        return False

def main():
    """Основная функция мониторинга."""
    logger.info(f"Запуск мониторинга бота в {datetime.datetime.now()}")
    
    try:
        if not is_bot_running():
            logger.warning("Бот не работает. Перезапуск...")
            restart_success = restart_bot()
            if restart_success:
                logger.info("Бот успешно перезапущен.")
            else:
                logger.error("Не удалось перезапустить бота. Необходимо ручное вмешательство.")
        else:
            logger.info("Бот работает нормально.")
    except Exception as e:
        logger.error(f"Ошибка в процессе мониторинга: {e}")
    
    logger.info(f"Мониторинг завершен в {datetime.datetime.now()}")

if __name__ == "__main__":
    main()