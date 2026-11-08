import os
import re
import telebot
from yt_dlp import YoutubeDL
from threading import Thread
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Бот працює стабільно та надійно!"

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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8',
        }
    }
    
    # Витягуємо чистий текст назви треку з URL Shazam
    if "shazam.com" in url_or_search:
        clean_url = url_or_search.split('?')
        match = re.search(r'/track/\d+/([^/]+)', clean_url[0])
        if match:
            # Перетворюємо фрагмент посилання "color-your-night" на слова "color your night"
            keywords = match.group(1).replace('-', ' ')
            # Використовуємо DuckDuckGo відео-пошук для повного обходу блокувань YouTube
            url_to_download = f"ddgsearch1:{keywords} audio"
        else:
            raise Exception("Не вдалося розпізнати назву пісні з структури посилання.")
    else:
        url_to_download = url_or_search

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url_to_download, download=True)
        if 'entries' in info:
            if info['entries']:
                info = info['entries'][0]
            else:
                raise Exception("Нічого не знайдено за назвою треку у вільних джерелах.")
        
        filename = ydl.prepare_filename(info)
        mp3_filename = os.path.splitext(filename)[0] + '.mp3'
        return mp3_filename

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Надішли мені посилання на трек із Shazam, і я завантажу його для тебе як MP3!")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        # Критичне фіксування: беремо перший елемент списку як чистий рядок (String)
        clean_url = urls[0]
        status_message = bot.reply_to(message, "🔍 Обходжу блоки, шукаю та нарізаю твій трек...")
        try:
            file_path = download_audio(clean_url)
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as audio:
                    bot.send_audio(message.chat.id, audio)
                bot.delete_message(message.chat.id, status_message.message_id)
                os.remove(file_path)
            else:
                raise Exception("Помилка генерації MP3 файлу на сервері.")
                
        except Exception as e:
            bot.edit_message_text(f"❌ Помилка завантаження: {str(e)}", message.chat.id, status_message.message_id)
    else:
        bot.reply_to(message, "Будь ласка, надішли мені повідомлення з коректним інтернет-посиланням.")

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Бот успішно запущений в обхідному режимі DuckDuckGo...")
    bot.infinity_polling()
