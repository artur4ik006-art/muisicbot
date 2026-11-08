import os
import re
import telebot
from telebot import types
from yt_dlp import YoutubeDL
from threading import Thread
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Мультизадачний медіа-бот онлайн!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = '9019116927:AAGKjHLRDNEp-BpmZaUqfF1pIBTiBsL3YyI'
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Тимчасове збереження пошукових запитів користувачів
user_requests = {}

def download_track(query, source_type):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '/tmp/%(title)s.%(ext)s',  
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True
    }
    
    if source_type == "sc":
        target = f"scsearch1:{query}"
    elif source_type == "yt_tv":
        target = f"ytsearch1:{query} lyrics"
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['tvembedded'], 'player_skip': ['webpage', 'configs']}}
    else:
        target = f"ytsearch1:{query} audio"
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android_music'], 'player_skip': ['webpage', 'configs']}}

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(target, download=True)
        if 'entries' in info and info['entries']:
            info = info['entries'][0]
        filename = ydl.prepare_filename(info)
        return os.path.splitext(filename)[0] + '.mp3'

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Привіт! Я твій гнучкий музичний асистент.\n\nНадішли мені назву пісні або посилання на Shazam, і ти зможеш сам обрати параметри завантаження!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    # Визначаємо ключові слова для пошуку
    if urls:
        clean_url = urls[0]  # Виправлено: беремо перший рядок зі списку
        if "shazam.com" in clean_url:
            clean_url_parts = clean_url.split('?')
            match = re.search(r'/track/\d+/([^/]+)', clean_url_parts[0])
            if match:
                keywords = match.group(1).replace('-', ' ')
            else:
                keywords = clean_url
        else:
            keywords = clean_url
    else:
        keywords = text

    # Зберігаємо запит користувача
    user_requests[message.chat.id] = keywords

    # Створюємо інтерактивне меню з інлайн-кнопками
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_sc = types.InlineKeyboardButton("🎵 Завантажити з SoundCloud (Без капчі)", callback_data="get_sc")
    btn_ytm = types.InlineKeyboardButton("📱 Завантажити з YouTube Music (Мобільний)", callback_data="get_ytm")
    btn_tv = types.InlineKeyboardButton("📺 Завантажити через TV-Bypass (Супер-обхід)", callback_data="get_tv")
    btn_lyrics = types.InlineKeyboardButton("📝 Знайти текст пісні (Скоро)", callback_data="get_lyrics")
    
    markup.add(btn_sc, btn_ytm, btn_tv, btn_lyrics)

    bot.send_message(message.chat.id, f"🔍 Я розпізнав трек: *{keywords}*\nОбери дію або джерело завантаження:", 
                     parse_mode="Markdown", reply_markup=markup)

# Обробник натискання кнопок (Виправлено декоратор)
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    query = user_requests.get(chat_id)

    if not query:
        bot.answer_callback_query(call.id, "❌ Запит застарів. Надішли посилання або назву знову.")
        return

    if call.data == "get_lyrics":
        bot.answer_callback_query(call.id, "Функція розробляється!")
        bot.send_message(chat_id, f"📖 Модуль Lyrics для *{query}* наразі підключається.")
        return

    # Мапа вибору джерел
    source_map = {"get_sc": "sc", "get_ytm": "yt_music", "get_tv": "yt_tv"}
    source_type = source_map.get(call.data)

    bot.answer_callback_query(call.id, "⏳ Починаю обробку запиту...")
    status_message = bot.send_message(chat_id, "📥 Завантажую аудіопотік за обраним сценарієм...")

    try:
        file_path = download_track(query, source_type)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as audio:
                bot.send_audio(chat_id, audio)
            bot.delete_message(chat_id, status_message.message_id)
            os.remove(file_path)
        else:
            raise Exception("Файл не збережено.")
    except Exception as e:
        bot.edit_message_text(f"❌ Помилка цього сценарію: {str(e)}\nСпробуй іншу кнопку вище!", chat_id, status_message.message_id)

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Мультизадачний бот активовано...")
    bot.infinity_polling()
