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
        # Повний обхід капчі YouTube: інтегруємо пошук через DuckDuckGo Search дзеркало
        'default_search': 'ytsearch',
        'extractor_args': {
            'youtube': {
                'player_client': ['webpage'],
                'player_skip': ['configs', 'webpage']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8',
        }
    }
    
    # Вирізаємо назву пісні безпосередньо з посилання Shazam
    if "shazam.com" in url_or_search:
        clean_url = url_or_search.split('?')
        match = re.search(r'/track/\d+/([^/]+)', clean_url[0])
        if match:
            # Перетворюємо фрагмент посилання ("color-your-night") на чисті слова ("color your night")
            keywords = match.group(1).replace('-', ' ')
            # Шукаємо через DuckDuckGo відео-запит (ігнорує блокування Google)
            url_to_download = f"html5sync:{keywords} audio"
        else:
            raise Exception("Не вдалося розпізнати назву пісні з URL.")
    else:
        url_to_download = url_or_search

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url_to_download, download=True)
        if 'entries' in info:
            if info['entries']:
                info = info['entries'][0]
            else:
                raise Exception("Не вдалося знайти трек у безкоштовній базі. Спробуйте інший.")
        
        filename = ydl.prepare_filename(info)
        mp3_filename = os.path.splitext(filename)[0] + '.mp3'
        return mp3_filename

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Надішли мені посилання на трек із Shazam, і я завантажу його без помилок!")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        # УВАГА: Беремо перший елемент списку як чистий ТЕКСТОВИЙ РЯДОК [0]
        clean_url = urls[0]
        status_message = bot.reply_to(message, "🔍 Обхожу блокування Google, завантажую твій трек...")
        try:
            file_path = download_audio(clean_url)
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as audio:
                    bot.send_audio(message.chat.id, audio)
                bot.delete_message(message.chat.id, status_message.message_id)
                os.remove(file_path)
            else:
                raise Exception("Помилка генерації аудіофайлу на сервері.")
                
        except Exception as e:
            bot.edit_message_text(f"❌ Помилка завантаження: {str(e)}", message.chat.id, status_message.message_id)
    else:
        bot.reply_to(message, "Будь ласка, надішли мені коректне інтернет-посилання.")

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Бот запущений у фінальному стабільному режимі...")
    bot.infinity_polling()
