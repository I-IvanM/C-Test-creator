#################### IMPORT #################

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    LabeledPrice
)
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
    PreCheckoutQueryHandler
)
from telegram.constants import ChatAction
import re
from openai import AsyncOpenAI
import sqlite3
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv()  # подтягиваем переменные из файла .env

#Подтягиваем переводы
from locales.ru import TEXT as RU
from locales.fa import TEXT as FA
from locales.en import TEXT as EN
from locales.de import TEXT as DE
translations = {"ru": RU, "fa": FA, "en": EN, "de": DE}

################## ПЕРЕМЕННЫЕ ##################

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DATABASE_PATH = os.getenv("DATABASE_PATH", "users.db")

ADMIN_ID = 876824576 # Сюда идёт поддержка, этот пользователь может выдавать VIP
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") # Пароль там, где он нужен
SUBSCRIPTION_PRICE = 900 # Цена подписки

# Переменные состояний
MODE_CREATE = "create"
MODE_GENERATE = "generate"
MODE_SUPPORT = "support"
MODE_SETTINGS = "settings"

STATE_QUESTION_1 = "question_1"
STATE_QUESTION_2 = "question_2"
STATE_QUESTION_3 = "question_3"
STATE_COMPLETED = "completed"

###################### КЛАВИАТУРЫ #####################

# Основная
def get_main_keyboard(language):
    keyboard = [
        [KeyboardButton(t(language, "text to c-test")), KeyboardButton(t(language, "generate"))],
        [KeyboardButton(t(language, "help")), KeyboardButton(t(language, "Subscription")), KeyboardButton("🌐")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Вопрос про язык
def get_language_keyboard(language):
    keyboard = [
        [KeyboardButton("🏴󠁧󠁢󠁥󠁮󠁧󠁿 Englisch"), KeyboardButton("🇩🇪 Deutsch")],
        [KeyboardButton(t(language, "Return to the main menu"))]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# A1 A2 B1 B2 C1 C2
def get_A1C2_keyboard(language):
    keyboard = [
        [KeyboardButton("A1"), KeyboardButton("B1"), KeyboardButton("C1")],
        [KeyboardButton("A2"), KeyboardButton("B2"), KeyboardButton("C2")],
        [KeyboardButton(t(language, "Return to the main menu"))]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Нет пожеланий
def get_no_wishes_keyboard(language):
    keyboard = [
        [KeyboardButton(t(language, "No wishes"))],
        [KeyboardButton(t(language, "Return to the main menu"))]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Вернуться в главное меню
def get_menu_keyboard(language):
    keyboard = [[KeyboardButton(t(language, "Return to the main menu"))]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Смотреть ответы
def get_answer_keyboard(language):
    keyboard = [
        [KeyboardButton(t(language, "View answers"))],
        [KeyboardButton(t(language, "Return to the main menu"))]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Управление подпиской
def get_subscription_keyboard(language):
    keyboard = [
        [KeyboardButton(t(language, "About subscription"))],
        [KeyboardButton(t(language, "My Subscription"))],
        [KeyboardButton(t(language, "Buy a subscription"))],
        [KeyboardButton(t(language, "Return to the main menu"))]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Смена языков
def get_my_language_keyboard(language):
    keyboard = [
        [KeyboardButton("English"), KeyboardButton("Deutsch")],
        [KeyboardButton("Русский"), KeyboardButton("فارسی")],
        [KeyboardButton(t(language, "Return to the main menu"))]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

################# ФУНКЦИИ #################

#Подстановка перевода
def t(language, key, **kwargs):
    if language not in translations:
        language = "en"
    return translations[language][key].format(**kwargs)

# превращение в c-test
def process_ctest(user_text: str, language) -> str:

    output = ""
    words = None

    p1 = user_text.find(".")
    p2= user_text.find("?")
    p3 = user_text.find("!")
    p4 = user_text.find(";")
    p5 = user_text.find(":")
    # p6 = user_text.find(",") # Запятая не считается
    p7 = user_text.find("\n")

    positions = [p for p in (p1, p2, p3, p4, p5, p7) if p != -1]

    if positions:
       pos = min(positions)
       output = user_text[:pos + 1] + " "
       words = user_text[pos + 1:].lstrip()
    else:
        # ERROR: No sentence-ending punctuation found
        output = t(language, "The text must contain several sentences ...")
        return output

    words = re.findall(r"\w+|[^\w\s]", words)

    count = 0
    for j in range(len(words)):
        count += 1
        if count % 2 == 0:
            num = len(words[j])
            if num >1 and not words[j].isdigit():
                output += words[j][:num//2] + "___  "
            # Проверка на символ, который не буква
            elif not words[j].isalpha():
                output = output[:-1]
                output += words[j] + " "
                count -= 1
            else:
                output += words[j] + " "
                count -= 1

        else:
            if len(words[j]) > 1:
                output += words[j] + " "
            # Проверка на символ, который не буква
            elif not words[j].isalpha():
                output = output[:-1]
                output += words[j] + " "
                count -= 1
            else:
                output += words[j] + " "

    return output

# Выделение ответов жирным
def process_mark_answers(generated_text: str, language):
    output = ""
    words = None

    p1 = generated_text.find(".")
    p2= generated_text.find("?")
    p3 = generated_text.find("!")
    p4 = generated_text.find(";")
    p5 = generated_text.find(":")
    # p6 = generated_text.find(",") # Запятая не считается
    p7 = generated_text.find("\n")

    positions = [p for p in (p1, p2, p3, p4, p5, p7) if p != -1]

    if positions:
       pos = min(positions)
       output = generated_text[:pos + 1] + " "
       words = generated_text[pos + 1:].lstrip()
    else:
        # ERROR: No sentence-ending punctuation found
        output = t(language, "The text must contain several sentences ...")
        return output

    words = re.findall(r"\w+|[^\w\s]", words)

    count = 0
    for j in range(len(words)):
        count += 1
        if count % 2 == 0:
            num = len(words[j])
            if num >1 and not words[j].isdigit():
                output += words[j][:num//2] + "<b>" + words[j][num//2:] + "</b> "
            # Проверка на символ, который не буква
            elif not words[j].isalpha():
                output = output[:-1]
                output += words[j] + " "
                count -= 1
            else:
                output += words[j] + " "
                count -= 1

        else:
            if len(words[j]) > 1:
                output += words[j] + " "
            # Проверка на символ, который не буква
            elif not words[j].isalpha():
                output = output[:-1]
                output += words[j] + " "
                count -= 1
            else:
                output += words[j] + " "
    return output

# Запрос к Chat GPT по API
client = AsyncOpenAI(api_key=OPENAI_API_KEY)
async def generate_text(language: str, level: str, wishes: str) -> str:
    prompt = (f"Generate a short text in {language} that is 5 sentences long. "
              f"Language level: {level}."
              f"Preferences for the text: {wishes}."
              f"DO NOT ADD ANY COMMENTS! ONLY THE TEXT ITSELF! Ignore any preferences that contradict the conditions or are unclear.")
    
    try:
        response = await client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )
    except Exception:
        return None
    return response.output_text

# БАЗА ДАННЫХ, инициализация
def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        language TEXT DEFAULT 'ru',
        registered TEXT,
        last_free_refresh TEXT,
        subscription_expires_at TEXT,
        creations_left INTEGER DEFAULT 3,
        generations_left INTEGER DEFAULT 3,
        is_VIP INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()

# БАЗА ДАННЫ, регистрация пользователя
def register_user(user_id: int, username: str, first_name: str, language: str):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users (
            user_id,
            username,
            first_name,
            language,
            registered,
            last_free_refresh,
            subscription_expires_at,
            creations_left,
            generations_left,
            is_VIP
        )
        VALUES (?, ?, ?, ?, ?, ?, NULL, 3, 3, 0)
    """, (
        user_id,
        username,
        first_name,
        language,
        datetime.now().isoformat(timespec="seconds"),
        datetime.now().isoformat(timespec="seconds")
    ))

    conn.commit()
    conn.close()

# БАЗА ДАННЫХ, вызов данных пользователя
def get_user(user_id: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    row = cursor.fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "user_id": row[0],
        "username": row[1],
        "first_name": row[2],
        "language": row[3],
        "registered": row[4],
        "last_free_refresh": row[5],
        "subscription_expires_at": row[6],
        "creations_left": row[7],
        "generations_left": row[8],
        "is_VIP": bool(row[9]),
    }

# БАЗА ДАННЫХ, напечатать пользователя
def print_user(user_id: int) -> str:
    user = get_user(user_id)

    if user is None:
        return "User not found"

    return (
        f"ID: {user['user_id']}\n"
        f"Username: @{user['username']}\n"
        f"Имя: {user['first_name']}\n"
        f"Язык: {user['language']}\n"
        f"Дата регистрации: {user['registered']}\n"
        f"Последнее обновление бесплатной {user['last_free_refresh']}\n"
        f"Подписка до: {user['subscription_expires_at']}\n"
        f"Преобразований осталось: {user['creations_left']}\n"
        f"Генераций осталось: {user['generations_left']}\n"
        f"VIP: {user['is_VIP']}"
    )

# БАЗА ДАННЫХ, Уменьшить кол-во оставшихся генераций
def decrease_generation(user_id: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET generations_left = generations_left - 1
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

# БАЗА ДАННЫХ, уменьшить количество оставшихся конвертаций
def decrease_creation(user_id: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET creations_left = creations_left - 1
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

# БАЗА ДАННЫХ, добавление генераций
def add_generations(user_id: int, amount: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET generations_left = generations_left + ?
        WHERE user_id = ?
    """, (amount, user_id))

    conn.commit()
    conn.close()

# БАЗА ДАННЫХ, добавление конвертаций
def add_creations(user_id: int, amount: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET creations_left = creations_left + ?
        WHERE user_id = ?
    """, (amount, user_id))

    conn.commit()
    conn.close()

# БАЗА ДАННЫХ, установка значения оставшихся генераций
def set_generations(user_id: int, amount: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET generations_left = ?
        WHERE user_id = ?
    """, (amount, user_id))

    conn.commit()
    conn.close()

# БАЗА ДАННЫХ, установка значений оставшихся конвертаций
def set_creations(user_id: int, amount: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET creations_left = ?
        WHERE user_id = ?
    """, (amount, user_id))

    conn.commit()
    conn.close()

# БАЗА ДАННЫХ, проверка, не истекла ли подписка
def check_subscription_expired(user_id: int):
    user = get_user(user_id)

    if not user['subscription_expires_at']:
        return

    expires = datetime.fromisoformat(user['subscription_expires_at'])
    creations = user['creations_left']
    generations = user['generations_left']

    if datetime.now() >= expires:
        if creations > 3:
            set_creations(user_id, 3)
        if generations > 3:
            set_generations(user_id, 3)


        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users
            SET subscription_expires_at = NULL
            WHERE user_id = ?
        """, (user_id,))

        conn.commit()
        conn.close()

# БАЗА ДАННЫХ, проверка бесплатной подписки
def check_free_month(user_id: int):
    user = get_user(user_id)

    last_refresh = user["last_free_refresh"]

    if not last_refresh:
        return

    last_refresh = datetime.fromisoformat(last_refresh)

    if datetime.now() >= last_refresh + timedelta(days=30):

        if user["generations_left"] < 3:
            set_generations(user_id, 3)

        if user["creations_left"] < 3:
            set_creations(user_id, 3)

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users
            SET last_free_refresh = ?
            WHERE user_id = ?
        """, (
            datetime.now().isoformat(timespec="seconds"),
            user_id
        ))

        conn.commit()
        conn.close()

# БАЗА ДАННЫХ, все проверки сразу + кол-во преобразований и генераций + 
def refresh_user(user_id: int):
    check_subscription_expired(user_id)
    check_free_month(user_id)
    user = get_user(user_id)

    if user["is_VIP"]:
        set_creations(user_id, 57)
        set_generations(user_id, 57)
        user = get_user(user_id)

    return {
        "creations": user["creations_left"],
        "generations": user["generations_left"]
    }

# БАЗА ДАННЫХ, выдача подписки
def give_subscription(user_id: int, days):

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT subscription_expires_at
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    row = cursor.fetchone()

    now = datetime.now()

    if row and row[0]:
        current_expire = datetime.fromisoformat(row[0])

        if current_expire > now:
            new_expire = current_expire + timedelta(days=days)
        else:
            new_expire = now + timedelta(days=days)
    else:
        new_expire = now + timedelta(days=days)

    cursor.execute("""
        UPDATE users
        SET subscription_expires_at = ?
        WHERE user_id = ?
    """, (
        new_expire.isoformat(timespec="seconds"),
        user_id
    ))

    conn.commit()
    conn.close()

    add_creations(user_id, 100)
    add_generations(user_id, 100)

# БАЗА ДАННЫХ, обнулить подписку
def reset_subscription(user_id: int):

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET
            subscription_expires_at = NULL,
            creations_left = 0,
            generations_left = 0
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

# БАЗА ДАННЫХ, выдать VIP
def set_vip(user_id: int, value: bool):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET is_VIP = ?
        WHERE user_id = ?
    """, (1 if value else 0, user_id))

    conn.commit()
    conn.close()

# БАЗА ДАННЫХ, сменить язык
def set_language(user_id: int, language: str):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET language = ?
        WHERE user_id = ?
    """, (language, user_id))

    conn.commit()
    conn.close()

# ПОДПИСКА, создание строки метки платежа
def build_payload(user_id: int, purpose: str) -> str:
    return f"{purpose}:{user_id}"


######################### РАБОТА БОТА ######################### (обработчики входящих)

# START
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = (update.effective_user.language_code or "en")[:2]
    if language not in translations:
        language = "en"

    register_user(
    update.effective_user.id,
    update.effective_user.username,
    update.effective_user.first_name,
    language
)

    welcome_text = (t(language, "starting text"))
    context.user_data['mode'] = MODE_CREATE
    context.user_data['quiz_state'] = None
    context.user_data.setdefault("messages", [])

    reply_markup=get_main_keyboard(language)

    msg = await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    context.user_data["messages"].append(msg.message_id)
    context.user_data["messages"].append(update.message.message_id)

# Удаление сообщений из списка context.user_data["messages"]
async def delete_listed_messages(list, chat_id, context: ContextTypes.DEFAULT_TYPE):
                for i in list:
                    try:
                        await context.bot.delete_message(chat_id, message_id=i)
                    except Exception:
                        pass

# КОМАНДА /help 
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if user is None:
        language = (update.effective_user.language_code or "en")[:2]
        if language not in translations:
            language = "en"
    else:
        language = user["language"] or "en"
    text = (t(language, "The bot can operate in two modes: ..."))
    await update.message.reply_text(text)

# Команда /support
async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE,):
    context.user_data["mode"] = MODE_SUPPORT
    user = get_user(update.effective_user.id)
    language = user["language"] or "en"
    await update.message.reply_text(
            t(language,"Describe your problem."),
            reply_markup=get_menu_keyboard(language)
        )
    
# Команда /my_language
async def my_language_command(update: Update, context: ContextTypes.DEFAULT_TYPE,):
    context.user_data["mode"] = MODE_SETTINGS
    user = get_user(update.effective_user.id)
    language = user["language"] or 'en'
    await update.message.reply_text(
            t(language,"Select your language."),
            reply_markup=get_my_language_keyboard(language)
        )

# БАЗА ДАННЫХ, выдать всю информацию о пользователе /user
async def user_comand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = print_user(update.effective_user.id)
    msg = await update.message.reply_text(text)
    context.user_data["messages"].append(msg.message_id)

# ПОДПИСКА, выдача информации /my_info
async def my_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    date = user["subscription_expires_at"]
    language = user["language"] or 'ru'

    if date != None:
        date = f"{date[:4]}.{date[5:7]}.{date[8:10]} {date[11:16]}"
        status = t(language, "active until", date=date)
    else:
        status = t(language, "inactive")

    creations_left = user['creations_left']
    generations_left = user['generations_left']

    text = (t(language, "Subscription, Conversions remaining, Generations remaining", status=status, creations_left=creations_left, generations_left=generations_left))

    if user['is_VIP']:
        text = t(language, "You are a VIP user", text=text)
    msg = await update.message.reply_text(text, reply_markup=get_subscription_keyboard(language))
    context.user_data["messages"].append(msg.message_id)

# ПОДПИСКА, рассказ о ней /subscription
async def subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    language = user["language"] or 'ru'

    text = (t(language, "The subscription includes:..."))

    msg = await update.message.reply_text(text)
    context.user_data["messages"].append(msg.message_id)

# ПОДПИСКА, выдать /give_sub
async def give_sub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    language = user["language"] or 'ru'

    give_subscription(update.effective_user.id, 30)
    user = get_user(update.effective_user.id)
    date = user["subscription_expires_at"]
    if date != None:
        date = f"{date[:4]}.{date[5:7]}.{date[8:10]} {date[11:16]}"

    await update.message.reply_text(t(language, "Congratulations!", date=date))

# ПОДПИСКА, обнулить /reset_sub
async def reset_sub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    language = user["language"] or 'ru'

    reset_subscription(update.effective_user.id)

    msg = await update.message.reply_text(
        t(language, "Subscription reset.")
    )
    context.user_data["messages"].append(msg.message_id)
    context.user_data["messages"].append(update.message.message_id)

# ПОДПИСКА, выдать / забрать VIP
async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    language = user["language"] or 'ru'

    args = context.args

    if len(args) != 3:
        await update.message.reply_text(
            "Отправьте команду в формате:\n/VIP пароль user_id True|False"
        )
        return

    password = args[0]

    if password != ADMIN_PASSWORD:
        await update.message.reply_text("Неверный пароль")
        return
    
    if update.effective_user.id != ADMIN_ID:
        msg = await update.message.reply_text(t(language, "You are not an administrator."))
        context.user_data["messages"].append(msg.message_id)
        context.user_data["messages"].append(update.message.message_id)
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await update.message.reply_text("Некорректный user_id")
        return

    vip_value = args[2].lower()

    if vip_value == "true":
        set_vip(user_id, True)
        await update.message.reply_text(
            f"VIP выдан пользователю {user_id}"
        )

    elif vip_value == "false":
        set_vip(user_id, False)
        await update.message.reply_text(
            f"VIP забран у пользователя {user_id}"
        )

    else:
        await update.message.reply_text(
            "Последний параметр должен быть True или False"
        )

# Оплата
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: int) -> None:
    user = get_user(update.effective_user.id)
    language = user["language"] or 'ru'

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    payload = build_payload(user_id, "subscription")

    title = t(language, "Subscription payment")
    description = t(language, "C-Test Creator subscription: 1 month, 100 conversions, 100 generations", amount=amount)
    prices = [LabeledPrice(label="Subscription payment", amount=amount)]

    await context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=prices,
    )

# Донат
'''
async def donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user(update.effective_user.id)
    language = user["language"] or 'ru'

    args = context.args

    if not args or not args[0].isdigit():
        await update.message.reply_text(t(language, "Enter the command in the format: /donate <number of stars>"))
        return

    amount = int(args[0])

    if amount < 1:
        await update.message.reply_text(t(language, "The number of stars must be at least 1."))
        return

    await pay(update, context, amount)
'''

# ПОДПИСКА, выставление счёта
async def buy_sub_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await pay(update, context, SUBSCRIPTION_PRICE)

# Подтверждение готовности (наличия)
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    await query.answer(ok=True)

# Подтверждение оплаты
async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user(update.effective_user.id)
    language = user["language"] or 'ru'
    
    payment = update.message.successful_payment
    amount = payment.total_amount

    give_subscription(update.effective_user.id, 30)
    await update.message.reply_text(t(language, "Thank you, payment received!", amount=amount))



########################## ОБРАБОТКА ВХОДЯЩИХ ТЕКСТОВЫХ СООБЩЕНИЙ #########################
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.setdefault("messages", [])
    user_text = update.message.text
    quiz_state = context.user_data.get('quiz_state')
    mode = context.user_data.get('mode', MODE_CREATE)
    user_id = update.effective_user.id

    language = (update.effective_user.language_code or "en")[:2]
    if language not in translations:
        language = "en"

    register_user(
        user_id,
        update.effective_user.username or "",
        update.effective_user.first_name or "",
        language
    )
    limits = refresh_user(user_id)

    user = get_user(user_id)
    language = user["language"] or "en"
    

    # Кнопка переключения в режим "текст в C-Test"
    if user_text == t(language, "text to c-test"):
        context.user_data["messages"].append(update.message.message_id)
        context.user_data['mode'] = MODE_CREATE
        context.user_data['quiz_state'] = None
        msg = await update.message.reply_text(
            t(language, "Switched to 'text to C-Test' mode."),
            reply_markup=get_main_keyboard(language)
        )
        context.user_data["messages"].append(msg.message_id)

    # Кнопка переключения в режим генерации
    elif user_text == t(language, "generate"):
        if limits["generations"] <= 0:
                msg = await update.message.reply_text(
                    t(language, "Generation limit reached, purchase a subscription!")
                    )
                context.user_data["messages"].append(msg.message_id)
                return
        
        context.user_data['mode'] = MODE_GENERATE
        context.user_data['quiz_state'] = STATE_QUESTION_1
        context.user_data['answers'] = {}
        context.user_data["messages"].append(update.message.message_id)

        msg = await update.message.reply_text(
            t(language, "Switched to Generation mode. In which language do you need the text?"),
            reply_markup=get_language_keyboard(language)
        )
        context.user_data["messages"].append(msg.message_id)

    # Кнопка вернуться в главное меню
    elif user_text == t(language, "Return to the main menu"):
        context.user_data["messages"].append(update.message.message_id)
        context.user_data['mode'] = MODE_CREATE
        context.user_data['quiz_state'] = None
        
        # Удаление сообщений из списка
        await delete_listed_messages(
            context.user_data["messages"],
            update.effective_chat.id,
            context
        )
        context.user_data["messages"].clear()

        msg = await update.message.reply_text(
            t(language, "You have returned to the main menu."),
            reply_markup=get_main_keyboard(language)
        )
        context.user_data["messages"].append(msg.message_id)

    # Кнопка помощь
    elif user_text == t(language, "help"):
        context.user_data["messages"].append(update.message.message_id)
        await help_command(update, context)

    # Кнопка смотреть ответы
    elif user_text == t(language, "View answers"):
        context.user_data["messages"].append(update.message.message_id)
        if "original_text" not in context.user_data:
            return
        text = context.user_data["original_text"]
        text = process_mark_answers(text, language)
        await update.message.reply_text(
        text,
        reply_markup=get_main_keyboard(language),
        parse_mode="HTML")

    elif user_text == t(language, "Subscription") or user_text == t(language, "My Subscription"):
        context.user_data["messages"].append(update.message.message_id)
        await my_info_command(update, context)

    elif user_text == t(language, "Buy a subscription"):
        context.user_data["messages"].append(update.message.message_id)
        await buy_sub_command(update, context)

    elif user_text == t(language, "About subscription"):
        context.user_data["messages"].append(update.message.message_id)
        await subscription_command (update, context)

    elif user_text == "🌐":
        context.user_data["messages"].append(update.message.message_id)
        await my_language_command (update, context)

    # Обработка свободного текста
    else:
        # В режиме "текст в C-Test" — обрабатываем текст
        if mode == MODE_CREATE:
            if limits["creations"] <= 0:
                msg = await update.message.reply_text(
                    t(language, "Creation limit reached, purchase a subscription!")
                )
                context.user_data["messages"].append(msg.message_id)
                return
            
            try:
                output = process_ctest(user_text, language)
                decrease_creation(user_id)
                await update.message.reply_text(output)

            except Exception as e:
                await update.message.reply_text(
                    f"Error processing message:\n{e}"
                )

        # В режиме генерации — обрабатываем ответы на вопросы
        elif mode == MODE_GENERATE and quiz_state:
            answers = context.user_data.get('answers', {})
            context.user_data["messages"].append(update.message.message_id)

            if quiz_state == STATE_QUESTION_1:
                answers['language'] = user_text
                text = t(language, "What level should the C-Test be")
                context.user_data["quiz_state"] = STATE_QUESTION_2
                msg = await update.message.reply_text(
                    text,
                    reply_markup=get_A1C2_keyboard(language))
                context.user_data["messages"].append(msg.message_id)

            elif quiz_state == STATE_QUESTION_2:
                answers['level'] = user_text
                text = t(language, "Do you have any wishes?")
                context.user_data["quiz_state"] = STATE_QUESTION_3
                msg = await update.message.reply_text(
                    text,
                    reply_markup=get_no_wishes_keyboard(language))
                context.user_data["messages"].append(msg.message_id)

            elif quiz_state == STATE_QUESTION_3:
                answers['wishes'] = user_text
                context.user_data["quiz_state"] = STATE_COMPLETED
                # Удаление сообщений из списка
                await delete_listed_messages(
                    context.user_data["messages"],
                    update.effective_chat.id,
                    context
                )
                context.user_data["messages"] = []
                # Отправка нового сообения    
                text = (
                    t(language, "Great, it's generating!",
                      lang=answers['language'],
                      level = answers['level'],
                      wishes = answers['wishes']
                    )
                )
                msg = await update.message.reply_text(
                    text,
                    reply_markup=get_answer_keyboard(language))
                context.user_data["messages"].append(update.message.message_id)
                # Печатает...
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id,
                    action=ChatAction.TYPING
                )
                # Генерация текста
                text = await (generate_text(answers['language'], answers['level'], answers['wishes']))
                if text is None:
                    await update.message.reply_text(
                        t(language, "Error, contact support!")
                    )
                    return
                decrease_generation(user_id)
                context.user_data["original_text"] = text
                text = process_ctest(text, language)
                await update.message.reply_text(
                    text,
                    reply_markup=get_answer_keyboard(language))
                
            elif quiz_state == STATE_COMPLETED:
                context.user_data["mode"] = MODE_CREATE
                context.user_data["quiz_state"] = None

            else:
                mode = context.user_data['mode']
                quiz_state = context.user_data['quiz_state']
                text = (
                    t(language, "Error, contact support!",
                      mode=mode, quiz_state=quiz_state)
                )
                await update.message.reply_text(
                text,
                reply_markup=get_menu_keyboard(language))

        elif mode == MODE_SUPPORT:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"🔧 Обращение в поддержку\n\n"
                    f"User ID: {user_id}\n"
                    f"Username: @{update.effective_user.username or "no username"}\n"
                    f"Имя: {update.effective_user.first_name}\n\n"
                    f"{user_text}"
                )
            )
            msg = await update.message.reply_text(
                t(language, "The message has been sent to support.")
            )
            context.user_data["messages"].append(msg.message_id)

        elif mode == MODE_SETTINGS:
            languages = {"en": "english", "de": "Deutsch", "ru": "Русский", "fa": "فارسی"}
            if user_text == "فارسی":
                set_language(user_id, "fa")
                user = get_user(user_id)
                language = user["language"]
                text = t(language, "The interface language has been changed to", ln = languages[language])
            elif user_text == "English":
                set_language(user_id, "en")
                user = get_user(user_id)
                language = user["language"]
                text = t(language, "The interface language has been changed to", ln = languages[language])
            elif user_text == "Deutsch":
                set_language(user_id, "de")
                user = get_user(user_id)
                language = user["language"]
                text = t(language, "The interface language has been changed to", ln = languages[language])
            elif user_text == "Русский":
                set_language(user_id, "ru")
                user = get_user(user_id)
                language = user["language"]
                text = t(language, "The interface language has been changed to", ln = languages[language])
            else:
                text = t(language, "Please select one of the offered languages.")

            context.user_data["mode"] = MODE_CREATE
            msg = await update.message.reply_text(
                text,
                reply_markup=get_main_keyboard(language)
            )
            context.user_data["messages"].append(msg.message_id)



########################### ОБРАБОТКА НЕ-ТЕКСТОВЫХ СООБЩЕНИЙ #########################
async def handle_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user(update.effective_user.id)
    language = user["language"] or 'en'

    context.user_data.setdefault("messages", [])

    # Пересылаем сообщение администратору
    await context.bot.forward_message(
        chat_id=ADMIN_ID,
        from_chat_id=update.effective_chat.id,
        message_id=update.message.message_id
    )

    # Дополнительная информация о пользователе
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"Нетекстовое сообщение\n\n"
            f"User ID: {update.effective_user.id}\n"
            f"Username: @{update.effective_user.username}\n"
            f"Имя: {update.effective_user.first_name}"
        )
    )

    msg = await update.message.reply_text(
        t(language, "Your message has been forwarded to support.")
    )

    context.user_data["messages"].append(msg.message_id)

################### MAIN #####################
def main() -> None:
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        CommandHandler("start", start_command)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    app.add_handler(
        CommandHandler("support", support_command)
    )

    app.add_handler(
        CommandHandler("user", user_comand)
    )

    app.add_handler(
    CommandHandler("my_info", my_info_command)
    )

    app.add_handler(
    CommandHandler("my_language", my_language_command)
    )

    '''
    app.add_handler(
        CommandHandler("give_sub", give_sub_command)
    )

    app.add_handler(
        CommandHandler("reset_sub", reset_sub_command)
    )
    '''

    app.add_handler(
        CommandHandler("VIP", vip_command)
    )

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    app.add_handler(
        CommandHandler("subscription", subscription_command)
    )

    '''
    app.add_handler(
        CommandHandler("donate", donate_command)
    )
    '''

    app.add_handler(
        PreCheckoutQueryHandler(precheckout_callback)
    )

    app.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
    )

    app.add_handler(
        MessageHandler(~filters.TEXT, handle_non_text)
    )

    print("The bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
