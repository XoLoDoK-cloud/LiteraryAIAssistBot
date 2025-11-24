import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Open Router API client
api_key = os.getenv("OPEN_ROUTER_API_KEY")
if not api_key:
    raise ValueError("OPEN_ROUTER_API_KEY не установлен!")
OPEN_ROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Store conversation history per user
user_conversations = {}

SYSTEM_PROMPT = """Ты – эксперт по мировой литературе. Твоя главная задача – помогать пользователям 
изучать жизнь и творчество писателей со всех уголков мира. 

Ты можешь:
- Подробно рассказывать о биографии любого писателя
- Объяснять его литературное наследие и влияние на мировую культуру
- Анализировать его произведения и их темы
- Сравнивать писателей и их стили
- Рекомендовать книги для чтения
- Помогать с цитатами и анализом текстов

Будь информативен, вежлив и увлекательно общайся на русском языке. 
Если ты не уверен в информации, честно об этом скажи."""


def get_user_conversation(user_id):
    """Получить или создать историю разговора для пользователя"""
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    return user_conversations[user_id]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    await update.message.reply_text(
        "👋 Привет! Я – литературный чат-бот!\n\n"
        "Я могу рассказать тебе о любом писателе мира, его жизни, творчестве и влиянии на литературу.\n\n"
        "Просто напиши имя писателя или вопрос о литературе!\n\n"
        "Команды:\n"
        "/clear – очистить историю разговора\n"
        "/help – справка"
    )


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /clear"""
    user_id = update.effective_user.id
    if user_id in user_conversations:
        user_conversations[user_id] = []
    await update.message.reply_text("✨ История разговора очищена. Давай начнём заново!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    await update.message.reply_text(
        "📚 Я литературный эксперт. Спроси меня о:\n"
        "• Биографии писателей\n"
        "• Их произведениях\n"
        "• Литературных направлениях\n"
        "• Анализе книг\n"
        "• Рекомендациях для чтения\n\n"
        "Команды:\n"
        "/start – главное меню\n"
        "/clear – очистить историю\n"
        "/help – эта справка"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик обычных сообщений"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Показываем индикатор печатания
    await update.message.chat.send_action("typing")
    
    # Получаем историю разговора пользователя
    conversation = get_user_conversation(user_id)
    
    # Добавляем новое сообщение в историю
    conversation.append({"role": "user", "content": user_message})
    
    try:
        # Отправляем запрос к Claude через Open Router
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": "anthropic/claude-3.5-sonnet",
            "messages": conversation,
            "system": SYSTEM_PROMPT,
            "max_tokens": 1024,
            "temperature": 0.7,
        }
        
        response = requests.post(OPEN_ROUTER_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        # Получаем ответ
        response_data = response.json()
        assistant_message = response_data["choices"][0]["message"]["content"]
        
        # Добавляем ответ в историю
        conversation.append({"role": "assistant", "content": assistant_message})
        
        # Отправляем ответ пользователю
        await update.message.reply_text(assistant_message)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            "❌ Извини, произошла ошибка при обработке твоего сообщения. "
            "Попробуй ещё раз или напиши /clear для очистки истории."
        )


def main():
    """Главная функция для запуска бота"""
    # Получаем токен из переменной окружения
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не установлен!")
        raise ValueError("Пожалуйста, установи TELEGRAM_BOT_TOKEN")
    
    # Создаём Application
    app = Application.builder().token(token).build()
    
    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_history))
    app.add_handler(CommandHandler("help", help_command))
    
    # Регистрируем обработчик сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🚀 Бот запущен! Нажми Ctrl+C для остановки.")
    
    # Запускаем бота
    app.run_polling()


if __name__ == "__main__":
    main()
