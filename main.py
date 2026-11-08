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
    
    # ⚡ Сценарій 1: Пряме завантаження через перевірене SoundCloud-дзеркало
    if source_type == "sc_direct":
        # Робимо прямий запит без вбудованого пошуку yt-dlp, який застарів на сервері
        try:
            search_api = f"https://soundcloud.com{query}&client_id=IL0b7W7S2667ZAnWAsU00w5w402u707w&limit=1"
            res = requests.get(search_api, timeout=5).json()
            if res.get('collection') and res['collection']:
                target = res['collection'][0]['permalink_url']
            else:
                target = f"scsearch1:{query}"
        except Exception:
            target = f"scsearch1:{query}"

    # 📺 Сценарій 2: TV-Bypass імітація Smart TV для YouTube
    elif source_type == "yt_tv":
        target = f"ytsearch1:{query} lyrics"
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['tvembedded'], 'player_skip': ['webpage', 'configs']}}
    
    # 📱 Сценарій 3: YouTube Music мобільний клієнт
    else:
        target = f"ytsearch1:{query} audio"
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android_music'], 'player_skip': ['webpage', 'configs']}}

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(target, download=True)
        if 'entries' in info and info['entries']:
            info = info['entries'][0]
        filename = ydl.prepare_filename(info)
        file_path = os.path.splitext(filename)[0] + '.mp3'
        
        # Парсимо назву для вшивання обкладинки
        parts = query.split('-', 1)
        artist = parts[0].strip() if len(parts) > 1 else "Unknown Artist"
        title = parts[1].strip() if len(parts) > 1 else query.strip()
        
        inject_metadata(file_path, title, artist)
        return file_path

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Вітаю у твоєму оновленому музичному медіа-центрі!\n\nНадішли назву пісні або лінк із Shazam — я знайду трек через стабільний SoundCloud, завантажу офіційну обкладинку альбому або знайду текст пісні!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        clean_url = urls[0] # Виправлено: беремо СТРОГО перший елемент як чистий рядок
        if "shazam.com" in clean_url:
            try:
                clean_url_parts = clean_url.split('?')[0]
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
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_sc = types.InlineKeyboardButton("🎵 SoundCloud (Основний стабільний режим)", callback_data="get_sc")
    btn_tv = types.InlineKeyboardButton("📺 Режим Smart TV (Резервний обхід)", callback_data="get_tv")
    btn_lyrics = types.InlineKeyboardButton("📝 Текст пісні (Lyrics)", callback_data="get_lyrics")
    
    markup.add(btn_sc, btn_tv, btn_lyrics)

    bot.send_message(message.chat.id, f"📋 *Музичний запит:* {keywords}\n\nОбери бажану дію:", 
                     parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    query = user_requests.get(chat_id)

    if not query:
        bot.answer_callback_query(call.id, "❌ Запит застарів. Надішли назву треку знову.")
        return

    # 📝 ФУНКЦІЯ: Миттєвий пошук тексту пісні (Повністю виправлено помилку Host та додано правильний слеш)
    if call.data == "get_lyrics":
        bot.answer_callback_query(call.id, "🔍 Пошук тексту...")
        status = bot.send_message(chat_id, "⏳ Опитую відкриті бази текстів пісень...")
        try:
            if '-' in query:
                parts = query.split('-', 1)
                artist_part = parts[0].strip().replace(' ', '%20')
                title_part = parts[1].strip().replace(' ', '%20')
                lyrics_url = f"https://lyrics.ovh{artist_part}/{title_part}"
            else:
                title_part = query.strip().replace(' ', '%20')
                lyrics_url = f"https://lyrics.ovhUnknown%20Artist/{title_part}"
            
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

    source_map = {"get_sc": "sc_direct", "get_tv": "yt_tv"}
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
