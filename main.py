\import os
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
        # Повне маскування запитів для SoundCloud/інших джерел
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    }
    
    # Вирізаємо назву з посилання Shazam
    if "shazam.com" in url_or_search:
        clean_url = url_or_search.split('?')
        match = re.search(r'/track/\d+/([^/]+)', clean_url[0])
        if match:
            # Наприклад: "my moon my man"
            keywords = match.group(1).replace('-', ' ')
            # Використовуємо стабільний пошук SoundCloud без API ключів за допомогою прямого кодування
            url_to_download = f"scsearch1:{keywords}"
        else:
            raise Exception("Не вдалося розпізнати посилання Shazam.")
    else:
        url_to_download = url_or_search

    with YoutubeDL(ydl_opts) as ydl:
        # Спочатку отримуємо інформацію про трек без глибокого аналізу
        info = ydl.extract_info(url_to_download, download=True)
        
        if 'entries' in info:
            if info['entries'] and info['entries'][0]:
                info = info['entries'][0]
            else:
                raise Exception("Не вдалося знайти вільний аудіопотік у мережі.")
        
        filename = ydl.prepare_filename(info)
        mp3_filename = os.path.splitext(filename)[0] + '.mp3'
        return mp3_filename

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Скинь мені посилання на трек із Shazam, і я завантажу його для тебе!")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        # Критичне виправлення: дістаємо перший елемент списку як звичайний текстовий рядок
        clean_url = str(urls[0]) 
        status_message = bot.reply_to(message, "🔍 Шукаю та нарізаю трек, зачекай трішки...")
        try:
            file_path = download_audio(clean_url)
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as audio:
                    bot.send_audio(message.chat.id, audio)
                bot.delete_message(message.chat.id, status_message.message_id)
                os.remove(file_path)
            else:
                raise Exception("Помилка створення аудіофайлу.")
                
        except Exception as e:
            bot.edit_message_text(f"❌ Помилка завантаження: {str(e)}", message.chat.id, status_message.message_id)
    else:
        bot.reply_to(message, "Будь ласка, надішли мені коректне інтернет-посилання.")

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Бот успішно перезапущений з виправленим парсером рядків...")
    bot.infinity_polling()
