#!/usr/bin/env python3

import subprocess
import time
import os
import signal
import sys
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot_launcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("bot_launcher")

def run_bot():
    """Запускает бота и перезапускает его при сбоях."""
    logger.info("Запуск Telegram Покемон бота...")
    
    try:
        # Запускаем процесс бота
        process = subprocess.Popen(
            ["python", "run_polling_bot.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        logger.info(f"Бот запущен с PID {process.pid}")
        
        # Читаем вывод в реальном времени
        for line in process.stdout:
            print(line, end="")
            
        # Если процесс завершился, проверяем код возврата
        return_code = process.wait()
        logger.warning(f"Бот завершил работу с кодом {return_code}")
        return return_code
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        return 1

def main():
    """Основной цикл работы лаунчера."""
    logger.info("Запуск лаунчера бота Покемон")
    
    # Обработчик сигналов для корректного завершения
    def signal_handler(sig, frame):
        logger.info("Получен сигнал завершения. Завершение работы...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    retry_count = 0
    max_retries = 5
    wait_time = 10  # начальное время ожидания перед перезапуском (в секундах)
    
    while retry_count < max_retries:
        return_code = run_bot()
        
        if return_code == 0:
            logger.info("Бот завершил работу успешно")
            break
        
        retry_count += 1
        logger.warning(f"Попытка перезапуска {retry_count}/{max_retries} через {wait_time} секунд...")
        time.sleep(wait_time)
        
        # Увеличиваем время ожидания перед следующим перезапуском
        wait_time = min(wait_time * 2, 300)  # максимум 5 минут
    
    if retry_count >= max_retries:
        logger.error(f"Достигнуто максимальное количество попыток перезапуска ({max_retries})")
    
    logger.info("Лаунчер завершает работу")

if __name__ == "__main__":
    main()
