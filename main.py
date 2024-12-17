import re
import sqlite3
import sys
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import requests
from apscheduler.triggers.cron import CronTrigger
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackContext, CallbackQueryHandler, filters
sys.stdout.reconfigure(encoding='utf-8')

TOKEN = "7575170127:AAG187KgonmZ-36WpzhIH1EGB0MYDxKOr4w"
OAUTH_TOKEN = 'y0_AgAAAAA_Z7qeAATuwQAAAAEXbTStAADgsfFcTkhES5l0VNi7NUW4M3pZeg'#OAUTH_TOKEN
FOLDER_ID = 'b1gpla5n2g0jm6f120el'#'<идентификатор_каталога>'
API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

# Создаем планировщик
scheduler = AsyncIOScheduler()

DATE, TIME, DESCRIPTION = range(3)

WAITING_FOR_REQUEST_FOOD, CHOOSE_FOOD = range(2)

EVENT_TITLE, EVENT_DATE = range(2)
WAITING_FOR_REQUEST_SPORT, CHOOSE_TYPE, ASK_SAVE_EVENT, GET_EVENT_NAME, CHOOSE_FREQUENCY, ASK_IF_TIME_NORMAL = range(6)

WAITING_FOR_TIME = range(1)

# Константы для состояний
CHANGE_DAY, MODIFY_ACTION, MODIFY_TIME = range(3)
EVENT_NAME, EVENT_DAY_OF_WEEK = range(2)
WAIT_FOR_REMINDER_NUMBER = range(1)

daysi = [
    "Понедельника", "Вторника", "Среды", "Четверга", "Пятницы", "Субботы", "Воскресенья"
]

days_of_week = {
        "Понедельника": "monday",
        "Вторника": "tuesday",
        "Среды": "wednesday",
        "Четверга": "thursday",
        "Пятницы": "friday",
        "Субботы": "saturday",
        "Воскресенья": "sunday"
    }

days_of_week_db1 = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
    "sunday": 7
}

# Подключаемся к базе данных
conn3 = sqlite3.connect('user_schedule.db')
cursor3 = conn3.cursor()

# Создаем таблицу, если ее еще нет
cursor3.execute('''
CREATE TABLE IF NOT EXISTS user_schedule (
    user_id INTEGER PRIMARY KEY,
    monday TEXT,
    tuesday TEXT,
    wednesday TEXT,
    thursday TEXT,
    friday TEXT,
    saturday TEXT,
    sunday TEXT
)
''')

conn3.commit()
conn3.close()


# Список дней недели
days_of_week_db = {
    "Понедельника": "monday",
    "Вторника": "tuesday",
    "Среды": "wednesday",
    "Четверга": "thursday",
    "Пятницы": "friday",
    "Субботы": "saturday",
    "Воскресенья": "sunday"
}

async def view_reminders_for_delete(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Проверяем, есть ли у пользователя напоминания
    if 'reminders' not in context.user_data or not context.user_data['reminders']:
        await update.message.reply_text("У вас нет напоминаний.")
        return

    reminders = context.user_data['reminders']

    # Формируем список напоминаний
    reminder_list = ''
    for i in range(0, len(reminders)):
        reminder_list += "\n" + f"{i + 1}. " + f"Событие: {reminders[i]['event_name']}, День: {reminders[i]['day_of_week']}, Время: {reminders[i]['time']}"

    await update.message.reply_text(f"Ваши напоминания:\n{reminder_list}\n\nВведите номер напоминания, которое хотите удалить.")
    return WAIT_FOR_REMINDER_NUMBER


async def handle_reminder_deletion(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Получаем номер напоминания, которое хочет удалить пользователь
    try:
        reminder_number = int(update.message.text) - 1
        reminders = context.user_data['reminders']

        scheduler.remove_job(f"reminder_{update.effective_chat.id}{reminders[reminder_number]['event_name']}{reminders[reminder_number]['day_of_week']}{reminders[reminder_number]['time']}",)
        pop_num = context.user_data['reminders'].pop(reminder_number)
        await update.message.reply_text("Напоминание успешно удалено!")

    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректный номер напоминания.")
        return WAIT_FOR_REMINDER_NUMBER

    return ConversationHandler.END

async def add_reminder_to_user_data(context: CallbackContext, chat_id, event_name, day_of_week, time_str):
    # Проверяем, есть ли уже список напоминаний у пользователя
    if 'reminders' not in context.user_data:
        context.user_data['reminders'] = []

    # Добавляем новое напоминание в список
    context.user_data['reminders'].append({
        'event_name': event_name,
        'day_of_week': day_of_week,
        'time': time_str
    })

async def view_reminders(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Проверяем, есть ли у пользователя напоминания
    if 'reminders' not in context.user_data or not context.user_data['reminders']:
        await update.message.reply_text("У вас нет напоминаний.")
        return

    reminders = context.user_data['reminders']

    # Формируем список напоминаний
    reminder_list = "\n".join(
        [f"Событие: {reminder['event_name']}, День: {reminder['day_of_week']}, Время: {reminder['time']}"
         for reminder in reminders])

    await update.message.reply_text(f"Ваши напоминания:\n{reminder_list}")


async def start_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите название события для напоминания:")
    return EVENT_NAME

async def get_event_name_for_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    event_name = update.message.text
    context.user_data['event_name'] = event_name

    await update.message.reply_text(f"Введите дни недели и время в формате:\nпн 9:00\nчт 14:00")
    return EVENT_DAY_OF_WEEK

dict_days = {"пн": "mon",
    "вт": "tue",
    "ср": "wed",
    "чт": "thu",
    "пт": "fri",
    "сб": "sat",
    "вс": "sun"}

async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text
    answer = answer.lower()

    pattern = r"(\w{2}) (\d{1,2}):(\d{2})"

    matches = re.findall(pattern, answer)
    for match in matches:
        days, hour, minute = match
        day = dict_days[days]
        scheduler.add_job(
            send_reminder,
            trigger=CronTrigger(day_of_week=day, hour=hour, minute=minute),
            context={'chat_id': update.effective_chat.id, 'event_name': context.user_data['event_name']},
            id=f"reminder_{update.effective_chat.id}{context.user_data['event_name']}{day}{hour}:{minute}",
            replace_existing=True,  # Заменяет, если уже существует задача с таким ID
            args=[context, update.effective_chat.id, context.user_data['event_name']]
        )
        await add_reminder_to_user_data(context, update.effective_chat.id, context.user_data['event_name'],
                                  day, f"{hour}:{minute}")

    await update.message.reply_text("Отлично! Напоминание сохранено!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Начальная команда /change_schedule
async def change_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [[InlineKeyboardButton(day, callback_data=day)] for day in daysi]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Для какого дня будем вносить изменения?", reply_markup=reply_markup)
    return CHANGE_DAY


# Обработка выбора дня недели
async def choose_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    # Сохраняем выбранный день недели
    selected_day = query.data
    context.user_data["selected_day"] = selected_day

    # Получаем данные из базы
    user_id = update.effective_chat.id
    conn = sqlite3.connect('user_schedule.db')
    cursor = conn.cursor()

    day_column = days_of_week_db[selected_day]
    cursor.execute("SELECT * FROM user_schedule WHERE user_id = ?", (user_id,))
    current_data = cursor.fetchone()

    if current_data:
        current_time = current_data[days_of_week_db1[days_of_week_db[selected_day]]]
    else:
        current_time = None

    conn.close()

    # Отправляем текущее свободное время и спрашиваем, что делать
    if current_time:
        await query.edit_message_text(f"Ваше текущее свободное время для {selected_day}: {current_time}. "
                                      "Хотите добавить или удалить время?", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Добавить время", callback_data="add_time"),
             InlineKeyboardButton("Удалить время", callback_data="remove_time")]
        ]))
    else:
        await query.edit_message_text(f"У вас нет свободного времени для {selected_day}. "
                                      "Хотите добавить время?", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Добавить время", callback_data="add_time")]
        ]))
    return MODIFY_ACTION


async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    action = query.data
    context.user_data["action"] = action

    if action == "add_time":
        await query.message.reply_text("Введите время, которое вы хотите добавить (например, 9:00, 18:00).", reply_markup=ReplyKeyboardRemove())
    elif action == "remove_time":
        await query.message.reply_text("Введите время, которое вы хотите удалить (например, 9:00, 18:00).", reply_markup=ReplyKeyboardRemove())

    return MODIFY_TIME


# Обработка добавления или удаления времени
async def modify_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_chat.id
    user_input = update.message.text.strip()
    selected_day = context.user_data.get("selected_day")

    # Сохраняем добавленное или удаленное время в базу
    conn = sqlite3.connect('user_schedule.db')
    cursor = conn.cursor()

    # Получаем текущее свободное время для дня недели
    day_column = days_of_week_db[selected_day]
    cursor.execute("SELECT * FROM user_schedule WHERE user_id = ?", (user_id,))
    current_data = cursor.fetchone()

    action = context.user_data.get("action")

    if current_data:
        current_time = current_data[days_of_week_db1[days_of_week_db[selected_day]]]
    else:
        current_data = [user_id, None, None, None, None, None, None, None]
        current_time = None

    # Обработка добавления времени
    if action == "add_time":
        new_time = user_input.split(",")  # Допустим, ввод через запятую
        updated_time = f"{current_time}, {', '.join(new_time)}" if current_time else ", ".join(new_time)

        cursor.execute(f'''
        INSERT OR REPLACE INTO user_schedule (user_id, monday, tuesday, wednesday, thursday, friday, saturday, sunday)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, updated_time if day_column == "monday" else current_data[1],
              updated_time if day_column == "tuesday" else current_data[2],
              updated_time if day_column == "wednesday" else current_data[3],
              updated_time if day_column == "thursday" else current_data[4],
              updated_time if day_column == "friday" else current_data[5],
              updated_time if day_column == "saturday" else current_data[6],
              updated_time if day_column == "sunday" else current_data[7]))
        await update.message.reply_text(f"Ваше расписание для {selected_day} обновлено!")

    # Обработка удаления времени
    elif action == "remove_time":
        if (current_data != None):
            if user_input in current_time:
                # Удаляем введенное время из списка (удаляем точные совпадения)
                updated_time = ', '.join([time.strip() for time in current_time.split(",") if time.strip() not in user_input.strip()])

                # Если оставшийся список пустой, то записываем NULL (или пустую строку)
                updated_time = updated_time if updated_time else None

                # Обновляем базу данных с новым временем
                cursor.execute(f'''
                        INSERT OR REPLACE INTO user_schedule (user_id, monday, tuesday, wednesday, thursday, friday, saturday, sunday)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (user_id, updated_time if day_column == "monday" else current_data[1],
                              updated_time if day_column == "tuesday" else current_data[2],
                              updated_time if day_column == "wednesday" else current_data[3],
                              updated_time if day_column == "thursday" else current_data[4],
                              updated_time if day_column == "friday" else current_data[5],
                              updated_time if day_column == "saturday" else current_data[6],
                              updated_time if day_column == "sunday" else current_data[7]))
                await update.message.reply_text(
                    f"Ваше свободное время для {selected_day} обновлено! Время {user_input} удалено.")
            else:
                await update.message.reply_text(
                    f"Время {user_input} не найдено в вашем расписании для {selected_day}.")
        else:
            await update.message.reply_text(f"У вас нет свободного времени для удаления в {selected_day}.")

    conn.commit()
    conn.close()

    return ConversationHandler.END

# Опрос по времени, когда пользователь свободен
async def ask_free_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_chat.id
    context.user_data["day_index"] = 0  # Начинаем с Понедельника

    # Спрашиваем о свободном времени для первого дня (Понедельник)
    await update.message.reply_text(
        f"Для начала введите свободное время для {daysi[0]} (например, 9:00, 18:00). Если у вас в этот день нет свободного времени, напишите 'Нет'.")
    return WAITING_FOR_TIME


# Обработка ответов пользователя
async def handle_free_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_chat.id
    free_time = update.message.text.strip()

    # Сохраняем данные в базу данных
    day_index = context.user_data["day_index"]
    day_column = days_of_week[daysi[day_index]]

    # Подключаемся к базе данных
    conn3 = sqlite3.connect('user_schedule.db')
    cursor3 = conn3.cursor()

    cursor3.execute("SELECT * FROM user_schedule WHERE user_id = ?", (user_id,))
    current_data = cursor3.fetchone()

    if current_data is None:
        current_data = [user_id, None, None, None, None, None, None, None]

    # Если свободное время не пустое, сохраняем его
    cursor3.execute(f'''
            INSERT OR REPLACE INTO user_schedule (user_id, monday, tuesday, wednesday, thursday, friday, saturday, sunday)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, current_data[1] if day_column != "monday" else free_time,
                  current_data[2] if day_column != "tuesday" else free_time,
                  current_data[3] if day_column != "wednesday" else free_time,
                  current_data[4] if day_column != "thursday" else free_time,
                  current_data[5] if day_column != "friday" else free_time,
                  current_data[6] if day_column != "saturday" else free_time,
                  current_data[7] if day_column != "sunday" else free_time))

    conn3.commit()
    conn3.close()

    # Переходим к следующему дню недели
    day_index += 1
    if day_index < len(days_of_week):
        context.user_data["day_index"] = day_index
        await update.message.reply_text(
            f"Введите свободное время для {daysi[day_index]} (например, 9:00, 18:00). Если у вас в этот день нет свободного времени, напишите 'Нет'.")
        return WAITING_FOR_TIME
    else:
        await update.message.reply_text("Спасибо! Все данные сохранены!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

# Календарь и напоминания

async def send_reminder(context: ContextTypes.DEFAULT_TYPE, chat_id, title):
    await context.bot.send_message(chat_id=chat_id, text=f"Напоминание: {title}")

def get_iam_token():
    response = requests.post(
        'https://iam.api.cloud.yandex.net/iam/v1/tokens',
        json={'yandexPassportOauthToken': OAUTH_TOKEN}
    )
    response.raise_for_status()
    return response.json()['iamToken']

AGE, WEIGHT, HEIGHT, HEALTH = range(4)

conn = sqlite3.connect("survey_results.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    age INTEGER,
    weight REAL,
    height REAL,
    health TEXT
)
''')
conn.commit()

# Команды бота

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я - бот, который поможет вам следить за здоровым образом жизни! Я много чего умею, весь список команд можете увидеть в меню!\n "
                                    "Для начала советую установить свое свободное время с помощью команды /set_schedule, чтобы я понимал, когда можно ставить тренировки\n"
                                    "Если в дальнейшем захотите изменить его, используйте команду /change_schedule \n"
                                    "Теперь мы можем перейти к моим основным функциям:\n"
                                    "    * Команда /generate_sport поможет вам подобрать тренировки, а также выбрать расписание для них. Также вы можете установить еженедельные напоминания (используйте команду /set_reminder и /delete_reminder для добавления и удаления напоминаний)\n"
                                    "    * Команда /view_reminders покажет все ваши текущие напоминания\n"
                                    "    * Команда /generate_food выведет вам разнообразные рецепты. Попробуйте, вдруг вам что-нибудь понравится!\n"
                                    "С помощью запросов при генерации вы можете уточнять свои цели и желания\n"
                                    "Генерация тренировок и рецептов может быть долгой, не пугайтесь! Просто я пытаюсь выбрать лучшее для вас!\n"
                                    "Если вдруг я сломался - пишите @fgjkps")



    chat_id = update.effective_chat.id
    event_name = "Прием_пищи"  # Название события по умолчанию
    hour = 9  # Час для напоминания (например, 9 утра)
    minute = 0  # Минуты для напоминания (например, ровно в час)

    # ID задачи на основе chat_id и event_name
    job_id = f"reminder_{update.effective_chat.id}Напоминание о генерации рецептовЕжедневно9:00"

    # Проверяем, существует ли задача с таким ID
    if scheduler.get_job(job_id) is None:
        # Создаем ежедневное напоминание
        scheduler.add_job(
            send_reminder,
            trigger=CronTrigger(hour=hour, minute=minute),  # Ежедневный триггер
            context={'chat_id': chat_id, 'event_name': event_name},
            id=job_id,
            replace_existing=True,  # Заменяет, если уже существует задача с таким ID
            args=[context, chat_id, "Доброе утро! Не забудьте сгенерировать рецепты на сегодня!"]
        )
        print(
            f"Ежедневное напоминание '{event_name}' установлено на {hour:02d}:{minute:02d}.")
        await add_reminder_to_user_data(context, update.effective_chat.id, "Напоминание о генерации рецептов", "Ежедневно", f"9:00")
    else:
        print("Ежедневное напоминание уже установлено!")

async def request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Давайте начнем опрос! Какой у вас возраст?")
    return AGE

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["age"] = update.message.text
    await update.message.reply_text("Спасибо! Какой у вас вес (в кг)?")
    return WEIGHT

async def ask_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["weight"] = update.message.text
    await update.message.reply_text("Отлично! Укажите ваш рост (в см).")
    return HEIGHT

async def ask_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["height"] = update.message.text
    await update.message.reply_text("Хорошо! Есть ли у вас какие-то хронические заболевания? Напишите да или нет.")
    return HEALTH

async def ask_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["health"] = update.message.text

    save_to_db(
        user_id=update.message.from_user.id,
        age=context.user_data["age"],
        weight=context.user_data["weight"],
        height=context.user_data["height"],
        health=context.user_data["health"]
    )

    await update.message.reply_text("Спасибо! Ваши ответы сохранены.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

# Функии для работы с базой данных

def save_to_db(user_id, age, weight, height, health):
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, age, weight, height, health)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, age, weight, height, health))
    conn.commit()

def get_user_data(user_id):
    cursor.execute("SELECT age, weight, height, health FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result

async def my_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if user_data:
        age, weight, height, health = user_data
        response_text = (f"Вот ваши данные:\n"
                         f"Возраст: {age} лет\n"
                         f"Вес: {weight} кг\n"
                         f"Рост: {height} см\n"
                         f"Состояние здоровья: {health}")
    else:
        response_text = "У вас нет сохранённых данных. Пройдите опрос командой /request."

    await update.message.reply_text(response_text)

# GPT

async def gpt_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Запрашиваем у пользователя его запрос
    keyboard = [
        [InlineKeyboardButton("Завтрак", callback_data='breakfast')],
        [InlineKeyboardButton("Обед", callback_data='lunch')],
        [InlineKeyboardButton("Ужин", callback_data='dinner')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Для чего бы вы хотели рецепты?", reply_markup=reply_markup)
    return CHOOSE_FOOD

async def choose_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    choice = query.data  # Получаем выбор пользователя
    context.user_data["food_type"] = choice

    await query.message.reply_text("Введите ваш запрос (например: я хочу сбросить вес / я хочу много энергии) и пожелания по ингридиентам, если они есть:", reply_markup=ReplyKeyboardRemove())
    return WAITING_FOR_REQUEST_SPORT

async def generate_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = context.user_data["food_type"]
    if choice == 'breakfast':
        s = "Ты - опытный повар-диетолог. Напиши понятные рецепты для 3 разных завтраков основываясь на целях пользователя и его предпочтениях. Пиши без воды. Продукты должны быть доступные для всех. Также пиши рецепт приготоваления.Ответ выводи в формате: <Завтрак1/Завтрак2/Завтрак3/Завтрак4>\n <Название> \n <Ингредиенты> \n <Рецепт>. Рецепты пиши более менее подробно."
    elif choice == 'lunch':
        s = "Ты - опытный повар-диетолог. Напиши понятные рецепты для 3 разных обедов основываясь на целях пользователя и его предпочтениях. Пиши без воды. Продукты должны быть доступные для всех. Также пиши рецепт приготоваления.Ответ выводи в формате: <Обед1/Обед2/Обед3/Обед4>\n <Название> \n <Ингредиенты> \n <Рецепт>. Рецепты пиши более менее подробно."
    else:
        s = "Ты - опытный повар-диетолог. Напиши понятные рецепты для 3 разных ужинов основываясь на целях пользователя и его предпочтениях. Пиши без воды. Продукты должны быть доступные для всех. Также пиши рецепт приготоваления.Ответ выводи в формате: <Ужин1/Ужин2/Ужин3/Ужин4>\n <Название> \n <Ингредиенты> \n <Рецепт>. Рецепты пиши более менее подробно."

    user_text = update.message.text

    try:
        iam_token = get_iam_token()
    except requests.RequestException as e:
        await update.message.reply_text('Произошла ошибка при получении токена.')
        return ConversationHandler.END  # Завершаем разговор в случае ошибки

    # Формируем запрос к Yandex GPT
    data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt",
        "completionOptions": {"temperature": 0.3, "maxTokens": 1000},
        "messages": [
            {"role": "system", "text": s},
            {"role": "user", "text": user_text}
        ]
    }

    try:
        response = requests.post(
            API_URL,
            headers={"Accept": "application/json", "Authorization": f"Bearer {iam_token}"},
            json=data
        )
        response.raise_for_status()
        result = response.json()
        answer = result.get('result', {}).get('alternatives', [{}])[0].get('message', {}).get('text', 'Ошибка получения ответа.')
    except requests.RequestException as e:
        answer = 'Произошла ошибка при запросе к Yandex GPT.'

    await update.message.reply_text(answer)
    return ConversationHandler.END

async def gpt_sport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Запрашиваем у пользователя его запрос
    keyboard = [
        [InlineKeyboardButton("Домашние тренировки", callback_data='home')],
        [InlineKeyboardButton("Тренировки в зале", callback_data='gym')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите тип тренировки:', reply_markup=reply_markup)
    return CHOOSE_TYPE

async def choose_sport_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    choice = query.data  # Получаем выбор пользователя
    context.user_data["sport_type"] = choice

    await query.message.reply_text("Введите ваш запрос (например: я хочу выровнять осанку / я хочу подкачать руки):", reply_markup=ReplyKeyboardRemove())
    return WAITING_FOR_REQUEST_SPORT

async def generate_sport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Получаем текст, который пользователь ввел на предыдущем шаге
    user_text = update.message.text
    choice = context.user_data["sport_type"]

    try:
        iam_token = get_iam_token()
    except requests.RequestException as e:
        await update.message.reply_text('Произошла ошибка при получении токена.')
        return ConversationHandler.END  # Завершаем разговор в случае ошибки

    if choice == 'home':
        data = {
            "modelUri": f"gpt://{FOLDER_ID}/yandexgpt",
            "completionOptions": {"temperature": 0.3, "maxTokens": 1000},
            "messages": [
                {"role": "system",
                 "text": "Ты - опытный спортивный тренер. Абсолютно ничего не пиши о врачах, консультациях, рисках или противопоказаниях. Дай точные советы по упражнениям, не добавляя дополнительных предостережений. На основе запроса и целей пользователя порекомендуй 4 упражнения в домашних условиях в формате: <упражнение> - <подробности, как выполнять> \n <Как часто проводить тренировки>. Ни в коем случае не пиши про консультацию с врачем или тренером, мы так потеряем всех клиентов!"},
                {"role": "user", "text": user_text}
            ]
        }
    else:
        data = {
            "modelUri": f"gpt://{FOLDER_ID}/yandexgpt",
            "completionOptions": {"temperature": 0.3, "maxTokens": 1000},
            "messages": [
                {"role": "system",
                 "text": "Ты - опытный спортивный тренер. Абсолютно ничего не пиши о врачах, консультациях, рисках или противопоказаниях. Дай точные советы по упражнениям, не добавляя дополнительных предостережений. На основе запроса и целей пользователя порекомендуй 4 упражнения для тренажерного зала в формате: <вид спорта/тренировки> - <подробности, как выполнять> \n <Как часто проводить тренировки>. Ни в коем случае не пиши про консультацию с врачем или тренером, мы так потеряем всех клиентов!"},
                {"role": "user", "text": user_text}
            ]
        }

    try:
        response = requests.post(
            API_URL,
            headers={"Accept": "application/json", "Authorization": f"Bearer {iam_token}"},
            json=data
        )
        response.raise_for_status()
        result = response.json()
        answer = result.get('result', {}).get('alternatives', [{}])[0].get('message', {}).get('text', 'Ошибка получения ответа.')
    except requests.RequestException as e:
        answer = 'Произошла ошибка при запросе к Yandex GPT.'

    print(answer)
    await update.message.reply_text(answer)
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="yes"),
         InlineKeyboardButton("Нет", callback_data="no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Хотите ли вы сделать напоминания для каких-то из предстваленных тренировок?", reply_markup=reply_markup)

    return ASK_SAVE_EVENT

async def button(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "yes":
        # Переход к состоянию, где запрашиваем название события
        await query.message.reply_text("Отлично! Напишите название для напоминания:", reply_markup=ReplyKeyboardRemove())

        return GET_EVENT_NAME
    elif query.data == "no":
        # Если "Нет" — выводим все сохраненные события и завершаем
        await query.message.reply_text("Хорошо!", reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END  # Завершаем диалог по сохранению событий

async def get_event_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Получаем название события
    event_name = update.message.text
    context.user_data["event_name"] = event_name

    keyboard = [
        [InlineKeyboardButton("1 раз в неделю", callback_data="1"),
         InlineKeyboardButton("2 раза в неделю", callback_data="2")],
        [InlineKeyboardButton("3 раза в неделю", callback_data="3"),
         InlineKeyboardButton("4 раза в неделю", callback_data="4")],
        [InlineKeyboardButton("5 раз в неделю", callback_data="5"),
         InlineKeyboardButton("6 раз в неделю", callback_data="6")],
        [InlineKeyboardButton("7 раз в неделю", callback_data="7")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Тренировка '{event_name}' сохранена. Сколько раз в неделю хотите заниматься?",
                                    reply_markup=reply_markup)

    return CHOOSE_FREQUENCY


async def choose_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    # Сохраняем выбранную частоту тренировок
    frequency = query.data
    context.user_data["frequency"] = frequency

    chat_id = update.effective_chat.id

    # Подтверждение создания события и завершение диалога
    event_name = context.user_data.get("event_name")

    try:
        iam_token = get_iam_token()
    except requests.RequestException as e:
        await update.message.reply_text('Произошла ошибка при получении токена.')
        return ConversationHandler.END  # Завершаем разговор в случае ошибки

    user_id = update.effective_chat.id

    # Подключаемся к базе данных
    conn = sqlite3.connect('user_schedule.db')
    cursor = conn.cursor()

    # Получаем данные из таблицы по user_id
    cursor.execute("SELECT * FROM user_schedule WHERE user_id = ?", (user_id,))
    current_data = cursor.fetchone()

    conn.close()

    if current_data:
        # Составляем строку с расписанием
        schedule = []
        days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

        for i, day in enumerate(days_of_week, start=1):  # Начинаем с 1, потому что в базе первые данные - это user_id
            free_time = current_data[i]  # Получаем свободное время для дня
            if free_time:  # Если свободное время есть, добавляем в список
                schedule.append(f"{day.capitalize()} - {free_time}")

        if schedule:

            # Формируем запрос к Yandex GPT
            data = {
                "modelUri": f"gpt://{FOLDER_ID}/yandexgpt",
                "completionOptions": {"temperature": 0.3, "maxTokens": 1000},
                "messages": [
                    {"role": "system",
                     "text": "Ты - опытный спортивный тренер. Нужно чтоб ты вывел подходящее время для тренировки. Тебе дается время пользователя, когда он может тренироваться. Выведи ровно столько результатов, сколько раз пользователь хочет заниматься в неделю. Выбери наилучшее время (лучше всего утром/днем), учитывая частоту тренировок - то есть выведи ровно столько времени, сколько просят. Ответ выведи в формате: mon 9:00 \n tue 9:00 \n wed 9:00 \n thu 9:00 \n fri 9:00 \n sat 9:00 \n sun 9:00. Ничего кроме этого не пиши. Не пиши 'или' и других ненужных слов."},
                    {"role": "user", "text": f"Мое свободное время для тренировок: \n {'.'.join(schedule)}. Я хочу заниматься {frequency} раз в неделю"}
                ]
            }

            try:
                response = requests.post(
                    API_URL,
                    headers={"Accept": "application/json", "Authorization": f"Bearer {iam_token}"},
                    json=data
                )
                response.raise_for_status()
                result = response.json()
                answer = result.get('result', {}).get('alternatives', [{}])[0].get('message', {}).get('text',
                                                                                                      'Ошибка получения ответа.')
            except requests.RequestException as e:
                answer = 'Произошла ошибка при запросе к Yandex GPT.'

            print(schedule)
            print(answer)
            if answer != 'Произошла ошибка при запросе к Yandex GPT.':
                pattern = r"(\w{3}) (\d{1,2}):(\d{2})"

                matches = re.findall(pattern, answer)
                ans = ''

                # Выводим извлеченные данные
                for match in matches:
                    day, hour, minute = match
                    ans += f'\n{day} - {hour}:{minute}'

                keyboard = [
                    [InlineKeyboardButton("Да", callback_data="yes"),
                     InlineKeyboardButton("Нет", callback_data="no")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.user_data["schedule"] = answer
                await query.message.reply_text("Вас устроит такое расписание?" + ans, reply_markup=reply_markup)
                return ASK_IF_TIME_NORMAL
        else:
            await query.message.reply_text("У вас нет свободного времени, сохраненного в расписании. Используйте /set_schedule для заполнения своего свободного времени, а далее создайте напоминание с помощью /set_reminder", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
    else:
        await query.message.reply_text("Не найдено ваше расписание. Вы можете заполнить его с помощью команды /set_schedule", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("Да", callback_data="yes"),
         InlineKeyboardButton("Нет", callback_data="no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Хотите ли вы добавить еще тренировку?", reply_markup=reply_markup)
    return ASK_SAVE_EVENT

async def is_time_normal(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "yes":
        answer = context.user_data["schedule"]
        pattern = r"(\w{3}) (\d{1,2}):(\d{2})"

        matches = re.findall(pattern, answer)
        for match in matches:
            day, hour, minute = match
            scheduler.add_job(
                send_reminder,
                trigger=CronTrigger(day_of_week=day, hour=hour, minute=minute),
                context={'chat_id': update.effective_chat.id, 'event_name': "Пора заниматься! Сейчас по плану: " + context.user_data['event_name']},
                id=f"reminder_{update.effective_chat.id}{context.user_data['event_name']}{day}{hour}:{minute}",
                replace_existing=True, # Заменяет, если уже существует задача с таким ID
                args = [context, update.effective_chat.id, context.user_data['event_name']]
            )
            await add_reminder_to_user_data(context, update.effective_chat.id, context.user_data['event_name'],
                                      day, f"{hour}:{minute}")

        await query.message.reply_text("Отлично! Расписание сохранено", reply_markup=ReplyKeyboardRemove())

        keyboard = [
            [InlineKeyboardButton("Да", callback_data="yes"),
             InlineKeyboardButton("Нет", callback_data="no")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Хотите ли вы добавить еще событие?", reply_markup=reply_markup)
        return ASK_SAVE_EVENT

    elif query.data == "no":
        # Если "Нет" — выводим все сохраненные события и завершаем
        await query.message.reply_text("Тогда вы можете установить расписание с напоминанием сами с помощью команды /set_reminder", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END  # Завершаем диалог по сохранению событий


def main():
    application = Application.builder().token(TOKEN).build()

    conv_handler_request = ConversationHandler(
        entry_points=[CommandHandler("request", request)],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_weight)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_height)],
            HEALTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_health)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_handler_food = ConversationHandler(
        entry_points=[CommandHandler("generate_food", gpt_food)],
        states={
            CHOOSE_FOOD: [CallbackQueryHandler(choose_food)],
            WAITING_FOR_REQUEST_FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_food)],
            # Обработка запроса пользователя
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_handler_sport = ConversationHandler(
        entry_points=[CommandHandler("generate_sport", gpt_sport)],
        states={
            WAITING_FOR_REQUEST_SPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_sport)],
            CHOOSE_TYPE: [CallbackQueryHandler(choose_sport_type)],
            ASK_SAVE_EVENT: [CallbackQueryHandler(button)],
            GET_EVENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_event_name)],
            CHOOSE_FREQUENCY: [CallbackQueryHandler(choose_frequency)],
            ASK_IF_TIME_NORMAL: [CallbackQueryHandler(is_time_normal)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_schedule = ConversationHandler(
        entry_points=[CommandHandler("set_schedule", ask_free_time)],
        states={
            WAITING_FOR_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_time)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_change_schedule = ConversationHandler(
        entry_points=[CommandHandler('change_schedule', change_schedule)],
        states={
            CHANGE_DAY: [CallbackQueryHandler(choose_day)],
            MODIFY_ACTION: [CallbackQueryHandler(choose_action)],
            MODIFY_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, modify_time)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_reminder = ConversationHandler(
        entry_points=[CommandHandler('set_reminder', start_reminder)],
        states={
            EVENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_event_name_for_reminder)],
            EVENT_DAY_OF_WEEK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_reminder_delete = ConversationHandler(
        entry_points=[CommandHandler('delete_reminder', view_reminders_for_delete)],
        states={
            WAIT_FOR_REMINDER_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reminder_deletion)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_reminder_delete)

    application.add_handler(conv_change_schedule)
    application.add_handler(conv_reminder)
    application.add_handler(conv_schedule)

    #application.add_handler(conv_handler_request)
    application.add_handler(conv_handler_food)
    application.add_handler(conv_handler_sport)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("view_reminders", view_reminders))
    #application.add_handler(CommandHandler("mydata", my_data))

    scheduler.start()

    application.run_polling()

if __name__ == '__main__':
    main()
