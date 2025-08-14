#!/bin/bash
# Скрипт для запуска покемон бота через Replit

# Очистить вебхук если он установлен
echo "Очищаем вебхук..."
python clear_webhook.py

# Запуск бота в режиме поллинга
echo "Запускаем бота в режиме поллинга..."
exec python run_polling_bot.py
