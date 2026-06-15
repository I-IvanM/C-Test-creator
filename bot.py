#################### IMPORT #################

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction
import re
from openai import AsyncOpenAI
import sqlite3
from datetime import datetime, timedelta

import os

################## ПЕРЕМЕННЫЕ ##################

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ID поддержки, куда перенаправлять запросы
admin = "@I_IvanM"

MODE_CREATE = "create"
MODE_GENERATE = "generate"
MODE_SUPPORT = "support"

STATE_QUESTION_1 = "question_1"
STATE_QUESTION_2 = "question_2"
STATE_QUESTION_3 = "question_3"
STATE_QUESTION_4 = "question_4"
STATE_COMPLETED = "completed"

###################### КЛАВИАТУРЫ #####################

# Основная
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("текст в C-Test"), KeyboardButton("Генерировать")],
        [KeyboardButton("Справка"), KeyboardButton("ℹ Подписка info")]
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
        [KeyboardButton("Моя подписка")],
        [KeyboardButton("Купить подписку")],
        [KeyboardButton("Вернуться в главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

################# ФУНКЦИИ #################

# превращение в c-test
def process_ctest(user_text: str) -> str:
    
    print(user_text)

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
        output = "There must be multiple sentence-ending punctuation marks (., ?, !) in the input text."
        return output

    words = re.findall(r"\w+|[^\w\s]", words)

    count = 0
    for j in range(len(words)):
        count += 1
        if count % 2 == 0:
            num = len(words[j])
            if num >1:
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
            if num >1:
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
        model="gpt-5-mini",
        input=prompt
    )
    return response.output_text

# Удаление сообщений из списка context.user_data["messages"]
async def delete_listed_messages(list, chat_id, context: ContextTypes.DEFAULT_TYPE):
                for i in list:
                    await context.bot.delete_message(
                        chat_id,
                        message_id=i
                    )

# БАЗА ДАННЫХ, илиниализация
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT
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
            first_Name,
            registered,
            last_free_refresh,
            subscription_expires_at,
            creations_left,
            generations_left,
            is_VIP
        )
        VALUES (?, ?, ?, ?, ?, NULL, 3, 2, 0)
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
    creations = user['crestions_left']
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
    creations = get_user(user_id)['creations_left']
    generations = get_user(user_id)['generations_left']
    if get_user(user_id)["is_VIP"] == True:
        set_creations(user_id, 57)
        set_generations(user_id, 57)

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
            new_expire = current_expire + timedelta(hours=1)
        else:
            new_expire = now + timedelta(hours=1)
    else:
        new_expire = now + timedelta(hours=1)

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

    add_creations(user_id, 2)
    add_generations(user_id, 2)

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
######################### РАБОТА БОТА ######################### (обработчики входящих)

# START
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = ("C-Tester \n"
                    "Этот бот может превратить Ваш текст в C-Test или сгенерировать новый С-Test специально для Вас! \n"
                    "Если у Вас есть вопросы, нажмите кнопку \"справка\" или введите команду /help.")
    context.user_data['mode'] = MODE_CREATE
    context.user_data['quiz_state'] = None
    context.user_data["messages"] = []

    reply_markup=get_main_keyboard()

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

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
        "/give_sub – Выдать себе подписку (пока на час, тестовая команда)\n"
        "/reset_sub – Сбрасывает лимиты в 0 (тестовая)"

        #"/clear – полностью очищает чат с ботом\n"
        #"/support – позволяет отправить запрос в тех. поддержку бота\n"
    )
    await update.message.reply_text(text)

# Команда /clear
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Функция ещё не готова")

    context.user_data.clear()
    await start_command(update, context)


# Комнада /support
async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = MODE_SUPPORT
    await update.message.reply_text(
            "Опишите Вашу проблему:"
            "Пока что прикладывать скриншоты нельзя",
            reply_markup=get_menu_keyboard()
        )
    print("Функция ещё не готова, отправить сообщение на ", admin)


# ПОДПИСКА, выдача информации /my_info
async def my_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)

    if user["subscription_expires_at"]:
        status = f"активна до {user['subscription_expires_at']}"
    else:
        status = "не активна"

    text = (
        f"Подписка {status}\n\n"
        f"Осталось преобразований: {user['creations_left']}\n"
        f"Осталось генераций: {user['generations_left']}\n\n"
    )

    if user['is_VIP'] == 1:
        text = (f"Вы VIP пользователь, Вам доступны неограниченные возможности преобразования и генерации с-тестов!\n {text}")

    await update.message.reply_text(text)

# ПОДПИСКА, рассказ о ней /subscription
async def subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "Подписка включает:\n\n"
        "• 100 преобразований текста в C-Test\n"
        "• 100 генераций новых C-Test\n"
        "• срок действия 30 дней\n\n"
        "По истечении 30 дней все оставшиеся генерации с преобразования сгорают.\n"
        "Оплата производится при помощи Telegram Stars:\n"
        "1 подписка: 100 звёзд ≈ 2-3 €"
    )

    await update.message.reply_text(text, reply_markup=get_subscription_keyboard())

# ПОДПИСКА, выдать /give_sub
async def give_sub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    give_subscription(update.effective_user.id)
    user = get_user(update.effective_user.id)

    await update.message.reply_text(
        "🎉🎉🎉 Поздравляем! 🎉🎉🎉\n"
        "Вы оформили подписку на C-Test creator бота!\n"
        "📚 Мы желаем Вам хорошей подготовки и простых заданий на экзамене!\n\n"
        f"Подписка активна до {user['subscription_expires_at']}"
    )

# ПОДПИСКА, обнулить /reset_sub
async def reset_sub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    reset_subscription(update.effective_user.id)

    await update.message.reply_text(
        "Подписка сброшена."
    )

########################## ОБРАБОТКА ВХОДЯЩИХ ТЕКСТОВЫХ СООБЩЕНИЙ #########################
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        context.user_data['mode'] = MODE_CREATE
        context.user_data['quiz_state'] = None
        await update.message.reply_text(
            "✅ Переключено в режим \"текст в C-Test\".\n"
            "Отправьте ваш текст — бот превратит его в C-Test!",
            reply_markup=get_main_keyboard()
        )

    # Кнопка переключения в режим генерации
    elif user_text == "Генерировать":
        context.user_data['mode'] = MODE_GENERATE
        context.user_data['quiz_state'] = STATE_QUESTION_1
        context.user_data['answers'] = {}
        context.user_data["messages"] = []

        msg = await update.message.reply_text(
            "🐙 Переключено в режим Генерации.\n\n"
            "На каком языке нужен текст?\n" 
            "Выберите из предложенных или введите с клавиатуры.",
            reply_markup=get_language_keyboard()
        )
        context.user_data["messages"].append(msg.message_id)

    # Кнопка отмены генерации
    elif user_text == "Вернуться в главное меню":
        context.user_data['mode'] = MODE_CREATE
        context.user_data['quiz_state'] = None
        await update.message.reply_text(
            "❌ Генерация отменена.\n"
            "Переключено в режим обработки вашего текста.",
            reply_markup=get_main_keyboard()
        )

    # Кнопка помощь
    elif user_text == "Справка":
        await help_command(update, context)

    # Кнопка смотреть ответы
    elif user_text == "Смотреть ответы":
        text = context.user_data["original_text"]
        text = process_marck_answers(text)
        await update.message.reply_text(
        text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML")

    elif user_text == "Моя подписка":
        await my_info_command(update, context)

    elif user_text == "Купить подписку":
        await give_sub_command(update, context)

    elif user_text == "ℹ Подписка info":
        await subscription_command (update, context)

    # Обработка свободного текста
    else:
        # В режиме "текст в C-Test" — обрабатываем текст
        if mode == MODE_CREATE:
            if limits["creations"] <= 0:
                await update.message.reply_text(
                    "Лимит преобразований исчерпан, купите подписку!"
                )
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
            if limits["generations"] <= 0:
                await update.message.reply_text(
                "Лимит генераций исчерпан, купите подписку!"
                )
                return
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
                # Отправка нового сообения
                text = (
                    f"Отлично, генерируется!\n"
                    f"{answers['language']}\n"
                    f"{answers['level']}\n"
                    f"{answers['wishes']}"
                )
                await update.message.reply_text(
                    text,
                    reply_markup=get_answer_keyboard())
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
                keyboard = get_main_keyboard()

            else:
                text = (
                    f"Ошибка, обратитесь в поддержку!\n\n"
                    f"{context.user_data['mode']}\n"
                    f"{context.user_data['quiz_state']}"
                )
                await update.message.reply_text(
                text,
                reply_markup=get_menu_keyboard())



########################### ОБРАБОТКА НЕ-ТЕКСТОВЫХ СООБЩЕНИЙ #########################
async def handle_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Error: Unsupported message type. Please send text messages only."
    )

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
        CommandHandler("clear", clear_command)
    )

    app.add_handler(
        CommandHandler("support", support_command)
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
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    app.add_handler(
    CommandHandler("subscription", subscription_command)
    )



    app.add_handler(
        MessageHandler(~filters.TEXT, handle_non_text)
    )

    print("The bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
