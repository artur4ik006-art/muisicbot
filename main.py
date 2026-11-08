import os
import re
import telebot
from yt_dlp import YoutubeDL
from threading import Thread
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Мульти-пошукова музична система активна!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = '9019116927:AAGKjHLRDNEp-BpmZaUqfF1pIBTiBsL3YyI'
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def download_audio(keywords):
    # Джерело 1: Вільно завантажуваний SoundCloud
    ydl_opts_sc = {
        'format': 'bestaudio/best',
        'outtmpl': '/tmp/%(title)s.%(ext)s',  
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True
    }

    # Джерело 2: Мобільний API YouTube Music (імітація офіційного додатка)
    ydl_opts_yt_music = {
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
                'player_client': ['android_music'],
                'player_skip': ['webpage', 'configs']
            }
        }
    }

    # Джерело 3: Smart TV Інфраструктура (YouTube для телевізорів ніколи не просить капчу)
    ydl_opts_tv = {
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
                'player_client': ['tvembedded'],
                'player_skip': ['webpage', 'configs']
            }
        }
    }

    # Почерговий каскадний пошук
    # 1. Пробуємо завантажити вільну копію з SoundCloud
    try:
        print(f"Спроба 1: Пошук '{keywords}' на SoundCloud...")
        with YoutubeDL(ydl_opts_sc) as ydl:
            info = ydl.extract_info(f"scsearch1:{keywords}", download=True)
            if 'entries' in info and info['entries']:
                filename = ydl.prepare_filename(info['entries'][0])
                return os.path.splitext(filename)[0] + '.mp3'
    except Exception as e:
        print(f"SoundCloud недоступний або DRM: {e}")

    # 2. Переключаємось на YouTube Music через мобільний додаток
    try:
        print(f"Спроба 2: Пошук '{keywords}' через YouTube Music API...")
        with YoutubeDL(ydl_opts_yt_music) as ydl:
            info = ydl.extract_info(f"ytsearch1:{keywords} audio", download=True)
            if 'entries' in info and info['entries']:
                filename = ydl.prepare_filename(info['entries'][0])
                return os.path.splitext(filename)[0] + '.mp3'
    except Exception as e:
        print(f"YouTube Music заблоковано: {e}")

    # 3. Фінальний пробій блокувань через Smart TV клієнт
    print(f"Спроба 3: Запуск фінального Smart TV обходу для '{keywords}'...")
    with YoutubeDL(ydl_opts_tv) as ydl:
        info = ydl.extract_info(f"ytsearch1:{keywords} lyrics", download=True)
        if 'entries' in info and info['entries']:
            filename = ydl.prepare_filename(info['entries'][0])
            return os.path.splitext(filename)[0] + '.mp3'
        else:
            raise Exception("Жодна музична база не змогла надати цей трек.")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Надішли мені лінк на Shazam, і мій інтелектуальний мульти-пошук знайде цей трек!")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        # СУВОРЕ ВИПРАВЛЕННЯ: Беремо перший елемент списку як ТЕКСТОВИЙ РЯДОК (String)
        raw_url = urls[0] 
        status_message = bot.reply_to(message, "🔍 Працює мультиплатформенна ротація. Шукаю трек...")
        
        try:
            # Витягуємо чисту назву треку з тексту URL
            clean_url = raw_url.split('?')
            match = re.search(r'/track/\d+/([^/]+)', clean_url[0])
            if match:
                keywords = match.group(1).replace('-', ' ')
            else:
                keywords = raw_url

            file_path = download_audio(keywords)
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as audio:
                    bot.send_audio(message.chat.id, audio)
                bot.delete_message(message.chat.id, status_message.message_id)
                os.remove(file_path)
            else:
                raise Exception("Помилка фіналізації MP3 на хмарному сервері.")
                
        except Exception as e:
            bot.edit_message_text(f"❌ Помилка завантаження: {str(e)}", message.chat.id, status_message.message_id)
    else:
        bot.reply_to(message, "Будь ласка, надішли мені коректне інтернет-посилання.")

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Мульти-бот успішно активовано...")
    bot.infinity_polling()
