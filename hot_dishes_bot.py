# Модуль для работы с путями к файлам
import os
# Модуль для запросов в интернет (ставится вместе с pytelegrambotapi)
import requests
# Подключаем модуль для работы с базой данных SQLite
import sqlite3
# Подключаем модуль для Телеграма
import telebot
# Импортируем типы из модуля, чтобы создавать кнопки
from telebot import types

# Указываем токен, полученный у @BotFather
bot = telebot.TeleBot('токен')

# Ссылка на веб-интерфейс (страница на GitHub Pages)
WEB_APP_URL = 'https://ВАШ_ЛОГИН.github.io/ИМЯ_РЕПОЗИТОРИЯ/'

# Подключение к БД (файл dishes.db должен лежать в одной папке со скриптом)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dishes.db')
if not os.path.exists(DB_PATH):
    raise SystemExit('Не найден файл базы данных: ' + DB_PATH)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()
# Таблица истории просмотров: кто и какое блюдо (id из таблицы dishes) смотрел
cur.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, dish_id INTEGER NOT NULL)')
conn.commit()

HEADERS = {'User-Agent': 'HotDishesBot/1.0 (student project)'}


def get_photo(query):
    # Ищем статью про блюдо в Википедии и берём её главную картинку
    answer = requests.get('https://ru.wikipedia.org/w/api.php', headers=HEADERS, timeout=10, params={
        'action': 'query', 'format': 'json', 'generator': 'search', 'gsrsearch': query,
        'gsrlimit': 5, 'prop': 'pageimages', 'piprop': 'thumbnail', 'pithumbsize': 800})
    pages = answer.json()['query']['pages']
    # Идём по найденным статьям по порядку и берём первую, где есть картинка
    for page in sorted(pages.values(), key=lambda page: page['index']):
        if 'thumbnail' in page:
            # Скачиваем картинку по ссылке прямо из интернета
            return requests.get(page['thumbnail']['source'], headers=HEADERS, timeout=10).content


def send_dish(chat_id, user_id, dish_id):
    # Достаём все данные о блюде из БД
    name, description, ingredients, cook_time, recipe, photo_query = cur.execute(
        'SELECT name, description, ingredients, cook_time, recipe, photo_query FROM dishes WHERE id = ?',
        (dish_id,)).fetchone()
    # Записываем просмотр в историю
    cur.execute('INSERT INTO history (user_id, dish_id) VALUES (?, ?)', (user_id, dish_id))
    conn.commit()

    # Берём фото блюда из интернета и отправляем в чат
    try:
        photo = get_photo(photo_query)
        if photo:
            bot.send_photo(chat_id, photo)
    except Exception:
        pass  # если фото не нашлось — просто покажем текст

    # Оформляем текст: жирный заголовок, подписи и эмодзи
    msg = ('🍲 <b>' + name.upper() + '</b>\n\n<i>' + description + '</i>\n\n'
           '🛒 <b>Ингредиенты:</b> ' + ingredients + '\n'
           '⏱ <b>Время:</b> ' + cook_time + '\n\n'
           '👨‍🍳 <b>Приготовление:</b> ' + recipe)
    bot.send_message(chat_id, msg, parse_mode='HTML')


# Обработчик команды /start: приветствие и сразу меню с категориями из БД
@bot.message_handler(commands=['start'])
def send_start(message):
    # Клавиатура с кнопкой, которая открывает веб-интерфейс
    web_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    web_keyboard.add(types.KeyboardButton(text='🍽 Меню блюд', web_app=types.WebAppInfo(url=WEB_APP_URL)))
    bot.send_message(message.from_user.id,
                     "👋 <b>Привет!</b>\nСейчас я расскажу тебе про <b>горячие блюда</b> 🍲",
                     parse_mode='HTML', reply_markup=web_keyboard)

    # Категории берём из таблицы dishes
    keyboard = types.InlineKeyboardMarkup()
    for row in cur.execute('SELECT DISTINCT category FROM dishes').fetchall():
        keyboard.add(types.InlineKeyboardButton(text='📂 ' + row[0], callback_data='cat:' + row[0]))
    keyboard.add(types.InlineKeyboardButton(text='🎲 Случайное блюдо', callback_data='random'))
    bot.send_message(message.from_user.id, text='👇 <b>Выбери категорию:</b>', reply_markup=keyboard, parse_mode='HTML')


# Обработчик команды /help
@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(message.from_user.id,
                     "ℹ️ Команды:\n/start — меню блюд\n/find курица — поиск блюда по ингредиенту\n"
                     "/top — самые популярные блюда\n/my — мои последние блюда")


# Команда /find: поиск блюд по ингредиенту (запрос к БД с LIKE)
@bot.message_handler(commands=['find'])
def send_find(message):
    word = message.text[5:].strip().lower()
    if not word:
        bot.send_message(message.from_user.id, "Напиши, что ищем, например: /find курица")
        return
    rows = cur.execute('SELECT name FROM dishes WHERE ingredients LIKE ?', ('%' + word + '%',)).fetchall()
    if not rows:
        bot.send_message(message.from_user.id, "😕 Блюд с таким ингредиентом не нашлось.")
        return
    bot.send_message(message.from_user.id, '🔎 <b>Найдено:</b>\n' + '\n'.join('• ' + row[0] for row in rows),
                     parse_mode='HTML')


# Команда /top: самые популярные блюда (JOIN двух таблиц и группировка)
@bot.message_handler(commands=['top'])
def send_top(message):
    rows = cur.execute('SELECT dishes.name, COUNT(*) FROM history JOIN dishes ON dishes.id = history.dish_id '
                       'GROUP BY dishes.id ORDER BY COUNT(*) DESC LIMIT 3').fetchall()
    if not rows:
        bot.send_message(message.from_user.id, "Пока никто не выбирал блюда. Напиши /start")
        return
    text = '🏆 <b>Самые популярные блюда:</b>\n'
    for i, row in enumerate(rows, 1):
        text += str(i) + '. ' + row[0] + ' — ' + str(row[1]) + ' раз(а)\n'
    bot.send_message(message.from_user.id, text, parse_mode='HTML')


# Команда /my: последние блюда, которые смотрел этот пользователь
@bot.message_handler(commands=['my'])
def send_my(message):
    rows = cur.execute('SELECT dishes.name FROM history JOIN dishes ON dishes.id = history.dish_id '
                       'WHERE history.user_id = ? ORDER BY history.id DESC LIMIT 5', (message.from_user.id,)).fetchall()
    if not rows:
        bot.send_message(message.from_user.id, "Ты ещё не выбирал блюда. Напиши /start")
        return
    bot.send_message(message.from_user.id, '🕘 <b>Ты недавно смотрел:</b>\n' + '\n'.join('• ' + row[0] for row in rows),
                     parse_mode='HTML')


# Данные из веб-интерфейса: приходит id блюда, которое выбрал пользователь
@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    send_dish(message.chat.id, message.from_user.id, int(message.web_app_data.data))


# Обработчик остальных текстовых сообщений
@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    bot.send_message(message.from_user.id, "🤔 Я тебя не понимаю. Напиши /help.")


# Обработчик нажатий на кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    if call.data.startswith('cat:'):
        # Нажали на категорию — показываем блюда этой категории из БД
        category = call.data[4:]
        keyboard = types.InlineKeyboardMarkup()
        for dish_id, name in cur.execute('SELECT id, name FROM dishes WHERE category = ?', (category,)).fetchall():
            keyboard.add(types.InlineKeyboardButton(text='🍽 ' + name, callback_data='dish:' + str(dish_id)))
        bot.send_message(chat_id, '👇 <b>' + category + ':</b>', reply_markup=keyboard, parse_mode='HTML')
    elif call.data == 'random':
        # Случайное блюдо: выбираем случайную строку прямо в БД
        dish_id = cur.execute('SELECT id FROM dishes ORDER BY RANDOM() LIMIT 1').fetchone()[0]
        send_dish(chat_id, call.from_user.id, dish_id)
    else:
        # Нажали на блюдо — показываем карточку
        send_dish(chat_id, call.from_user.id, int(call.data[5:]))


# Запускаем постоянный опрос бота в Телеграме
bot.polling(none_stop=True, interval=0)
