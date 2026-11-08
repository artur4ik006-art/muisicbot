import os
import telebot
from yt_dlp import YoutubeDL

# Ваш токен вже вшитий у код для надійності
BOT_TOKEN = '9019116927:AAGKjHLRDNEp-BpmZaUqfF1pIBTiBsL3YyI'
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        # На Render файли безпечно писати у тимчасову папку /tmp
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
        mp3_filename = os.path.splitext(filename)[0] + '.mp3'
        return mp3_filename

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
            bot.edit_message_text(f"❌ Не вдалося завантажити трек. Ошибка: {str(e)}", 
                                  message.chat.id, status_message.message_id)
    else:
        bot.reply_to(message, "Будь ласка, надішли мені коректне інтернет-посилання.")

if __name__ == '__main__':
    print("Бот успішно запущений...")
    bot.infinity_polling()
