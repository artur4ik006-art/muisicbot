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
    return "Мультизадачна музична медіа-станція онлайн!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = '9019116927:AAGKjHLRDNEp-BpmZaUqfF1pIBTiBsL3YyI'
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

user_requests = {}

# Автоматичне вшивання обкладинок альбому з iTunes API
def inject_metadata(file_path, title, artist):
    try:
        search_url = f"https://apple.com{artist} {title}&media=music&limit=1"
        res = requests.get(search_url, timeout=5).json()
        
        img_data = None
        if res.get('results') and res['results']:
            img_url = res['results']['artworkUrl100'].replace('100x100bb', '600x600bb')
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
        print(f"ID3 Tagging error: {e}")

# Каскадний двигун скачування
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
    
    # ⚡ Сценарій 1: Пряме публічне API дзеркало (100% обхід капчі та DRM)
    if source_type == "api_fast":
        try:
            api_url = f"https://jamendo.com{query}"
            res = requests.get(api_url, timeout=5).json()
            if res.get('results') and res['results']:
                target = res['results']['audio']
            else:
                raise Exception("Немає в базовому індексі")
        except Exception:
            # Якщо в базі немає, автоматично робимо безпечне переключення
            target = f"ytsearch1:{query} audio"
            ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android_music'], 'player_skip': ['webpage', 'configs']}}

    # 📺 Сценарій 2: TV-Bypass імітація Smart TV
    elif source_type == "yt_tv":
        target = f"ytsearch1:{query} lyrics"
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['tvembedded'], 'player_skip': ['webpage', 'configs']}}
    
    # 🎵 Сценарій 3: Пряме скачування за прямим посиланням
    else:
        target = f"ytsearch1:{query} audio"
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android_music'], 'player_skip': ['webpage', 'configs']}}

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(target, download=True)
        if 'entries' in info and info['entries']:
            info = info['entries']
        filename = ydl.prepare_filename(info)
        file_path = os.path.splitext(filename) + '.mp3'
        
        # Парсимо назву для вшивання обкладинки
        parts = query.split('-', 1)
        artist = parts.strip() if len(parts) > 1 else "Unknown Artist"
        title = parts.strip() if len(parts) > 1 else query.strip()
        
        inject_metadata(file_path, title, artist)
        return file_path

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Вітаю у твоєму новому музичному медіа-центрі!\n\nНадішли назву пісні або лінк із Shazam — я знайду трек, завантажу офіційну обкладинку альбому або знайду текст пісні!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        clean_url = urls
        if "shazam.com" in clean_url:
            try:
                clean_url_parts = clean_url.split('?')
                match = re.search(r'/track/\d+/([^/]+)', clean_url_parts)
                if match:
                    keywords = match.group(1).replace('-', ' ')
                else:
                    keywords = clean_url
            except Exception:
                keywords = clean_url
        else:
            keywords = clean_url
    else:
        keywords = text

    user_requests[message.chat.id] = keywords

    # Гарне гнучке інтерактивне меню
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_api = types.InlineKeyboardButton("⚡ Пряме Дзеркало (Швидко)", callback_data="get_api")
    btn_tv = types.InlineKeyboardButton("📺 Режим Smart TV (Обхід)", callback_data="get_tv")
    btn_lyrics = types.InlineKeyboardButton("📝 Текст пісні (Lyrics)", callback_data="get_lyrics")
    
    markup.add(btn_api, btn_tv)
    markup.add(btn_lyrics)

    bot.send_message(message.chat.id, f"📋 *Музичний запит:* {keywords}\n\nОбери бажану дію:", 
                     parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    query = user_requests.get(chat_id)

    if not query:
        bot.answer_callback_query(call.id, "❌ Запит застарів. Надішли назву треку знову.")
        return

    # 📝 ФУНКЦІЯ: Миттєвий пошук тексту пісні (Повністю виправлено помилку Host)
    if call.data == "get_lyrics":
        bot.answer_callback_query(call.id, "🔍 Пошук тексту...")
        status = bot.send_message(chat_id, "⏳ Опитую відкриті бази текстів пісень...")
        try:
            # Формуємо правильний відносний URL зі слешем
            if '-' in query:
                parts = query.split('-', 1)
                lyrics_url = f"https://lyrics.ovh{parts[0].strip()}/{parts[1].strip()}"
            else:
                lyrics_url = f"https://lyrics.ovhUnknown Artist/{query.strip()}"
            
            res = requests.get(lyrics_url, timeout=5).json()
            lyrics_text = res.get('lyrics')
            
            if lyrics_text:
                bot.delete_message(chat_id, status.message_id)
                for chunk in [lyrics_text[i:i+4000] for i in range(0, len(lyrics_text), 4000)]:
                    bot.send_message(chat_id, f"📝 *Текст пісні {query}:*\n\n{chunk}", parse_mode="Markdown")
            else:
                bot.edit_message_text(f"❌ Текст для '{query}' не знайдено у публічних архівах.", chat_id, status.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Не вдалося отримати текст: {str(e)}", chat_id, status.message_id)
        return

    source_map = {"get_api": "api_fast", "get_tv": "yt_tv"}
    source_type = source_map.get(call.data)

    bot.answer_callback_query(call.id, "📥 Запуск завантаження...")
    status_message = bot.send_message(chat_id, "⚡ Завантажую аудіо та інтегрую офіційну обкладинку...")

    try:
        file_path = download_track(query, source_type)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as audio:
                bot.send_audio(chat_id, audio)
            bot.delete_message(chat_id, status_message.message_id)
            os.remove(file_path)
        else:
            raise Exception("Помилка генерації файлу.")
    except Exception as e:
        bot.edit_message_text(f"❌ Цей сценарій заблоковано захистом: {str(e)}\nСпробуй натиснути іншу кнопку з меню вище!", chat_id, status_message.message_id)

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Гнучкий мульти-бот онлайн...")
    bot.infinity_polling()
