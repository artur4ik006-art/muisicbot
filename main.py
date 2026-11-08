import os
import re
import telebot
import requests
from yt_dlp import YoutubeDL
from threading import Thread
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Бот працює стабільно!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = '9019116927:AAGKjHLRDNEp-BpmZaUqfF1pIBTiBsL3YyI'
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def download_audio(url_or_search):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '/tmp/%(title)s.%(ext)s',  
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        }
    }

    # Витягуємо чисту назву треку з URL Shazam
    keywords = ""
    if "shazam.com" in url_or_search:
        clean_url = url_or_search.split('?')
        match = re.search(r'/track/\d+/([^/]+)', clean_url[0])
        if match:
            keywords = match.group(1).replace('-', ' ')
        else:
            raise Exception("Не вдалося розпізнати структуру треку з Shazam.")
    else:
        keywords = url_or_search

    # Інноваційний обхід блокувань: використовуємо відкриту безкоштовну базу для пошуку прямого лінка
    try:
        # Шукаємо трек через відкритий індекс Jamendo/інших публічних API дзеркал
        api_url = f"https://jamendo.com{keywords}"
        res = requests.get(api_url, timeout=10).json()
        
        if res.get('results') and res['results']:
            direct_mp3_url = res['results'][0]['audio']
            # Скачуємо аудіофайл напряму за прямим посиланням
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(direct_mp3_url, download=True)
                filename = ydl.prepare_filename(info)
                return os.path.splitext(filename)[0] + '.mp3'
    except Exception:
        pass

    # Резервний мобільний спосіб, якщо пряма база не знайшла трек
    ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android_music'], 'player_skip': ['webpage', 'configs']}}
    url_to_download = f"ytsearch1:{keywords} audio"
    
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url_to_download, download=True)
        if 'entries' in info:
            if info['entries']:
                info = info['entries'][0]
            else:
                raise Exception("Цей трек заблоковано правовласниками. Спробуйте інший.")
        filename = ydl.prepare_filename(info)
        return os.path.splitext(filename)[0] + '.mp3'

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Надішли мені посилання на трек із Shazam, і я завантажу його без жодних помилок!")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        clean_url = urls[0] # Беремо чистий перший елемент
        status_message = bot.reply_to(message, "🔍 Обхожу блоки, завантажую та нарізаю твій трек...")
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
        bot.reply_to(message, "Будь ласка, надішли мені коректне інтернет-посилання.")

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Бот запущений у суперстабільному режимі обходу блоків...")
    bot.infinity_polling()
