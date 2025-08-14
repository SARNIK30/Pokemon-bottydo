#!/bin/bash

# Скрипт для запуска Telegram бота в режиме 24/7 с автоматическим перезапуском
# Автор: Replit AI

# Директория для хранения PID бота
PID_DIR="./run"
mkdir -p $PID_DIR

# Файл для хранения PID бота
PID_FILE="$PID_DIR/bot.pid"

# Файл для логов
LOG_FILE="./pokemon_bot.log"

# Функция для запуска бота
start_bot() {
    echo "$(date) - Запуск бота Pokemon в режиме 24/7..." >> $LOG_FILE
    
    # Запускаем бота в фоновом режиме
    nohup python run_polling_bot.py >> $LOG_FILE 2>&1 &
    
    # Сохраняем PID процесса
    echo $! > $PID_FILE
    
    echo "$(date) - Бот запущен с PID $(cat $PID_FILE)" >> $LOG_FILE
    echo "Бот запущен с PID $(cat $PID_FILE)"
}

# Функция для остановки бота
stop_bot() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        echo "$(date) - Остановка бота с PID $PID..." >> $LOG_FILE
        
        # Проверяем, существует ли процесс
        if ps -p $PID > /dev/null; then
            # Отправляем сигнал для корректного завершения
            kill -15 $PID
            
            # Ждем завершения процесса
            for i in {1..10}; do
                if ! ps -p $PID > /dev/null; then
                    break
                fi
                sleep 1
            done
            
            # Если процесс все еще не завершился, завершаем его принудительно
            if ps -p $PID > /dev/null; then
                echo "$(date) - Процесс не завершился, принудительное завершение..." >> $LOG_FILE
                kill -9 $PID
            fi
        else
            echo "$(date) - Процесс с PID $PID не найден" >> $LOG_FILE
        fi
        
        # Удаляем файл PID
        rm -f $PID_FILE
        echo "$(date) - Бот остановлен" >> $LOG_FILE
        echo "Бот остановлен"
    else
        echo "$(date) - Файл PID не найден, бот не запущен" >> $LOG_FILE
        echo "Бот не запущен"
    fi
}

# Функция для проверки состояния бота
check_bot() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        
        # Проверяем, существует ли процесс
        if ps -p $PID > /dev/null; then
            echo "$(date) - Бот работает с PID $PID" >> $LOG_FILE
            echo "Бот работает с PID $PID"
            return 0
        else
            echo "$(date) - Процесс с PID $PID не найден, перезапуск..." >> $LOG_FILE
            echo "Процесс с PID $PID не найден, перезапуск..."
            rm -f $PID_FILE
            return 1
        fi
    else
        echo "$(date) - Файл PID не найден, бот не запущен" >> $LOG_FILE
        echo "Бот не запущен, запуск..."
        return 1
    fi
}

# Функция для работы с ботом в режиме демона
daemon_mode() {
    echo "$(date) - Запуск бота в режиме демона..." >> $LOG_FILE
    
    # Останавливаем бота, если он уже запущен
    stop_bot
    
    # Запускаем бота
    start_bot
    
    # Бесконечный цикл для проверки состояния бота
    while true; do
        # Проверяем состояние бота
        check_bot || start_bot
        
        # Пауза между проверками
        sleep 60
    done
}

# Главный блок скрипта
case "$1" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        stop_bot
        sleep 2
        start_bot
        ;;
    check)
        check_bot
        ;;
    daemon)
        daemon_mode
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|check|daemon}"
        exit 1
        ;;
esac

exit 0