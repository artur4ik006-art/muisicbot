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
        'format': 'bestaudio/best',
        'outtmpl': '/tmp/%(title)s.%(ext)s',  
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        # Ігноруємо дрібні помилки серверов, щоб бот не падав, якщо одне з джерел закрите
        'ignoreerrors': True,
        # Екстрактор налаштовуємо на роботу через веб-інтерфейси для обходу капчі
        'extractor_args': {
            'youtube': {
                'player_client': ['webpage', 'mweb'],
                'skip': ['webpage', 'configs']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    }
    
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
                    # Повертаємо пошук на YouTube Music, але з захистом
                    search_query = f"ytsearch1:{artist} {title} audio"
                elif title:
                    search_query = f"ytsearch1:{title} audio"
            except Exception:
                # Резервний випадок: якщо Shazam недоступний, парсимо текст прямо з посилання
                clean_url = url_or_search.split('?')
                match = re.search(r'/track/\d+/([^/]+)', clean_url[0])
                if match:
                    keywords = match.group(1).replace('-', ' ')
                    search_query = f"ytsearch1:{keywords} audio"
                else:
                    raise Exception("Не вдалося отримати назву з Shazam.")
        
        url_to_download = search_query
    else:
        url_to_download = url_or_search

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url_to_download, download=True)
        if 'entries' in info:
            if len(info['entries']) > 0 and info['entries'][0]:
                info = info['entries'][0]
            else:
                raise Exception("Нічого не знайдено за цим запитом.")
        
        filename = ydl.prepare_filename(info)
        mp3_filename = os.path.splitext(filename)[0] + '.mp3'
        return mp3_filename

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Надішли мені посилання на трек (Shazam або YouTube), і я завантажу його для тебе як MP3!")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        # УВАГА: тепер ми чітко передаємо перший елемент списку як рядок (urls[0])
        clean_url = urls[0]
        status_message = bot.reply_to(message, "🔍 Шукаю та нарізаю трек, зачекай трішки...")
        try:
            file_path = download_audio(clean_url)
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as audio:
                    bot.send_audio(message.chat.id, audio)
                bot.delete_message(message.chat.id, status_message.message_id)
                os.remove(file_path)
            else:
                raise Exception("Файл не був створений. Спробуйте інший трек.")
                
        except Exception as e:
            bot.edit_message_text(f"❌ Помилка завантаження: {str(e)}", message.chat.id, status_message.message_id)
    else:
        bot.reply_to(message, "Будь ласка, надішли мені коректне інтернет-посилання.")

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Бот успішно перезапущений з фіксацією списків та веб-клієнтом...")
    bot.infinity_polling()
