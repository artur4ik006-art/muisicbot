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
    return "Музичний медіа-центр працює надійно!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = '9019116927:AAGKjHLRDNEp-BpmZaUqfF1pIBTiBsL3YyI'
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

user_requests = {}

# Вшивання обкладинок альбому з iTunes API
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

# Надійне скачування через SoundCloud дзеркало
def download_track(query):
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
    
    try:
        search_api = f"https://soundcloud.com{query}&client_id=IL0b7W7S2667ZAnWAsU00w5w402u707w&limit=1"
        res = requests.get(search_api, timeout=5).json()
        if res.get('collection') and res['collection']:
            target = res['collection'][0]['permalink_url']
        else:
            target = f"scsearch1:{query}"
    except Exception:
        target = f"scsearch1:{query}"

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(target, download=True)
        if 'entries' in info and info['entries']:
            info = info['entries'][0]
        filename = ydl.prepare_filename(info)
        file_path = os.path.splitext(filename)[0] + '.mp3'
        
        # Красиве розділення тексту на автора та пісню
        if '-' in query:
            parts = query.split('-', 1)
            artist = parts[0].strip()
            title = parts[1].strip()
        else:
            artist = "SoundCloud"
            title = query.strip()
        
        inject_metadata(file_path, title, artist)
        return file_path

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Вітаю! Я твій надійний музичний асистент.\n\nНадішли мені назву пісні або лінк із Shazam — я миттєво завантажу трек або знайду текст пісні!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        clean_url = urls[0] # Виправлено: беремо строго текстовий рядок з масиву
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

    # Компактне та повністю робоче меню
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_sc = types.InlineKeyboardButton("🎵 Завантажити музику (SoundCloud)", callback_data="get_sc")
    btn_lyrics = types.InlineKeyboardButton("📝 Текст пісні (Lyrics)", callback_data="get_lyrics")
    markup.add(btn_sc, btn_lyrics)

    bot.send_message(message.chat.id, f"📋 *Музичний запит:* {keywords}\n\nОбери бажану дію:", 
                     parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    query = user_requests.get(chat_id)

    if not query:
        bot.answer_callback_query(call.id, "❌ Запит застарів. Надішли назву знову.")
        return

    # 📝 Повністю виправлений модуль тексту пісень (Додано слеш "/")
    if call.data == "get_lyrics":
        bot.answer_callback_query(call.id, "🔍 Пошук тексту...")
        status = bot.send_message(chat_id, "⏳ Опитую відкриті бази текстів пісень...")
        try:
            if '-' in query:
                parts = query.split('-', 1)
                artist_part = parts[0].strip().replace(' ', '%20')
                title_part = parts[1].strip().replace(' ', '%20')
                # Додано обов'язковий слеш "/" між доменом і автором
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

    bot.answer_callback_query(call.id, "📥 Скачую...")
    status_message = bot.send_message(chat_id, "⚡ Завантажую аудіо та інтегрую обкладинку...")

    try:
        file_path = download_track(query)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as audio:
                bot.send_audio(chat_id, audio)
            bot.delete_message(chat_id, status_message.message_id)
            os.remove(file_path)
        else:
            raise Exception("Помилка генерації файлу.")
    except Exception as e:
        bot.edit_message_text(f"❌ Сталася помилка: {str(e)}", chat_id, status_message.message_id)

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Бот запущено у фінальному стабільному режимі...")
    bot.infinity_polling()
