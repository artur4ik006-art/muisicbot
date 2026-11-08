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
        # Використовуємо виключно імітацію офіційного Android-додатка YouTube Music
        'extractor_args': {
            'youtube': {
                'player_client': ['android_music'],
                'player_skip': ['webpage', 'configs']
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.android.apps.youtube.music/6.31.55 (Linux; U; Android 11; uk_UA; G3112 Build/48.1.A.2.112)',
            'Accept': '*/*',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8',
        }
    }
    
    if "shazam.com" in url_or_search:
        clean_url = url_or_search.split('?')
        match = re.search(r'/track/\d+/([^/]+)', clean_url[0])
        if match:
            # Очищаємо назву треку (наприклад: з "my-moon-my-man" робимо "my moon my man")
            keywords = match.group(1).replace('-', ' ')
            url_to_download = f"ytsearch1:{keywords} audio"
        else:
            raise Exception("Не вдалося розпізнати структуру посилання Shazam.")
    else:
        url_to_download = url_or_search

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url_to_download, download=True)
        if 'entries' in info:
            if info['entries']:
                info = info['entries'][0]
            else:
                raise Exception("Нічого не знайдено за назвою треку.")
        
        filename = ydl.prepare_filename(info)
        mp3_filename = os.path.splitext(filename)[0] + '.mp3'
        return mp3_filename

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Скинь мені посилання на трек із Shazam чи YouTube, і я завантажу його для тебе як MP3!")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    text = message.text
    urls = re.findall(r'(https?://\S+)', text)
    
    if urls:
        # КРИТИЧНЕ ВИПРАВЛЕННЯ: беремо перший елемент масиву як чистий рядок БЕЗ дужок і лапок
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
                raise Exception("Помилка створення MP3 файлу на сервері.")
                
        except Exception as e:
            bot.edit_message_text(f"❌ Помилка завантаження: {str(e)}", message.chat.id, status_message.message_id)
    else:
        bot.reply_to(message, "Будь ласка, надішли мені коректне інтернет-посилання.")

if __name__ == '__main__':
    Thread(target=run_web).start()
    print("Бот успішно перезапущений з виправленим чистим URL...")
    bot.infinity_polling()
