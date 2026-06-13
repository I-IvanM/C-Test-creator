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
import re
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
# BOT_TOKEN = "8979999144:AAGUzWZffpYlTeJSCxDrh_Sly_fM9JnUMls"
print("TOKEN:", BOT_TOKEN)

MODE_CREATE = "create"
MODE_GENERATE = "generate"

STATE_QUESTION_1 = "question_1"
STATE_QUESTION_2 = "question_2"
STATE_QUESTION_3 = "question_3"
STATE_COMPLETED = 'completed'

################ ^ ЗАПУСТИЛСЯ И ХОРОШО ^ ##################

################### достать основную клавиатуру ######################
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("текст в C-Test"), KeyboardButton("Генерировать")],
        [KeyboardButton("Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

############# достать клавиатуру под режим генерации ################
def get_quiz_keyboard():
    keyboard = [[KeyboardButton("Вернуться в главное меню")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


################## превращение в c-test ######################
def process_ctest(user_text: str) -> str:
    #Обработка входного текста.
   
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
                output += words[j][:num//2] + "___ "
            # Проверка на символ, который не буква
            elif words[j] not in "abcdeghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZабвгдежзийклмнопрстуфхцчшщъыьэюяАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ":
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
            elif words[j] not in "abcdeghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZабвгдежзийклмнопрстуфхцчшщъыьэюяАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ":
                output = output[:-1]
                output += words[j] + " "
                count -= 1
            else:
                output += words[j] + " "

    return output

##################### Обработка ответов перед генерацией ########################
def process_quiz(quiz_state: str, user_text: str, answers: dict):
    if quiz_state == STATE_QUESTION_1:
        answers['language'] = user_text
        text = "Какого уровня должен быть C-Test (A1, A2, B1, B2, C1)?"
        return STATE_QUESTION_2, text, answers

    elif quiz_state == STATE_QUESTION_2:
        answers['level'] = user_text
        text = "Есть ли у Вас пожелания к тексту?"
        return STATE_QUESTION_3, text,answers

    elif quiz_state == STATE_QUESTION_3:
        answers['wishes'] = user_text
        text = (f"Отлично, текст генерируется и скоро будет готов!\n\n"
                f"Ваши ответы:\n"
                f"• Язык: {answers['language']}\n"
                f"• Уровень: {answers['level']}\n"
                f"• Пожелания: {answers['wishes']}\n\n"
                )
        return STATE_COMPLETED, text, answers
    
    else:
        return quiz_state, "Ошибка состояния",answers

######################### работа бота #########################

######################### START #########################
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "C-Tester \nЯ могу превратить ваш текст в C-Test или сгенерировать новый С-Test специально для вас!"
    context.user_data['mode'] = MODE_CREATE
    context.user_data['quiz_state'] = None

    reply_markup=get_main_keyboard()

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

################ КОМАНДА ПОМОЩЬ ######################

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Доступные режимы:\n"
        "• «текст в C-Test» — Вы можете отправить любой текст, в котором есть хотя бы несколько предложений и бот преобразует его в C-Test\n"
        "• «Генерировать» — бот задаст Вам несколько вопросов и создаст новый C-Test специально для вас\n\n"
        "Используйте кнопки ниже для переключения режимов."
    )
    await update.message.reply_text(help_text)

########################## ОБРАБОТКА ВХОДЯЩИХ ТЕКСТОВЫХ СООБЩЕНИЙ #########################
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text

    mode = context.user_data.get('mode', MODE_CREATE)
    quiz_state = context.user_data.get('quiz_state')

    #Команда переключения в режим "текст в C-Test"
    if user_text == "текст в C-Test":
        context.user_data['mode'] = MODE_CREATE
        context.user_data['quiz_state'] = None
        await update.message.reply_text(
            "✅ Переключено в режим \"текст в C-Test\".\n"
            "Отправьте ваш текст — бот превратит его в C-Test!",
            reply_markup=get_main_keyboard()
        )

    # Команда переключения в режим генерации
    elif user_text == "Генерировать":
        context.user_data['mode'] = MODE_GENERATE
        context.user_data['quiz_state'] = STATE_QUESTION_1
        context.user_data['answers'] = {}

        await update.message.reply_text(
            "🐙 Переключено в режим Генерации.\n\n"
            "Вопрос 1: На каком языке нужен текст?",
            reply_markup=get_quiz_keyboard()
        )

    # Команда отмены генерации
    elif user_text == "Вернуться в главное меню":
        context.user_data['mode'] = MODE_CREATE
        context.user_data['quiz_state'] = None
        await update.message.reply_text(
            "❌ Генерация отменена.\n"
            "Переключено в режим обработки вашего текста.",
            reply_markup=get_main_keyboard()
        )

    # Команда помощь
    elif user_text == "Помощь":
        await help_command(update, context)

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
            # Режим генерации — обрабатываем ответы на вопросы
            quiz_state = context.user_data['quiz_state']
            answers = context.user_data.get('answers', {})

            new_state, reply_text, answers = process_quiz(quiz_state, user_text, answers)
            if new_state == STATE_COMPLETED:
                context.user_data["mode"] = MODE_CREATE
                context.user_data["quiz_state"] = None
                keyboard = get_main_keyboard()
            else:
                context.user_data["quiz_state"] = new_state
                context.user_data["answers"] = answers

            await update.message.reply_text(
                reply_text,
                reply_markup=get_quiz_keyboard()
            )

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
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    app.add_handler(
        MessageHandler(~filters.TEXT, handle_non_text)
    )

    print("The bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()