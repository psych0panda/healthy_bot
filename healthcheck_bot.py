import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
from service_monitor import ServiceMonitor

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class HealthCheckBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        
        self.application = Application.builder().token(self.token).build()
        self.service_monitor = ServiceMonitor()
        self.last_statuses = []
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("hello", self.hello_command))
        self.application.add_handler(CommandHandler("time", self.time_command))
        self.application.add_handler(CommandHandler("echo", self.echo_command))
        self.application.add_handler(CommandHandler("info", self.info_command))
        
        # Команды мониторинга
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("services", self.services_command))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        welcome_message = f"""
Привет, {user.first_name}! 👋

Я бот для мониторинга сервисов и здоровья системы.

Доступные команды:
/start - Начать работу с ботом
/help - Показать справку
/hello - Поздороваться
/time - Показать текущее время
/echo <текст> - Повторить ваш текст
/info - Информация о боте

📊 Команды мониторинга:
/status - Проверить статус всех сервисов
/services - Показать список мониторимых сервисов

Попробуйте команду /status для проверки сервисов!
        """
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """🤖 Справка по командам:

📱 Основные команды:
/start - Начать работу с ботом
/help - Показать эту справку
/hello - Поздороваться с ботом
/time - Показать текущее время
/echo <текст> - Повторить ваш текст
/info - Информация о боте

📊 Команды мониторинга:
/status - Проверить статус всех сервисов
/services - Показать список мониторимых сервисов

💡 Примеры использования:
/echo Привет, мир!
/status - проверить все сервисы"""
        await update.message.reply_text(help_text)
    
    async def hello_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /hello"""
        user = update.effective_user
        greetings = [
            f"Привет, {user.first_name}! 😊",
            f"Здравствуй, {user.first_name}! 👋",
            f"Добрый день, {user.first_name}! 🌟",
            f"Приветствую, {user.first_name}! ✨"
        ]
        import random
        await update.message.reply_text(random.choice(greetings))
    
    async def time_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /time"""
        from datetime import datetime
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        await update.message.reply_text(f"🕐 Текущее время: {current_time}")
    
    async def echo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /echo"""
        if not context.args:
            await update.message.reply_text("Пожалуйста, укажите текст для повторения.\nПример: /echo Привет, мир!")
            return
        
        text = ' '.join(context.args)
        await update.message.reply_text(f"📢 {text}")
    
    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /info"""
        user = update.effective_user
        username = user.username or 'Не указан'
        last_name = user.last_name or ''
        
        info_text = f"""ℹ️ Информация о боте:

👤 Пользователь: {user.first_name} {last_name}
🆔 ID пользователя: {user.id}
👤 Username: @{username}

🤖 Бот: HealthCheck Bot
📅 Версия: 1.0.0
🔧 Функции: Мониторинг сервисов

💬 Всего команд: 8"""
        await update.message.reply_text(info_text)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        await update.message.reply_text("🔍 Проверяю статус сервисов...")
        
        try:
            statuses = self.service_monitor.check_all_services()
            self.last_statuses = statuses
            
            if not statuses:
                await update.message.reply_text("⚠️ Нет настроенных сервисов для мониторинга.\nНастройте SERVICES_TO_MONITOR в .env файле")
                return
            
            summary = self.service_monitor.get_summary(statuses)
            await update.message.reply_text(summary)
            
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса: {e}")
            await update.message.reply_text(f"❌ Ошибка при проверке статуса: {str(e)}")
    
    async def services_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /services"""
        services = self.service_monitor.services
        
        if not services:
            await update.message.reply_text("📋 Нет настроенных сервисов.\n\nНастройте SERVICES_TO_MONITOR в .env файле:\n\nПример:\nweb:http://localhost:8080\nnginx:docker:nginx\ndb:docker:postgres\npython:process:python")
            return
        
        services_text = "📋 Настроенные сервисы:\n\n"
        for service in services:
            services_text += f"• **{service['name']}** ({service['type']}): {service['config']}\n"
        
        await update.message.reply_text(services_text)
    
    def run(self):
        """Запуск бота"""
        logger.info("Запуск HealthCheck бота...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Главная функция"""
    try:
        bot = HealthCheckBot()
        bot.run()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

if __name__ == '__main__':
    main()
