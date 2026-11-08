import os
import re
import telebot
from yt_dlp import YoutubeDL
from threading import Thread
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Мульти-пошукова система активована!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = '9019116927:AAGKjHLRDNEp-BpmZaUqfF1pIBTiBsL3YyI'
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def download_audio(keywords):
    # Опція 1: Пошук на SoundCloud (Обходить капчі YouTube)
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

    # Опція 2: Резерв через YouTube Music (Клієнт веб-плеєра)
    ydl_opts_yt_music = {
        'format': 'bestaudio/best',
        'outtmpl': '/tmp/%(title)s.%(ext)s',  
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'extractor_args': {'youtube': {'player_client': ['webpage']}}
    }

    # Опція 3: Потужний супер-обхід (Імітація Smart TV додатка YouTube)
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

    #--- РОТАЦІЙНИЙ МУЛЬТИ-ПОШУК ---
    
    # Спроба 1: SoundCloud
    try:
        print(f"Спроба 1: Шукаю '{keywords}' на SoundCloud...")
        with YoutubeDL(ydl_opts_sc) as ydl:
            info = ydl.extract_info(f"scsearch1:{keywords}", download=True)
            if 'entries' in info and info['entries']:
                filename = ydl.prepare_filename(info['entries'][0])
                return os.path.splitext(filename) + '.mp3'
    except Exception as e:
        print(f"SoundCloud не знайшов або DRM блок: {e}")

    # Спроба 2: YouTube Music
    try:
        print(f"Спроба 2: Переключаюсь на YouTube Music для '{keywords}'...")
        with YoutubeDL(ydl_opts_yt_music) as ydl:
            info = ydl.extract_info(f"ytsearch1:{keywords} audio", download=True)
            if 'entries' in info and info['entries']:
                filename = ydl.prepare_filename(info['entries'][0])
                return os.path.splitext(filename) + '.mp3'
    except Exception as e:
        print(f"YouTube Music видав помилку: {e}")

    # Спроба 3: Надійний обхід через Smart TV Інфраструктуру
    print(f"Спроба 3: Запуск супер-обходу TV-Embedded для '{keywords}'...")
    with YoutubeDL(ydl_opts_tv) as ydl:
        info = ydl.extract_info(f"ytsearch1:{keywords} lyrics", download=True)
        if 'entries' in info and info['entries']:
            filename = ydl.prepare_filename(info['entries'][0])
            return os.path.splitext(filename) + '.mp3'
        else:
            raise Exception("Жодна пошукова система (SoundCloud/YouTube/TV) не змогла отримати цей трек.")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Надішли мені посилання на трек із Shazam, і моя розумна мульти-система знайде його!")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        # КРИТИЧНЕ ВИПРАВЛЕННЯ: urls[0] бере суто рядок тексту без квадратних дужок масиву
        raw_url = urls[0] 
        status_message = bot.reply_to(message, "🔍 Працює мульти-пошук. Перевіряю бази даних...")
        
        try:
            # Вирізаємо чистий текст треку з лінка Shazam
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
                raise Exception("Помилка фіналізації медіафайлу.")
                
        except Exception as e:
            bot.edit_message_text(f"❌ Помилка: {str(e)}", message.chat.id, status_message.message_id)
    else:
        bot.reply_to(message, "Будь ласка, надішли мені повідомлення, яке містить інтернет-посилання.")

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Розумний мульти-бот успішно запущений...")
    bot.infinity_polling()
