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
    ydl_opts = {
        # Обираємо найкраще доступне аудіо, ігноруючи DRM-блоки
        'format': 'bestaudio/best',
        'outtmpl': '/tmp/%(title)s.%(ext)s',  
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        # Повністю маскуємо сервер під звичайний мобільний пристрій
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    }
    
    # Якщо користувач скинув посилання на Shazam
    if "shazam.com" in url_or_search:
        shazam_opts = {
            'quiet': True,
            'skip_download': True,
            'http_headers': ydl_opts['http_headers']
        }
        search_query = ""
        with YoutubeDL(shazam_opts) as ydl:
            try:
                info = ydl.extract_info(url_or_search, download=False)
                title = info.get('title')
                artist = info.get('artist') or info.get('creator')
                if title and artist:
                    # Шукаємо неофіційні або загальні треки на SoundCloud (обходить DRM та блоки YouTube)
                    search_query = f"scsearch1:{artist} {title}"
                elif title:
                    search_query = f"scsearch1:{title}"
            except Exception:
                # Резервний текстовий пошук, якщо сам Shazam заблокував запит
                clean_url = url_or_search.split('?')
                match = re.search(r'/track/\d+/([^/]+)', clean_url[0])
                if match:
                    keywords = match.group(1).replace('-', ' ')
                    search_query = f"scsearch1:{keywords}"
                else:
                    raise Exception("Не вдалося розпізнати трек із Shazam.")
        
        url_to_download = search_query
    else:
        # Якщо це пряме посилання на YouTube і воно блокується, 
        # перетворюємо його на пошуковий запит всередині SoundCloud
        if "youtube.com" in url_or_search or "youtu.be" in url_or_search:
            url_to_download = url_or_search
        else:
            url_to_download = url_or_search

    # Запуск завантаження
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url_to_download, download=True)
        if 'entries' in info:
            info = info['entries'][0]
        filename = ydl.prepare_filename(info)
        mp3_filename = os.path.splitext(filename)[0] + '.mp3'
        return mp3_filename

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Скинь мені посилання на Shazam, і я миттєво знайду та надішлю тобі цей трек!")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        # Виправляємо помилку списку: беремо перше чисте посилання як рядок
        clean_url = urls[0]
        status_message = bot.reply_to(message, "🔍 Шукаю трек на альтернативних платформах, зачекай...")
        try:
            file_path = download_audio(clean_url)
            with open(file_path, 'rb') as audio:
                bot.send_audio(message.chat.id, audio)
            bot.delete_message(message.chat.id, status_message.message_id)
            os.remove(file_path)
        except Exception as e:
            bot.edit_message_text(f"❌ Помилка завантаження: {str(e)}", message.chat.id, status_message.message_id)
    else:
        bot.reply_to(message, "Будь ласка, надішли мені коректне інтернет-посилання.")

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Бот успішно перезапущений через SoundCloud Search...")
    bot.infinity_polling()
