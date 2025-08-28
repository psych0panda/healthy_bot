# HealthCheck Telegram Бот

Telegram бот для мониторинга сервисов и здоровья системы. Поддерживает мониторинг HTTP сервисов, Docker контейнеров и системных процессов.

## Возможности

### 📱 Основные команды
- `/start` - Начать работу с ботом
- `/help` - Показать справку по командам
- `/hello` - Поздороваться с ботом
- `/time` - Показать текущее время
- `/echo <текст>` - Повторить ваш текст
- `/info` - Информация о боте и пользователе

### 📊 Команды мониторинга
- `/status` - Проверить статус всех сервисов
- `/services` - Показать список мониторимых сервисов

### 🔧 Поддерживаемые типы сервисов
- **HTTP/HTTPS** - веб-сервисы и API
  - 2xx, 3xx, 4xx (включая 404) - сервер работает нормально
  - 5xx - ошибка сервера, сервис не работает
- **Docker** - контейнеры Docker
- **Systemd** - системные сервисы (redis, nginx, postgresql и др.)
- **Process** - системные процессы

## Установка и настройка

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Создание бота в Telegram

1. Откройте Telegram и найдите @BotFather
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Сохраните полученный токен

### 3. Настройка переменных окружения

Создайте файл `.env` в корневой папке проекта:

```bash
cp env_example.txt .env
```

Отредактируйте файл `.env` и вставьте ваш токен и настройте сервисы:

```
TELEGRAM_BOT_TOKEN=ваш_токен_бота_здесь
SERVICES_TO_MONITOR=web:http://localhost:8080,nginx:docker:nginx,db:docker:postgres,python:process:python
```

### Формат конфигурации сервисов

Переменная `SERVICES_TO_MONITOR` содержит список сервисов для мониторинга. Поддерживаются два формата:

#### 1. Упрощенный формат (рекомендуется)
```
http://localhost:8080,http://localhost:3000,postgresql,nginx,redis,wg-quick@wg0,minio,docker:jenkins
```

#### 2. Полный формат
```
web:http://localhost:8080,api:https://api.example.com,db:docker:postgres,app:process:python
```

**Автоматическое определение типов:**
- **HTTP/HTTPS** - автоматически определяется по протоколу
- **Docker** - автоматически определяется для известных сервисов (postgresql, nginx, redis, jenkins, minio)
- **Process** - автоматически определяется для системных сервисов (wg-quick, ssh, cron)

**Примеры:**
- `http://localhost:8080` - HTTP сервис
- `https://api.example.com/health` - HTTPS API
- `postgresql` - Docker контейнер PostgreSQL
- `nginx` - Docker контейнер Nginx
- `redis` - Docker контейнер Redis
- `wg-quick@wg0` - Системный процесс WireGuard
- `docker:jenkins` - Docker контейнер Jenkins
- `docker:eager_robinson` - Docker контейнер с именем eager_robinson

### 4. Запуск бота

```bash
python healthcheck_bot.py
```

### 5. Тестирование

Для проверки работы мониторинга:

```bash
# Тест парсинга конфигурации
python test_monitor.py

# Тест полного мониторинга
python test_full_monitor.py
```

## Использование

После запуска бота:

1. Найдите вашего бота в Telegram по имени
2. Отправьте команду `/start`
3. Используйте доступные команды

### Примеры команд

**Основные команды:**
```
/start - Начать работу
/help - Показать справку
/hello - Поздороваться
/time - Текущее время
/echo Привет, мир! - Повторить текст
/info - Информация о боте
```

**Команды мониторинга:**
```
/status - Проверить все сервисы
/services - Показать список сервисов
```

## Структура проекта

```
healthcheck/
├── healthcheck_bot.py        # Бот с мониторингом сервисов
├── service_monitor.py        # Модуль мониторинга сервисов
├── test_monitor.py           # Тест парсинга конфигурации
├── test_full_monitor.py      # Тест полного мониторинга
├── requirements.txt          # Зависимости Python
├── env_example.txt           # Пример переменных окружения
├── README.md                # Этот файл
└── venv/                    # Виртуальное окружение
```

## Технические детали

- **Python 3.7+**
- **python-telegram-bot 20.7** - Telegram Bot API
- **psutil 5.9.6** - мониторинг системных процессов
- **requests 2.31.0** - HTTP запросы
- **docker 6.1.3** - работа с Docker контейнерами
- **schedule 1.2.0** - планировщик задач
- **Асинхронная обработка** сообщений
- **Многопоточность** для мониторинга
- **Логирование** всех действий
- **Обработка ошибок**

## Добавление новых команд

Для добавления новой команды:

1. Создайте новый метод в классе `SimpleBot`
2. Добавьте обработчик в метод `_setup_handlers`
3. Обновите справку в командах `/start` и `/help`

Пример:

```python
async def new_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Новая команда!")

# В _setup_handlers:
self.application.add_handler(CommandHandler("new", self.new_command))
```

## Логирование

Бот ведет логи всех действий. Логи выводятся в консоль с временными метками.

## Безопасность

- Токен бота хранится в переменных окружения
- Файл `.env` добавлен в `.gitignore`
- Обработка ошибок для предотвращения падения бота
