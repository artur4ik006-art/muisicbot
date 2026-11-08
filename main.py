import os
import re
import telebot
import requests
from telebot import types
from yt_dlp import YoutubeDL
from threading import Thread
from flask import Flask
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, error

app = Flask('')

@app.route('/')
def home():
    return "Мультизадачний музичний комбайн активовано!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = '9019116927:AAGKjHLRDNEp-BpmZaUqfF1pIBTiBsL3YyI'
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

user_requests = {}

# ФУНКЦІЯ 1: Автоматичне вшивання обкладинки та метаданих в MP3
def inject_metadata(file_path, title, artist):
    try:
        # Шукаємо офіційну обкладинку альбому через публічний сервіс iTunes API
        search_url = f"https://apple.com{artist} {title}&media=music&limit=1"
        res = requests.get(search_url, timeout=5).json()
        
        img_data = None
        if res.get('results') and res['results']:
            img_url = res['results'][0]['artworkUrl100'].replace('100x100bb', '600x600bb')
            img_data = requests.get(img_url, timeout=5).content

        audio = MP3(file_path, ID3=ID3)
        try:
            audio.add_tags()
        except error:
            pass

        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TPE1(encoding=3, text=artist))

        if img_data:
            audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=img_data))
        audio.save()
    except Exception as e:
        print(f"Помилка обробки метаданих: {e}")

# ФУНКЦІЯ 2: Мульти-пошуковий каскадний двигун
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
    
    # Використовуємо SoundCloud
    if source_type == "sc":
        target = f"scsearch1:{query}"
    # Використовуємо пряме API-дзеркало в обхід блокувань Google
    elif source_type == "api_fast":
        try:
            api_url = f"https://jamendo.com{query}"
            res = requests.get(api_url, timeout=5).json()
            if res.get('results') and res['results']:
                target = res['results'][0]['audio']
        except Exception:
            target = f"scsearch1:{query} audio"
    # Резервний TV-клієнт
    else:
        target = f"ytsearch1:{query} lyrics"
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['tvembedded'], 'player_skip': ['webpage', 'configs']}}

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(target, download=True)
        if 'entries' in info and info['entries']:
            info = info['entries'][0]
        filename = ydl.prepare_filename(info)
        file_path = os.path.splitext(filename)[0] + '.mp3'
        
        # Намагаємося красиво розбити запит на Автора та Назву для метаданих
        parts = query.split('-', 1)
        artist = parts[0].strip() if len(parts) > 1 else "Unknown Artist"
        title = parts[1].strip() if len(parts) > 1 else query.strip()
        
        inject_metadata(file_path, title, artist)
        return file_path

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Привіт! Я твій супер-гнучкий музичний асистент.\n\nНадішли мені назву пісні або лінк із Shazam. Я знайду трек, його текст та красиво оформлю файл!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        clean_url = urls[0] # Виправлено: беремо СТРОГО рядок тексту
        # Розумний аналіз посилання Shazam
        if "shazam.com" in clean_url:
            try:
                clean_url_parts = clean_url.split('?')
                match = re.search(r'/track/\d+/([^/]+)', clean_url_parts[0])
                if match:
                    keywords = match.group(1).replace('-', ' ')
                else:
                    keywords = "Music Track"
            except Exception:
                keywords = "Music Track"
        else:
            keywords = clean_url
    else:
        keywords = text

    user_requests[message.chat.id] = keywords

    # Багатозадачне інтерактивне меню
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_sc = types.InlineKeyboardButton("🎵 SoundCloud (Вільний)", callback_data="get_sc")
    btn_api = types.InlineKeyboardButton("⚡ Пряме Дзеркало (Обхід)", callback_data="get_api")
    btn_tv = types.InlineKeyboardButton("📺 Режим Smart TV", callback_data="get_tv")
    btn_lyrics = types.InlineKeyboardButton("📝 Текст пісні (Lyrics)", callback_data="get_lyrics")
    
    markup.add(btn_sc, btn_api)
    markup.add(btn_tv, btn_lyrics)

    bot.send_message(message.chat.id, f"📋 *Музичний запит:* {keywords}\n\nОбери джерело для скачування файлу або додаткову функцію:", 
                     parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    query = user_requests.get(chat_id)

    if not query:
        bot.answer_callback_query(call.id, "❌ Запит застарів. Надішли назву знову.")
        return

    # ФУНКЦІЯ 3: Повноцінний миттєвий пошук тексту пісні (Lyrics API)
    if call.data == "get_lyrics":
        bot.answer_callback_query(call.id, "🔍 Шукаю текст пісні...")
        status = bot.send_message(chat_id, "⏳ Опитую відкриті бази текстів...")
        try:
            lyrics_url = f"https://lyrics.ovh{query}"
            if '-' in query:
                parts = query.split('-', 1)
                lyrics_url = f"https://lyrics.ovh{parts[0].strip()}/{parts[1].strip()}"
            
            res = requests.get(lyrics_url, timeout=5).json()
            lyrics_text = res.get('lyrics')
            
            if lyrics_text:
                bot.delete_message(chat_id, status.message_id)
                # Розбиваємо великий текст, щоб не перевищити ліміти Telegram
                for chunk in [lyrics_text[i:i+4000] for i in range(0, len(lyrics_text), 4000)]:
                    bot.send_message(chat_id, f"📝 *Текст пісні {query}:*\n\n{chunk}", parse_mode="Markdown")
            else:
                bot.edit_message_text(f"❌ Текст для '{query}' не знайдено у публічних базах.", chat_id, status.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Не вдалося отримати текст: {str(e)}", chat_id, status.message_id)
        return

    # Карта вибору джерел завантаження
    source_map = {"get_sc": "sc", "get_api": "api_fast", "get_tv": "yt_tv"}
    source_type = source_map.get(call.data)

    bot.answer_callback_query(call.id, "📥 Починаю скачування...")
    status_message = bot.send_message(chat_id, "⚡ Завантажую аудіопотік та інтегрую обкладинку альбому...")

    try:
        file_path = download_track(query, source_type)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as audio:
                bot.send_audio(chat_id, audio)
            bot.delete_message(chat_id, status_message.message_id)
            os.remove(file_path)
        else:
            raise Exception("Помилка обробки файлу.")
    except Exception as e:
        bot.edit_message_text(f"❌ Цей режим заблоковано: {str(e)}\nСпробуй натиснути іншу кнопку з меню вище!", chat_id, status_message.message_id)

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Супер-бот успішно активовано...")
    bot.infinity_polling()
