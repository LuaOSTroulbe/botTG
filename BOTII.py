import os
import json
import asyncio
import logging
from typing import Dict, List
from dotenv import load_dotenv
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
TELEGRAM_BOT_TOKEN = os.getenv("8502439228:AAGUzo_uGZlNy0K1sCtimmEwb0uU-tQsaxk")
OPENROUTER_API_KEY = os.getenv("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")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище истории диалогов пользователей
user_conversations: Dict[int, List[Dict[str, str]]] = {}

# Конфигурация доступных моделей
MODELS = {
    "free": [
        "google/gemini-2.0-flash-exp:free",     # Быстрый, хорошее качество
        "google/gemma-2-9b-it:free",            # Компактная модель
        "meta-llama/llama-3.2-3b-instruct:free", # Легкая Llama
        "nousresearch/hermes-3-llama-3.1-405b:free" # Мощная модель
    ],
    "paid": [
        "openai/gpt-4o",
        "anthropic/claude-3.5-sonnet",
        "google/gemini-pro-1.5"
    ]
}

class OpenRouterAI:
    """Класс для работы с OpenRouter API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "http://localhost:8000",  # Замените на ваш сайт
            "X-Title": "ВацапочкИИ",              # Название вашего приложения
            "Content-Type": "application/json"
        }
    
    async def get_response(self, messages: List[Dict[str, str]], model: str = "google/gemini-2.0-flash-exp:free") -> str:
        """Получение ответа от AI модели"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "top_p": 1,
                    "frequency_penalty": 0,
                    "presence_penalty": 0
                }
                
                response = await client.post(
                    OPENROUTER_API_URL,
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"API Error: {response.status_code} - {response.text}")
                    return f"⚠️ Ошибка API: {response.status_code}"
                    
        except httpx.TimeoutException:
            return "⏰ Превышено время ожидания ответа"
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return f"❌ Произошла ошибка: {str(e)}"

# Инициализация AI клиента
ai_client = OpenRouterAI(OPENROUTER_API_KEY)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    welcome_message = (
        "Привет! я ВацапочкИИ\n\n"
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/help - Помощь и список моделей\n"
        "/new - Начать новый диалог\n"
        "/model - Выбрать модель AI\n"
        "/models - Показать доступные модели\n\n"
        "Просто напишите мне сообщение, и я отвечу!"
    )
    
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = (
        "**ВацапочкИИ команды**\n\n"
        "**Команды:**\n"
        "/start - Запуск бота\n"
        "/help - Это сообщение\n"
        "/new - Начать новый диалог\n"
        "/model [название] - Выбрать модель\n"
        "/models - Показать модели\n\n"
        "**Бесплатные модели:**\n"
    )
    
    for model in MODELS["free"]:
        help_text += f"• `{model}`\n"
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def new_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начать новый диалог"""
    user_id = update.effective_user.id
    if user_id in user_conversations:
        del user_conversations[user_id]
    
    await update.message.reply_text("🆕 Диалог очищен. Можете начинать новый разговор!")

async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать доступные модели"""
    models_text = "📋 **Доступные модели:**\n\n**Бесплатные:**\n"
    
    for model in MODELS["free"]:
        models_text += f"• `{model}`\n"
    
    models_text += "\nВыберите модель командой /model [название]"
    
    await update.message.reply_text(models_text, parse_mode='Markdown')

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выбор модели AI"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите название модели\n"
            "Пример: `/model google/gemini-2.0-flash-exp:free`",
            parse_mode='Markdown'
        )
        return
    
    model_name = context.args[0]
    
    # Проверяем, есть ли такая модель
    all_models = MODELS["free"] + MODELS["paid"]
    if model_name not in all_models:
        await update.message.reply_text(f"❌ Модель '{model_name}' не найдена")
        return
    
    # Сохраняем выбранную модель для пользователя
    context.user_data["selected_model"] = model_name
    
    await update.message.reply_text(f"✅ Выбрана модель: `{model_name}`", parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Инициализация истории диалога
    if user_id not in user_conversations:
        user_conversations[user_id] = [
            {"role": "system", "content": "Ты полезный и дружелюбный AI ассистент в Telegram."}
        ]
    
    # Добавляем сообщение пользователя в историю
    user_conversations[user_id].append({"role": "user", "content": user_message})
    
    # Показываем статус "печатает"
    await update.message.chat.send_action(action="typing")
    
    # Получаем выбранную модель или используем по умолчанию
    model = context.user_data.get("selected_model", "google/gemini-2.0-flash-exp:free")
    
    # Получаем ответ от AI
    try:
        ai_response = await ai_client.get_response(user_conversations[user_id], model)
        
        # Добавляем ответ AI в историю
        user_conversations[user_id].append({"role": "assistant", "content": ai_response})
        
        # Отправляем ответ (разбиваем длинные сообщения)
        if len(ai_response) > 4000:
            for i in range(0, len(ai_response), 4000):
                await update.message.reply_text(ai_response[i:i+4000])
        else:
            await update.message.reply_text(ai_response)
            
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при получении ответа: {str(e)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.message:
        await update.message.reply_text("❌ Произошла внутренняя ошибка. Попробуйте позже.")

def main() -> None:
    """Запуск бота"""
    # Проверяем наличие токенов
    if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY:
        raise ValueError("Необходимо указать TELEGRAM_BOT_TOKEN и OPENROUTER_API_KEY в .env файле")
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("new", new_chat_command))
    application.add_handler(CommandHandler("model", model_command))
    application.add_handler(CommandHandler("models", models_command))
    
    # Регистрируем обработчик сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("Запуск бота...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
