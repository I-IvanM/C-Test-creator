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

################## ПЕРЕМЕННЫЕ ##################

BOT_TOKEN = "8710418561:AAE-XdSqTOq6dXVSig8noY3EvfQBMvaYQ5A"
OPENAI_API_KEY = "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"

ADMIN_ID = 876824576 # Сюда идёт поддержка, этот пользователь может выдавать VIP
ADMIN_PASSWORD = "Skat" # Пароль там, где он нужен
SUBSCRIPTION_PRICE = 100 # Цена подписки

# Переменные состояний
MODE_CREATE = "create"
MODE_GENERATE = "generate"
MODE_SUPPORT = "support"

STATE_QUESTION_1 = "question_1"
STATE_QUESTION_2 = "question_2"
STATE_QUESTION_3 = "question_3"
STATE_COMPLETED = "completed"

###################### КЛАВИАТУРЫ #####################

# Основная
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("текст в C-Test"), KeyboardButton("Генерировать")],
        [KeyboardButton("Справка"), KeyboardButton("Подписка")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Вопрос про язык
def get_language_keyboard():
    keyboard = [
        [KeyboardButton("Английский"), KeyboardButton("Немецкий")],
        [KeyboardButton("Вернуться в главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# A1 A2 B1 B2 C1 C2
def get_A1C2_keyboard():
    keyboard = [
        [KeyboardButton("A1"), KeyboardButton("B1"), KeyboardButton("C1")],
        [KeyboardButton("A2"), KeyboardButton("B2"), KeyboardButton("C2")],
        [KeyboardButton("Вернуться в главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Вернуться в главное меню
def get_menu_keyboard():
    keyboard = [[KeyboardButton("Вернуться в главное меню")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Смотреть ответы
def get_answer_keyboard():
    keyboard = [
        [KeyboardButton("Смотреть ответы")],
        [KeyboardButton("Вернуться в главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Управление подпиской
def get_subscription_keyboard():
    keyboard = [
        [KeyboardButton("О подписке ℹ")],
        [KeyboardButton("Моя подписка")],
        [KeyboardButton("Купить подписку")],
        [KeyboardButton("Вернуться в главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

################# ФУНКЦИИ #################

# превращение в c-test
def process_ctest(user_text: str) -> str:

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
        output = "В тексте должно быть несколько предложений, чтобы из него можно было составить C-Test."
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
            elif words[j] not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZабвгдежзийклмнопрстуфхцчшщъыьэюяАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ":
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
            elif words[j] not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZабвгдежзийклмнопрстуфхцчшщъыьэюяАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ":
                output = output[:-1]
                output += words[j] + " "
                count -= 1
            else:
                output += words[j] + " "

    return output

# Выделение ответов жирным
def process_marck_answers(generated_text: str):
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
        output = "There must be multiple sentence-ending punctuation marks (., ?, !) in the input text."
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
            elif words[j] not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZабвгдежзийклмнопрстуфхцчшщъыьэюяАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ":
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
            elif words[j] not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZабвгдежзийклмнопрстуфхцчшщъыьэюяАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ":
                output = output[:-1]
                output += words[j] + " "
                count -= 1
            else:
                output += words[j] + " "
    return output

# Запрос к Chat GPT по API
client = AsyncOpenAI(api_key=OPENAI_API_KEY)
async def generate_text(language: str, level: str, wishes: str) -> str:
    prompt = (f"Сгенерируй короткий текст на {language} языке длинной 5 предложений. "
              f"Уровень языка {level}. "
              f"Пожелания к тексту: {wishes}."
              f"НЕ ДОБАВЛЯЙ НИКАКИХ КОММЕНТАРИЕВ! ТОЛЬКО САМ ТЕКСТ! Игнорируй противоречащие условиям и непонятные пожелания.")
    
    response = await client.responses.create(
        model="gpt-5-nano",
        input=prompt
    )
    return response.output_text

# БАЗА ДАННЫХ, илиниализация
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        registered TEXT,
        last_free_refresh TEXT,
        subscription_expires_at TEXT,
        creations_left INTEGER DEFAULT 3,
        generations_left INTEGER DEFAULT 2,
        is_VIP INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()

# БАЗА ДАННЫ, регистрация пользователя
def register_user(user_id: int, username: str, first_name: str):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users (
            user_id,
            username,
            first_name,
            registered,
            last_free_refresh,
            subscription_expires_at,
            creations_left,
            generations_left,
            is_VIP
        )
        VALUES (?, ?, ?, ?, ?, NULL, 3, 3, 0)
    """, (
        user_id,
        username,
        first_name,
        datetime.now().isoformat(timespec="seconds"),
        datetime.now().isoformat(timespec="seconds")
    ))

    conn.commit()
    conn.close()

# БАЗА ДАННЫХ, вызов данных пользователя
def get_user(user_id: int):
    conn = sqlite3.connect("users.db")
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
        "registered": row[3],
        "last_free_refresh": row [4],
        "subscription_expires_at": row[5],
        "creations_left": row[6],
        "generations_left": row[7],
        "is_VIP": bool(row[8]),
    }

# БАЗА ДАННЫХ, напечатать пользователя
def print_user(user_id: int) -> str:
    user = get_user(user_id)

    if user is None:
        return "Пользователь не найден"

    return (
        f"ID: {user['user_id']}\n"
        f"Username: @{user['username']}\n"
        f"Имя: {user['first_name']}\n"
        f"Дата регистрации: {user['registered']}\n"
        f"Последнее обновление бесплатной {user['last_free_refresh']}\n"
        f"Подписка до: {user['subscription_expires_at']}\n"
        f"Преобразований осталось: {user['creations_left']}\n"
        f"Генераций осталось: {user['generations_left']}\n"
        f"VIP: {user['is_VIP']}"
    )

# БАЗА ДАННЫХ, Уменьшить кол-во оставшихся генераций
def decrease_generation(user_id: int):
    conn = sqlite3.connect("users.db")
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
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET creations_left = creations_left - 1
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

# БАЗА ДАННЫХ, довавление генераций
def add_generations(user_id: int, amount: int):
    conn = sqlite3.connect("users.db")
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
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET creations_left = creations_left + ?
        WHERE user_id = ?
    """, (amount, user_id))

    conn.commit()
    conn.close()

# БАЗА ДАННЫХ, установка значения генераций
def set_generations(user_id: int, amount: int):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET generations_left = ?
        WHERE user_id = ?
    """, (amount, user_id))

    conn.commit()
    conn.close()

# БАЗА ДАННЫХ, установка значений конвертаций
def set_creations(user_id: int, amount: int):
    conn = sqlite3.connect("users.db")
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


        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users
            SET subscription_expires_at = NULL
            WHERE user_id = ?
        """, (user_id,))

        conn.commit()
        conn.close()

# БАЗА ДАННЫХ, проверка бесплатной подписки (мб надо пополнить месячную норму)
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

        conn = sqlite3.connect("users.db")
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
    if get_user(user_id)["is_VIP"] == True:
        set_creations(user_id, 57)
        set_generations(user_id, 57)
    creations = get_user(user_id)['creations_left']
    generations = get_user(user_id)['generations_left']

    return{'creations': creations, 'generations': generations}

# БАЗА ДАННЫХ, выдача подписки
def give_subscription(user_id: int):

    conn = sqlite3.connect("users.db")
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
            new_expire = current_expire + timedelta(days=30)
        else:
            new_expire = now + timedelta(days=30)
    else:
        new_expire = now + timedelta(days=30)

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

    conn = sqlite3.connect("users.db")
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
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET is_VIP = ?
        WHERE user_id = ?
    """, (1 if value else 0, user_id))

    conn.commit()
    conn.close()

# ПОДПИСКА, создание строки метки платежа
def build_payload(user_id: int, purpose: str) -> str:
    return f"{purpose}:{user_id}"


######################### РАБОТА БОТА ######################### (обработчики входящих)

# START
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = ("C-Tester \n"
                    "Этот бот может превратить Ваш текст в C-Test или сгенерировать новый С-Test специально для Вас! \n"
                    "Если у Вас есть вопросы, нажмите кнопку \"справка\" или введите команду /help.")
    context.user_data['mode'] = MODE_CREATE
    context.user_data['quiz_state'] = None
    context.user_data.setdefault("messages", [])

    reply_markup=get_main_keyboard()

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
    text = (
        "Бот может работать в двух режимах:\n"
        "1️⃣ «текст в C-Test» — Вы можете отправить любой текст, в котором есть несколько предложений и бот преобразует его в C-Test!\n"
        "2️⃣ «Генерировать» — бот задаст Вам несколько вопросов и создаст новый C-Test специально для вас!\n\n"

        "Используйте кнопки внизу экрана для переключения режимов.\n\n"

        "📝 В режиме генерации бот задаёт несколько вопросов. Вы можете отвечать заготовленными кнопками или писать свои ответы.\n\n"

        "🫡 Полный список команд бота:\n"
        "/start – запускает бот заного\n"
        "/help – вызывает это сообщение\n"
        "/subscription – получиль информацию об условиях подписки\n"
        "/my_info – получить информацию о состоянии моей подписки\n"
        "/support – позволяет отправить запрос в тех. поддержку бота\n"
    )
    await update.message.reply_text(text)

# Комнада /support
async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = MODE_SUPPORT
    await update.message.reply_text(
            "🔧 Опишите Вашу проблему.\n"
            "Вы также может отправить фото возникшей проблемы, если считаете нужным. Все нетектовые сообщения автоматически перенаправляются в поддержку.",
            reply_markup=get_menu_keyboard()
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

    if date != None:
        date = f"{date[:4]}.{date[5:7]}.{date[8:10]} {date[11:16]}"
        status = f"активна до {date}"
    else:
        status = "не активна"

    text = (
        f"Подписка {status}\n\n"
        f"Осталось преобразований: {user['creations_left']}\n"
        f"Осталось генераций: {user['generations_left']}\n\n"
    )

    if user['is_VIP'] == 1:
        text = (f"🎩 Вы VIP пользователь, Вам доступны неограниченные возможности преобразования и генерации с-тестов!\n\n{text}")

    msg = await update.message.reply_text(text, reply_markup=get_subscription_keyboard())
    context.user_data["messages"].append(msg.message_id)

# ПОДПИСКА, рассказ о ней /subscription
async def subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "Подписка включает:\n\n"
        "• 100 преобразований текста в C-Test\n"
        "• 100 генераций новых C-Test\n\n"
        "Cрок действия 30 дней.\n"
        "Подписка не продляется автоматически.\n"
        "По истечении 30 дней все неизрасходыванные генерации и преобразования сгорают.\n"
        "Оплата производится при помощи Telegram Stars:\n"
        "1 месяц подписки стоит 100 звёзд ≈ 2-3 €."
    )

    msg = await update.message.reply_text(text)
    context.user_data["messages"].append(msg.message_id)

# ПОДПИСКА, выдать /give_sub
async def give_sub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    give_subscription(update.effective_user.id)
    user = get_user(update.effective_user.id)
    date = user["subscription_expires_at"]
    if date != None:
        date = f"{date[:4]}.{date[5:7]}.{date[8:10]} {date[11:16]}"


    await update.message.reply_text(
        "🎉🎉🎉 Поздравляем! 🎉🎉🎉\n"
        "Вы оформили подписку на C-Test creator бота!\n"
        "📚 Мы желаем Вам хорошей подготовки и простых заданий на экзамене!\n\n"
        f"Подписка активна до {date}"
    )

# ПОДПИСКА, обнулить /reset_sub
async def reset_sub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    reset_subscription(update.effective_user.id)

    msg = await update.message.reply_text(
        "Подписка сброшена."
    )
    context.user_data["messages"].append(msg.message_id)
    context.user_data["messages"].append(update.message.message_id)

# ПОДПИСКА, выдать / забрать VIP
async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    args = context.args

    if len(args) != 3:
        await update.message.reply_text(
            "Отправьте команду в формте:\n/VIP пароль user_id True|False"
        )
        return

    password = args[0]

    if password != ADMIN_PASSWORD:
        await update.message.reply_text("Неверный пароль")
        return
    
    if update.effective_user.id != ADMIN_ID:
        msg = await update.message.reply_text("Вы не администратор.")
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
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    payload = build_payload(user_id, "donate")

    title = "Оплата подписки"
    description = f"Подписка на C-Test crator: {amount} ⭐ || 1 месяц, 100 преобразований, 100 генераций"
    prices = [LabeledPrice(label="Донат", amount=amount)]

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
async def donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args

    if not args or not args[0].isdigit():
        await update.message.reply_text("Введите команду в формате: /donate <количество звёзд>")
        return

    amount = int(args[0])

    if amount < 1:
        await update.message.reply_text("Количество звёзд должно быть не меньше 1.")
        return

    await pay(update, context, amount)

# ПОДПИСКА, выставление счёта
async def buy_sub_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await pay(update, context, SUBSCRIPTION_PRICE)

# Подтверждение готовности (наличия)
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    await query.answer(ok=True)

# Подтверждение оплаты
async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payment = update.message.successful_payment
    amount = payment.total_amount

    await update.message.reply_text(
        f"Спасибо, платёж {amount} ⭐ получен!\n"
        "Если что-то пошло не так, вы можете обратить в поддержку с помощью команды /support"
    )

    give_subscription(update.effective_user.id)


########################## ОБРАБОТКА ВХОДЯЩИХ ТЕКСТОВЫХ СООБЩЕНИЙ #########################
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.setdefault("messages", [])
    user_text = update.message.text
    quiz_state = context.user_data.get('quiz_state')
    mode = context.user_data.get('mode', MODE_CREATE)

    register_user(
        update.effective_user.id,
        update.effective_user.username or "–",
        update.effective_user.first_name or "–"
    )
    limits = refresh_user(update.effective_user.id)

    # Кнопка переключения в режим "текст в C-Test"
    if user_text == "текст в C-Test":
        context.user_data["messages"].append(update.message.message_id)
        context.user_data['mode'] = MODE_CREATE
        context.user_data['quiz_state'] = None
        msg = await update.message.reply_text(
            "✅ Переключено в режим \"текст в C-Test\".\n"
            "Отправьте ваш текст — бот превратит его в C-Test!",
            reply_markup=get_main_keyboard()
        )
        context.user_data["messages"].append(msg.message_id)

    # Кнопка переключения в режим генерации
    elif user_text == "Генерировать":
        if limits["generations"] <= 0:
                msg = await update.message.reply_text(
                "Лимит генераций исчерпан, купите подписку!"
                )
                context.user_data["messages"].append(msg.message_id)
                return
        
        context.user_data['mode'] = MODE_GENERATE
        context.user_data['quiz_state'] = STATE_QUESTION_1
        context.user_data['answers'] = {}
        context.user_data["messages"].append(update.message.message_id)

        msg = await update.message.reply_text(
            "🐙 Переключено в режим Генерации.\n\n"
            "На каком языке нужен текст?\n" 
            "Выберите из предложенных или введите с клавиатуры.",
            reply_markup=get_language_keyboard()
        )
        context.user_data["messages"].append(msg.message_id)

    # Кнопка вернуться в главное меню
    elif user_text == "Вернуться в главное меню":
        context.user_data["messages"].append(update.message.message_id)
        context.user_data['mode'] = MODE_CREATE
        context.user_data['quiz_state'] = None
        
        # Удаление сообщений из списка
        await delete_listed_messages(
            context.user_data["messages"],
            update.effective_chat.id,
            context
        )
        context.user_data["messages"] = []

        msg = await update.message.reply_text(
            "Вы вернулись в главное меню\n",
            reply_markup=get_main_keyboard()
        )
        context.user_data["messages"].append(msg.message_id)

    # Кнопка помощь
    elif user_text == "Справка":
        context.user_data["messages"].append(update.message.message_id)
        await help_command(update, context)

    # Кнопка смотреть ответы
    elif user_text == "Смотреть ответы":
        context.user_data["messages"].append(update.message.message_id)
        if "original_text" not in context.user_data:
            return
        text = context.user_data["original_text"]
        text = process_marck_answers(text)
        await update.message.reply_text(
        text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML")

    elif user_text == "Подписка" or user_text == "Моя подписка":
        context.user_data["messages"].append(update.message.message_id)
        await my_info_command(update, context)

    elif user_text == "Купить подписку":
        context.user_data["messages"].append(update.message.message_id)
        await buy_sub_command(update, context)

    elif user_text == "О подписке ℹ":
        context.user_data["messages"].append(update.message.message_id)
        await subscription_command (update, context)

    # Обработка свободного текста
    else:
        # В режиме "текст в C-Test" — обрабатываем текст
        if mode == MODE_CREATE:
            if limits["creations"] <= 0:
                msg = await update.message.reply_text(
                    "Лимит преобразований исчерпан, купите подписку!"
                )
                context.user_data["messages"].append(msg.message_id)
                return
            
            try:
                output = process_ctest(user_text)
                decrease_creation(update.effective_user.id)
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
                text = "Какого уровня должен быть C-Test (A1, A2, B1, B2, C1)?"
                context.user_data["quiz_state"] = STATE_QUESTION_2
                msg = await update.message.reply_text(
                    text,
                    reply_markup=get_A1C2_keyboard())
                context.user_data["messages"].append(msg.message_id)

            elif quiz_state == STATE_QUESTION_2:
                answers['level'] = user_text
                text = "Есть ли у Вас пожелания к тексту?"
                context.user_data["quiz_state"] = STATE_QUESTION_3
                msg = await update.message.reply_text(
                    text,
                    reply_markup=get_menu_keyboard())
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
                    f"Отлично, генерируется!\n"
                    f"{answers['language']}\n"
                    f"{answers['level']}\n"
                    f"{answers['wishes']}"
                )
                msg = await update.message.reply_text(
                    text,
                    reply_markup=get_answer_keyboard())
                context.user_data["messages"].append(update.message.message_id)
                # Печатает...
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id,
                    action=ChatAction.TYPING
                )
                # Генерация текста
                text = await (generate_text(answers['language'], answers['level'], answers['wishes']))
                decrease_generation(update.effective_user.id)
                context.user_data["original_text"] = text
                text = process_ctest(text)
                await update.message.reply_text(
                    text,
                    reply_markup=get_answer_keyboard())
                
            elif quiz_state == STATE_COMPLETED:
                context.user_data["mode"] = MODE_CREATE
                context.user_data["quiz_state"] = None

            else:
                text = (
                    f"Ошибка, обратитесь в поддержку!\n\n"
                    f"/support"
                    f"{context.user_data['mode']}\n"
                    f"{context.user_data['quiz_state']}"
                    f"{await user_comand()}"
                )
                await update.message.reply_text(
                text,
                reply_markup=get_menu_keyboard())

        elif mode == MODE_SUPPORT:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"🔧 Обращение в поддержку\n\n"
                    f"User ID: {update.effective_user.id}\n"
                    f"Username: @{update.effective_user.username or "no username"}\n"
                    f"Имя: {update.effective_user.first_name}\n\n"
                    f"{user_text}"
                )
            )
            msg = await update.message.reply_text(
                "Сообщение отправлено в поддержку."
            )
            context.user_data["messages"].append(msg.message_id)



########################### ОБРАБОТКА НЕ-ТЕКСТОВЫХ СООБЩЕНИЙ #########################
async def handle_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

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
        "Ваше сообщение было переслано в поддержку."
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
        CommandHandler("give_sub", give_sub_command)
    )

    app.add_handler(
        CommandHandler("reset_sub", reset_sub_command)
    )

    app.add_handler(
        CommandHandler("VIP", vip_command)
    )

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    app.add_handler(
        CommandHandler("subscription", subscription_command)
    )

    app.add_handler(
        CommandHandler("donate", donate_command)
    )

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
