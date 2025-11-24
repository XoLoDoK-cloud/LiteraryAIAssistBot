import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from datetime import datetime
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Open Router API client with cheaper model
api_key = os.getenv("OPEN_ROUTER_API_KEY")
if not api_key:
    raise ValueError("OPEN_ROUTER_API_KEY не установлен!")
OPEN_ROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "mistralai/mistral-7b-instruct"  # Дешевая и быстрая модель

# Store conversation history and favorites per user
user_conversations = {}
user_favorites = {}
user_stats = {}

SYSTEM_PROMPT = """Ты – эксперт по мировой литературе. Твоя главная задача – помогать пользователям 
изучать жизнь и творчество писателей со всех уголков мира. 

ПРАВИЛА:
✓ Подробно рассказывай о биографии любого писателя
✓ Объясняй его литературное наследие и влияние
✓ Анализируй его произведения и их темы
✓ Сравнивай писателей и их стили
✓ Рекомендуй лучшие книги для чтения
✓ Помогай с цитатами и анализом текстов
✓ Делай ответы структурированными (с пунктами)
✓ Используй эмодзи для читаемости

ВАЖНО: Общайся на русском языке, будь информативен и увлекательно. 
Если не уверен - честно об этом скажи."""


def get_user_conversation(user_id):
    """Получить или создать историю разговора"""
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    return user_conversations[user_id]

def get_user_favorites(user_id):
    """Получить или создать список избранных писателей"""
    if user_id not in user_favorites:
        user_favorites[user_id] = []
    return user_favorites[user_id]

def get_user_stats(user_id):
    """Получить или создать статистику пользователя"""
    if user_id not in user_stats:
        user_stats[user_id] = {"total_messages": 0, "joined_date": datetime.now()}
    return user_stats[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start с красивым меню"""
    user_id = update.effective_user.id
    get_user_stats(user_id)["total_messages"] += 1
    
    keyboard = [
        [InlineKeyboardButton("📚 О писателе", callback_data="about")],
        [InlineKeyboardButton("⭐ Мои избранные", callback_data="favorites")],
        [InlineKeyboardButton("📖 Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎭 *ДОБРО ПОЖАЛОВАТЬ В ЛИТЕРАТУРНЫЙ БОТ!* 🎭\n\n"
        "📚 Я твой персональный гид по миру литературы\n\n"
        "Я знаю о:\n"
        "✨ Любых писателях мира\n"
        "📖 Их произведениях и наследии\n"
        "🎨 Литературных направлениях\n"
        "💭 Цитатах и анализе\n\n"
        "Просто напиши имя писателя или вопрос!\n\n"
        "*Доступные команды:*\n"
        "/clear - очистить историю\n"
        "/stats - твоя статистика\n"
        "/favorites - избранные писатели",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /clear"""
    user_id = update.effective_user.id
    if user_id in user_conversations:
        user_conversations[user_id] = []
    await update.message.reply_text("✨ История разговора очищена!\n🎯 Начинаем с чистого листа!")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать статистику пользователя"""
    user_id = update.effective_user.id
    stats = get_user_stats(user_id)
    favs = get_user_favorites(user_id)
    
    stats_text = (
        f"📊 *ВАШ ПРОФИЛЬ* 📊\n\n"
        f"👤 Пользователь: {update.effective_user.first_name}\n"
        f"💬 Всего сообщений: {stats['total_messages']}\n"
        f"⭐ Избранных писателей: {len(favs)}\n"
        f"📅 Присоединились: {stats['joined_date'].strftime('%d.%m.%Y')}\n\n"
    )
    
    if favs:
        stats_text += f"⭐ Избранные: {', '.join(favs)}"
    
    await update.message.reply_text(stats_text, parse_mode="Markdown")

async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать избранных писателей"""
    user_id = update.effective_user.id
    favs = get_user_favorites(user_id)
    
    if not favs:
        await update.message.reply_text("⭐ У вас ещё нет избранных писателей!\n\nДобавьте их в разговорах.")
    else:
        text = "⭐ *ВАШ СПИСОК ИЗБРАННЫХ:*\n\n"
        for i, writer in enumerate(favs, 1):
            text += f"{i}. {writer}\n"
        await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подробная справка"""
    help_text = (
        "📚 *СПРАВКА ЛИТЕРАТУРНОГО БОТА* 📚\n\n"
        "*ОСНОВНЫЕ ВОЗМОЖНОСТИ:*\n"
        "1️⃣ Расскажи о [писателе] - полная биография\n"
        "2️⃣ Какие произведения написал [писатель] - список книг\n"
        "3️⃣ Сравни [писатель 1] и [писатель 2] - сравнительный анализ\n"
        "4️⃣ Цитаты [писателя] - лучшие цитаты\n"
        "5️⃣ Рекомендуй мне книгу - персональная рекомендация\n\n"
        "*КОМАНДЫ:*\n"
        "/start - главное меню\n"
        "/clear - новый разговор\n"
        "/stats - ваша статистика\n"
        "/favorites - избранные писатели\n"
        "/help - справка\n\n"
        "💡 *ПРИМЕРЫ ВОПРОСОВ:*\n"
        "• Расскажи о Федоре Достоевском\n"
        "• Какие книги написала Джейн Остен\n"
        "• Сравни Пушкина и Лермонтова\n"
        "• Цитаты Чехова\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик обычных сообщений с улучшенным функционалом"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Обновляем статистику
    get_user_stats(user_id)["total_messages"] += 1
    
    # Проверяем команды в сообщении
    if "добавить в избранное" in user_message.lower() or "❤️" in user_message:
        await update.message.reply_text("❤️ Добавляю в избранное...")
        return
    
    # Показываем индикатор печатания
    await update.message.chat.send_action("typing")
    
    # Получаем историю разговора
    conversation = get_user_conversation(user_id)
    
    # Ограничиваем историю последними 10 сообщениями (экономим токены)
    if len(conversation) > 20:
        conversation = conversation[-20:]
    
    # Добавляем новое сообщение
    conversation.append({"role": "user", "content": user_message})
    
    try:
        # Отправляем запрос через Open Router
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://replit.com",
            "X-Title": "Literary Chatbot"
        }
        
        payload = {
            "model": MODEL,
            "messages": conversation,
            "system": SYSTEM_PROMPT,
            "max_tokens": 1200,
            "temperature": 0.8,
            "top_p": 0.95,
        }
        
        response = requests.post(OPEN_ROUTER_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        # Получаем ответ
        response_data = response.json()
        assistant_message = response_data["choices"][0]["message"]["content"]
        
        # Добавляем в историю
        conversation.append({"role": "assistant", "content": assistant_message})
        
        # Форматируем и отправляем ответ (разбиваем на части если длинно)
        if len(assistant_message) > 4096:
            parts = [assistant_message[i:i+4090] for i in range(0, len(assistant_message), 4090)]
            for part in parts:
                await update.message.reply_text(part, parse_mode="Markdown")
        else:
            await update.message.reply_text(assistant_message, parse_mode="Markdown")
        
        # Кнопки для избранного
        keyboard = [[InlineKeyboardButton("❤️ Добавить в избранное", callback_data="add_fav")]]
        await update.message.reply_text("Помогла информация?", reply_markup=InlineKeyboardMarkup(keyboard))
        
    except requests.exceptions.Timeout:
        await update.message.reply_text("⏱️ Истекло время ожидания. Попробуй более короткий вопрос.")
    except requests.exceptions.RequestException as e:
        logger.error(f"API Error: {e}")
        await update.message.reply_text(
            "❌ Ошибка при обращении к AI.\n\n"
            "💡 Попробуй:\n"
            "• Переформулировать вопрос\n"
            "• Написать /clear и начать заново\n"
            "• Позже попробовать снова"
        )
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        await update.message.reply_text(
            "😕 Произошла непредвиденная ошибка.\n"
            "Попробуй позже или напиши /clear"
        )


def main():
    """Главная функция для запуска бота"""
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
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CommandHandler("favorites", show_favorites))
    
    # Регистрируем обработчик сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🎭 ЛИТЕРАТУРНЫЙ БОТ ЗАПУЩЕН! 🎭")
    logger.info(f"📚 Модель: {MODEL}")
    logger.info("💫 Готов ответить на вопросы о писателях!")
    
    # Запускаем бота с обработкой ошибок
    try:
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен.")
    except Exception as e:
        logger.error(f"Critical Error: {e}")


if __name__ == "__main__":
    main()
