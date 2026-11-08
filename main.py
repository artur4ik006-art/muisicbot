import os
import re
import telebot
from yt_dlp import YoutubeDL
from threading import Thread
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Бот працює!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = '9019116927:AAGKjHLRDNEp-BpmZaUqfF1pIBTiBsL3YyI'
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def download_audio(url_or_search):
    # Базові налаштування для обходу блокувань (маскування під звичайний браузер)
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    }
    
    # Якщо це посилання на Shazam, зчитуємо сторінку та шукаємо трек на YouTube
    if "shazam.com" in url_or_search:
        # Спочатку зчитуємо метадані сторінки Shazam за допомогою yt_dlp
        shazam_opts = {
            'quiet': True,
            'skip_download': True,
            'http_headers': ydl_opts['http_headers']
        }
        with YoutubeDL(shazam_opts) as ydl:
            try:
                info = ydl.extract_info(url_or_search, download=False)
                # Перевіряємо, чи yt-dlp зміг витягнути назву/виконавця
                title = info.get('title')
                artist = info.get('artist') or info.get('creator')
                if title and artist:
                    search_query = f"ytsearch:{artist} - {title}"
                elif title:
                    search_query = f"ytsearch:{title}"
                else:
                    search_query = url_or_search
            except Exception:
                # Якщо сторінку заблоковано, спробуємо знайти за назвою з URL
                clean_url = url_or_search.split('?')[0]
                match = re.search(r'/track/\d+/([^/]+)', clean_url)
                if match:
                    search_query = f"ytsearch:{match.group(1).replace('-', ' ')}"
                else:
                    search_query = url_or_search
        
        # Використовуємо знайдений пошуковий запит
        url_to_download = search_query
    else:
        # Для YouTube та звичайних посилань використовуємо оригінальний лінк
        url_to_download = url_or_search

    # Завантаження треку
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url_to_download, download=True)
        # Якщо використовувався пошук ytsearch, структура даних буде у вигляді списку entries
        if 'entries' in info:
            info = info['entries'][0]
        filename = ydl.prepare_filename(info)
        return os.path.splitext(filename) + '.mp3'

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Надішли мені посилання на трек (YouTube, Spotify, Shazam тощо), і я спробую завантажити його для тебе як MP3!")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    text = message.text
    
    # Витягуємо чисте посилання, якщо користувач скинув його разом із текстом
    urls = re.findall(r'(https?://\S+)', text)
    if urls:
        url = urls[0]
        status_message = bot.reply_to(message, "🔍 Шукаю та завантажую трек, зачекай трішки...")
        try:
            file_path = download_audio(url)
            with open(file_path, 'rb') as audio:
                bot.send_audio(message.chat.id, audio)
            bot.delete_message(message.chat.id, status_message.message_id)
            os.remove(file_path)
        except Exception as e:
            bot.edit_message_text(f"❌ Помилка завантаження: {str(e)}", message.chat.id, status_message.message_id)
    else:
        bot.reply_to(message, "Будь ласка, надішли мені повідомлення, яке містить інтернет-посилання.")

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Бот успішно запущений з обходом 403 помилки...")
    bot.infinity_polling()
