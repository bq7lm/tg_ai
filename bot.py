import json
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from datetime import datetime

# Загрузка переменных окружения из файла .env
load_dotenv()

# Токены и конфигурация из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ID администратора
ADMIN_ID = 6061124706  

# Файл для хранения пользователей
USER_FILE = "users.json"

# Загрузка пользователей
def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return json.load(f)
    return {}

# Сохранение пользователей
def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=2)

# Словарь пользователей: {user_id: username}
registered_users = load_users()

# История сообщений
user_histories = {}

# Инициализация клиента OpenRouter SDK
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# Лог сообщений
def log_message(update: Update):
    user = update.effective_user
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    text = update.message.text if update.message else ""
    print(f"[{now}] FROM {user.username or 'без username'} ({user.full_name}) [ID: {user.id}]: {text}")

# /start — регистрация
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    user = update.effective_user
    user_id = str(user.id)
    username = user.username or "неизвестно"

    if user_id not in registered_users:
        registered_users[user_id] = username
        save_users(registered_users)

    await update.message.reply_text("Привет! Я готов к работе.")

# Обычные сообщения
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)

    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_histories:
        user_histories[user_id] = [
            {"role": "system", "content": "Ты дружелюбный голосовой помощник."}
        ]

    user_histories[user_id].append({"role": "user", "content": text})

    try:
        response = client.chat.completions.create(
            model="mistralai/mistral-small-24b-instruct-2501:free",
            messages=user_histories[user_id],
            max_tokens=150,
        )
        answer = response.choices[0].message.content.strip()
        user_histories[user_id].append({"role": "assistant", "content": answer})

        await update.message.reply_text(answer)
    except Exception as e:
        print("Ошибка OpenRouter:", e)
        await update.message.reply_text("Извините, произошла ошибка при получении ответа от AI.")

# /ss — отправка сообщений админом
async def send_message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Команда доступна только администратору.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Использование: /ss <username_or_id> <текст>")
        return

    target = args[0]
    text = " ".join(args[1:])
    bot = context.bot

    chat_id = int(target) if target.isdigit() else f"@{target}"

    try:
        await bot.send_message(chat_id=chat_id, text=text)
        await update.message.reply_text(f"Сообщение отправлено {target}")
    except Exception as e:
        print("Ошибка отправки:", e)
        await update.message.reply_text(f"Не удалось отправить сообщение {target}")

# /image
async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    await update.message.reply_text("В разработке")

# /text
async def text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    await update.message.reply_text("В разработке")

# /reset
async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    user_id = update.effective_user.id
    if user_id in user_histories:
        del user_histories[user_id]
    await update.message.reply_text("Контекст сброшен.")

# /ss22users
async def ss22users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Команда доступна только администратору.")
        return

    if not registered_users:
        await update.message.reply_text("Пользователи не найдены.")
        return

    user_list = [f"ID: {uid}, Username: @{username}" for uid, username in registered_users.items()]
    await update.message.reply_text("Пользователи:\n" + "\n".join(user_list))

# Лог всех команд
async def log_all_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)  # Только логирует

# Запуск
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ss", send_message_command))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(CommandHandler("text", text_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("ss22users", ss22users_command))

    # Лог команд
    app.add_handler(MessageHandler(filters.COMMAND, log_all_commands))
    # Ответы на обычные сообщения
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Бот запущен")
    app.run_polling()
