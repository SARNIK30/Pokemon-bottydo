#!/usr/bin/env python3
"""
Простой Flask-сервер для обработки запросов состояния бота.
Используется для мониторинга с помощью UptimeRobot или аналогичных сервисов.
"""

import datetime
import os
import logging
from flask import Flask, jsonify

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
HEARTBEAT_FILE = "bot_running.txt"
BOT_LOGS = "pokemon_bot_workflow.log"
MAX_HEARTBEAT_AGE = 600  # 10 минут


@app.route('/ping', methods=['GET'])
def ping():
    """Эндпоинт для проверки доступности сервиса."""
    return jsonify({
        "status": "online",
        "timestamp": datetime.datetime.now().isoformat(),
        "service": "Pokemon Bot"
    }), 200


@app.route('/health', methods=['GET'])
def health_check():
    """Эндпоинт для проверки здоровья бота."""
    # Проверяем наличие heartbeat-файла
    heartbeat_exists = os.path.exists(HEARTBEAT_FILE)
    
    # Проверяем возраст heartbeat-файла
    heartbeat_age = None
    heartbeat_content = None
    if heartbeat_exists:
        try:
            stat = os.stat(HEARTBEAT_FILE)
            now = datetime.datetime.now().timestamp()
            heartbeat_age = now - stat.st_mtime
            
            # Читаем содержимое heartbeat-файла
            with open(HEARTBEAT_FILE, 'r') as f:
                heartbeat_content = f.read().strip()
        except Exception as e:
            logger.error(f"Ошибка при проверке heartbeat-файла: {e}")
    
    # Проверяем наличие и размер файла логов
    log_exists = os.path.exists(BOT_LOGS)
    log_size = None
    log_time = None
    if log_exists:
        try:
            stat = os.stat(BOT_LOGS)
            log_size = stat.st_size
            log_time = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
        except Exception as e:
            logger.error(f"Ошибка при проверке файла логов: {e}")
    
    # Определяем статус бота
    status = "healthy"
    if not heartbeat_exists:
        status = "down"
    elif heartbeat_age and heartbeat_age > MAX_HEARTBEAT_AGE:
        status = "unresponsive"
    elif not heartbeat_content:
        status = "unhealthy"
    
    # Возвращаем информацию о состоянии бота
    return jsonify({
        "status": status,
        "heartbeat": {
            "exists": heartbeat_exists,
            "age_seconds": heartbeat_age,
            "content": heartbeat_content
        },
        "logs": {
            "exists": log_exists,
            "size_bytes": log_size,
            "last_modified": log_time
        },
        "timestamp": datetime.datetime.now().isoformat(),
        "monitor_version": "1.0.0"
    }), 200 if status == "healthy" else 503


@app.route('/', methods=['GET'])
def root():
    """Корневой эндпоинт с информацией о боте."""
    return jsonify({
        "name": "Pokemon Telegram Bot",
        "status": "running",
        "endpoints": {
            "/ping": "Basic ping endpoint for uptime monitoring",
            "/health": "Detailed health check of the bot"
        },
        "timestamp": datetime.datetime.now().isoformat()
    }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)