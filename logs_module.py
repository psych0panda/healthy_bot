import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from typing import List, Dict
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
LOG_DIR = "/srv/neuroboss/logs"
MAX_LOG_SIZE = 50 * 1024 * 1024  # 50MB максимальный размер лога для отправки
MAX_LINES = 1000  # Максимальное количество строк для отправки

# Список контейнеров (соответствует скрипту auto_update_simlink.sh)
CONTAINERS = [
    "infra-compose_api-service_1",
    "infra-compose_neuroboss-service_1", 
    "chroma",
    "infra-compose_rag-service_1",
    "infra-compose_agent-service_1"
]

class LogsModule:
    def __init__(self):
        self.log_dir = LOG_DIR
        
    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /logs - показывает список доступных сервисов"""
        keyboard = []
        
        # Создаем кнопки для каждого контейнера
        for container in CONTAINERS:
            log_file = os.path.join(self.log_dir, f"{container}.log")
            status = "🟢" if os.path.exists(log_file) else "🔴"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {container}", 
                    callback_data=f"get_log:{container}"
                )
            ])
        
        # Добавляем кнопку для получения всех логов
        keyboard.append([
            InlineKeyboardButton("📋 Все логи", callback_data="get_all_logs")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📊 **Доступные логи сервисов:**\n\n"
            "🟢 - лог доступен\n"
            "🔴 - лог недоступен\n\n"
            "Выберите сервис для получения лога:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_log_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки с логами"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "get_all_logs":
            await self._send_all_logs(query, context)
        elif query.data.startswith("get_log:"):
            container = query.data.split(":", 1)[1]
            await self._send_container_log(query, context, container)
    
    async def _send_container_log(self, query, context, container: str):
        """Отправляет лог конкретного контейнера"""
        log_file = os.path.join(self.log_dir, f"{container}.log")
        
        if not os.path.exists(log_file):
            await query.edit_message_text(
                f"❌ Лог для контейнера `{container}` недоступен",
                parse_mode='Markdown'
            )
            return
        
        try:
            # Получаем информацию о файле
            file_size = os.path.getsize(log_file)
            file_info = os.stat(log_file)
            
            # Читаем последние строки лога
            lines = await self._read_log_tail(log_file)
            
            if not lines:
                await query.edit_message_text(
                    f"📄 Лог контейнера `{container}` пуст",
                    parse_mode='Markdown'
                )
                return
            
            # Формируем сообщение
            message = f"📄 **Лог контейнера:** `{container}`\n\n"
            message += f"📊 **Информация:**\n"
            message += f"• Размер: {self._format_size(file_size)}\n"
            message += f"• Последнее изменение: {self._format_time(file_info.st_mtime)}\n"
            message += f"• Строк в логе: {len(lines)}\n\n"
            
            # Добавляем содержимое лога
            log_content = "\n".join(lines)
            
            # Если лог слишком большой, отправляем как файл
            if len(log_content.encode('utf-8')) > 4000:
                await self._send_log_as_file(query, context, container, log_content)
            else:
                message += f"```\n{log_content}\n```"
                await query.edit_message_text(
                    message,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Ошибка при чтении лога {container}: {e}")
            await query.edit_message_text(
                f"❌ Ошибка при чтении лога контейнера `{container}`: {str(e)}",
                parse_mode='Markdown'
            )
    
    async def _send_all_logs(self, query, context):
        """Отправляет сводку по всем логам"""
        message = "📊 **Сводка по всем логам:**\n\n"
        
        total_size = 0
        available_logs = 0
        
        for container in CONTAINERS:
            log_file = os.path.join(self.log_dir, f"{container}.log")
            
            if os.path.exists(log_file):
                file_size = os.path.getsize(log_file)
                file_info = os.stat(log_file)
                total_size += file_size
                available_logs += 1
                
                status = "🟢"
                size_info = self._format_size(file_size)
                last_modified = self._format_time(file_info.st_mtime)
            else:
                status = "🔴"
                size_info = "недоступен"
                last_modified = "недоступен"
            
            message += f"{status} **{container}**\n"
            message += f"   Размер: {size_info}\n"
            message += f"   Обновлен: {last_modified}\n\n"
        
        message += f"📈 **Общая статистика:**\n"
        message += f"• Доступно логов: {available_logs}/{len(CONTAINERS)}\n"
        message += f"• Общий размер: {self._format_size(total_size)}\n"
        
        # Добавляем кнопки для получения отдельных логов
        keyboard = []
        for container in CONTAINERS:
            log_file = os.path.join(self.log_dir, f"{container}.log")
            status = "🟢" if os.path.exists(log_file) else "🔴"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {container}", 
                    callback_data=f"get_log:{container}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _send_log_as_file(self, query, context, container: str, content: str):
        """Отправляет лог как файл"""
        try:
            # Создаем временный файл
            temp_file = f"/tmp/{container}_log.txt"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Отправляем файл
            with open(temp_file, 'rb') as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename=f"{container}_log.txt",
                    caption=f"📄 Лог контейнера {container}"
                )
            
            # Удаляем временный файл
            os.remove(temp_file)
            
            await query.edit_message_text(
                f"📄 Лог контейнера `{container}` отправлен как файл",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Ошибка при отправке файла лога {container}: {e}")
            await query.edit_message_text(
                f"❌ Ошибка при отправке лога контейнера `{container}`: {str(e)}",
                parse_mode='Markdown'
            )
    
    async def _read_log_tail(self, log_file: str, max_lines: int = MAX_LINES) -> List[str]:
        """Читает последние строки из лог-файла"""
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                return lines[-max_lines:] if len(lines) > max_lines else lines
        except Exception as e:
            logger.error(f"Ошибка при чтении файла {log_file}: {e}")
            return []
    
    def _format_size(self, size_bytes: int) -> str:
        """Форматирует размер файла в читаемый вид"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def _format_time(self, timestamp: float) -> str:
        """Форматирует время в читаемый вид"""
        from datetime import datetime
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%d.%m.%Y %H:%M:%S")

# Функции для интеграции с основным ботом
def setup_logs_module(application):
    """Настройка модуля логов для основного бота"""
    logs_module = LogsModule()
    
    # Регистрируем обработчики
    application.add_handler(
        CallbackQueryHandler(logs_module.handle_log_callback, pattern="^get_log:")
    )
    application.add_handler(
        CallbackQueryHandler(logs_module.handle_log_callback, pattern="^get_all_logs$")
    )
    
    return logs_module

# Пример использования в основном боте:
"""
from logs_module import setup_logs_module

def main():
    application = Application.builder().token(TOKEN).build()
    
    # Настройка модуля логов
    logs_module = setup_logs_module(application)
    
    # Добавляем команду /logs
    application.add_handler(CommandHandler("logs", logs_module.logs_command))
    
    application.run_polling()
"""
