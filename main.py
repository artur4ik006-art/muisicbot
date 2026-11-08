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
        # Пропускаємо системні конфіги клієнта YouTube, які викликають капчу
        'extractor_args': {
            'youtube': {
                'player_skip': ['configs', 'webpage'],
                'player_client': ['android', 'mweb']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8',
        }
    }
    
    if "shazam.com" in url_or_search:
        clean_url = url_or_search.split('?')
        match = re.search(r'/track/\d+/([^/]+)', clean_url[0])
        if match:
            # Перетворюємо шлях тексту на пошукову фразу (наприклад: "my moon my man")
            keywords = match.group(1).replace('-', ' ')
            # Шукаємо перше ліпше відео на YouTube (зазвичай це неофіційні перезавантаження, де немає DRM-захисту)
            url_to_download = f"ytsearch1:{keywords} lyrics"
        else:
            raise Exception("Не вдалося розпізнати посилання Shazam.")
    else:
        url_to_download = url_or_search

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url_to_download, download=True)
        if 'entries' in info:
            if info['entries']:
                info = info['entries'][0]
            else:
                raise Exception("Аудіофайл не знайдено.")
        
        filename = ydl.prepare_filename(info)
        return os.path.splitext(filename)[0] + '.mp3'

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Скинь мені посилання на трек із Shazam, і я завантажу його для тебе!")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        clean_url = urls[0] # Чітко передаємо перший рядок-посилання
        status_message = bot.reply_to(message, "🔍 Шукаю та нарізаю трек, зачекай трішки...")
        try:
            file_path = download_audio(clean_url)
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as audio:
                    bot.send_audio(message.chat.id, audio)
                bot.delete_message(message.chat.id, status_message.message_id)
                os.remove(file_path)
            else:
                raise Exception("Помилка обробки файлу на сервері.")
                
        except Exception as e:
            bot.edit_message_text(f"❌ Помилка завантаження: {str(e)}", message.chat.id, status_message.message_id)
    else:
        bot.reply_to(message, "Будь ласка, надішли мені коректне інтернет-посилання.")

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Бот запущений у стабільному мобільному режимі пошуку...")
    bot.infinity_polling()
