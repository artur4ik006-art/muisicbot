import os
import re
import telebot
from yt_dlp import YoutubeDL
from threading import Thread
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Бот працює надійно!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = '9019116927:AAGKjHLRDNEp-BpmZaUqfF1pIBTiBsL3YyI'
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def download_audio(url_string):
    # Налаштування 1: Спроба через SoundCloud (швидко і без капчі)
    ydl_opts_sc = {
        'format': 'bestaudio/best',
        'outtmpl': '/tmp/%(title)s.%(ext)s',  
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'ignoreerrors': False
    }

    # Налаштування 2: Резервна спроба через YouTube (мобільний клієнт iOS обходить капчу)
    ydl_opts_yt = {
        'format': 'bestaudio/best',
        'outtmpl': '/tmp/%(title)s.%(ext)s',  
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios'],
                'player_skip': ['webpage', 'configs']
            }
        }
    }
    
    # Вирізаємо чисті слова з посилання Shazam
    clean_url = url_string.split('?')
    match = re.search(r'/track/\d+/([^/]+)', clean_url[0])
    if match:
        keywords = match.group(1).replace('-', ' ')
    else:
        keywords = url_string

    # КРОК 1: Пробуємо знайти на SoundCloud
    try:
        search_query = f"scsearch1:{keywords}"
        with YoutubeDL(ydl_opts_sc) as ydl:
            info = ydl.extract_info(search_query, download=True)
            if 'entries' in info and info['entries']:
                entry = info['entries'][0]
                filename = ydl.prepare_filename(entry)
                return os.path.splitext(filename)[0] + '.mp3'
    except Exception as e:
        # Якщо SoundCloud видав DRM або ліцензійну помилку — переходимо до КРОКУ 2
        print(f"SoundCloud DRM/Error: {e}. Переключаюсь на YouTube...")
        
    # КРОК 2: Резервний пошук на YouTube через iOS-клієнт
    search_query = f"ytsearch1:{keywords} audio"
    with YoutubeDL(ydl_opts_yt) as ydl:
        info = ydl.extract_info(search_query, download=True)
        if 'entries' in info and info['entries']:
            entry = info['entries'][0]
            filename = ydl.prepare_filename(entry)
            return os.path.splitext(filename)[0] + '.mp3'
        else:
            raise Exception("Не вдалося знайти трек в жодному безкоштовному джерелі.")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Скинь мені посилання на Shazam, і я завантажу його для тебе як MP3!")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        # КРИТИЧНЕ ВИПРАВЛЕННЯ: Беремо перший елемент списку як чистий ТЕКСТОВИЙ РЯДОК [0]
        clean_url = urls[0] 
        status_message = bot.reply_to(message, "🔍 Обходжу блоки, шукаю твій трек...")
        try:
            file_path = download_audio(clean_url)
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as audio:
                    bot.send_audio(message.chat.id, audio)
                bot.delete_message(message.chat.id, status_message.message_id)
                os.remove(file_path)
            else:
                raise Exception("Помилка фіналізації MP3 на сервері.")
                
        except Exception as e:
            bot.edit_message_text(f"❌ Помилка завантаження: {str(e)}", message.chat.id, status_message.message_id)
    else:
        bot.reply_to(message, "Будь ласка, надішли мені повідомлення з коректним інтернет-посилання.")

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Бот успішно запущений у дворежимному обході...")
    bot.infinity_polling()
