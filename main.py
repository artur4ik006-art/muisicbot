import os
import telebot
from yt_dlp import YoutubeDL
from threading import Thread
from flask import Flask

# Створюємо міні-вебсайт, щоб Render думав, що це звичайна сторінка
app = Flask('')

@app.route('/')
def home():
    return "Бот працює!"

def run_web():
    # Запускаємо веб-сервер на порті, який вимагає Render
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Ваш токен
BOT_TOKEN = '9019116927:AAGKjHLRDNEp-BpmZaUqfF1pIBTiBsL3YyI'
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '/tmp/%(title)s.%(ext)s',  
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True  
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return os.path.splitext(filename) + '.mp3'

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Надішли мені посилання на трек (YouTube, Spotify, Shazam тощо), і я спробую завантажити його для тебе як MP3!")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    text = message.text
    if "http://" in text or "https://" in text:
        status_message = bot.reply_to(message, "🔍 Шукаю та завантажую трек, зачекай трішки...")
        try:
            file_path = download_audio(text)
            with open(file_path, 'rb') as audio:
                bot.send_audio(message.chat.id, audio)
            bot.delete_message(message.chat.id, status_message.message_id)
            os.remove(file_path)
        except Exception as e:
            bot.edit_message_text(f"❌ Помилка завантаження: {str(e)}", message.chat.id, status_message.message_id)
    else:
        bot.reply_to(message, "Будь ласка, надішли мені коректне інтернет-посилання.")

if __name__ == '__main__':
    # Запускаємо веб-сервер у фоні для обходу обмежень Render
    Thread(target=run_web).start()
    print("Бот успішно запущенний на безкоштовному тарифі...")
    bot.infinity_polling()
