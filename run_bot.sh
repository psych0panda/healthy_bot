#!/bin/bash

# Скрипт для запуска Telegram бота

echo "🤖 Запуск простого Telegram бота..."

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено. Создаем..."
    python3 -m venv venv
fi

# Активируем виртуальное окружение
echo "📦 Активация виртуального окружения..."
source venv/bin/activate

# Устанавливаем зависимости
echo "📥 Установка зависимостей..."
pip install -r requirements.txt

# Проверяем наличие .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден!"
    echo "📝 Создайте файл .env с вашим токеном бота:"
    echo "   TELEGRAM_BOT_TOKEN=ваш_токен_здесь"
    echo ""
    echo "💡 Используйте env_example.txt как пример"
    exit 1
fi

# Запускаем бота
echo "🚀 Запуск бота..."
python bot.py
