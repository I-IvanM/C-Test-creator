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
        [KeyboardButton("Справка")]
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

def get_answer_keyboard():
    keyboard = [
        [KeyboardButton("Смотреть ответы")],
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
        #"/clear – полностью очищает чат с ботом\n"
        #"/support – позволяет отправить запрос в тех. поддержку бота\n"
    )
    await update.message.reply_text(text)

# Команда /clear
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Функция ещё не готова")

    context.user_data.clear
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


########################## ОБРАБОТКА ВХОДЯЩИХ ТЕКСТОВЫХ СООБЩЕНИЙ #########################
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    quiz_state = context.user_data.get('quiz_state')
    mode = context.user_data.get('mode', MODE_CREATE)

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

    # Обработка свободного текста
    else:
        # В режиме "текст в C-Test" — обрабатываем текст
        if mode == MODE_CREATE:
            try:
                output = process_ctest(user_text)

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
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    app.add_handler(
        MessageHandler(~filters.TEXT, handle_non_text)
    )

    print("The bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
