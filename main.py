import os
import telebot
from yt_dlp import YoutubeDL

# Ініціалізація бота
BOT_TOKEN = '9019116927:AAGKjHLRDNEp-BpmZaUqfF1pIBTiBsL3YyI'
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Функція для завантаження аудіо
def download_audio(url):
    # Налаштування для yt-dlp: завантажуємо лише аудіо найкращої якості та конвертуємо в mp3
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # Збереження у папку downloads
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True  # Менше зайвого тексту в консолі
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # Отримуємо шлях до створеного файлу
        filename = ydl.prepare_filename(info)
        # Змінюємо розширення в імені файлу на mp3, оскільки postprocessor конвертував його
        mp3_filename = os.path.splitext(filename)[0] + '.mp3'
        return mp3_filename

# Обробник команди /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Надішли мені посилання на трек (YouTube, Spotify, Shazam тощо), і я спробую завантажити його для тебе як MP3!")

# Обробник текстових повідомлень (посилань)
@bot.message_handler(func=lambda message: True)
def handle_link(message):
    text = message.text
    
    # Проста перевірка, чи є повідомлення посиланням
    if "http://" in text or "https://" in text:
        status_message = bot.reply_to(message, "🔍 Шукаю та завантажую трек, зачекай трішки...")
        
        try:
            # Завантажуємо файл
            file_path = download_audio(text)
            
            # Надсилаємо аудіофайл користувачу
            with open(file_path, 'rb') as audio:
                bot.send_audio(message.chat.id, audio)
            
            # Видаляємо статус-повідомлення та завантажений файл з диска, щоб не засмічувати пам'ять
            bot.delete_message(message.chat.id, status_message.message_id)
            os.remove(file_path)
            
        except Exception as e:
            bot.edit_message_text(f"❌ Не вдалося завантажити трек. Можливо, посилання не підтримується або виникла помилка. {str(e)}", 
                                  message.chat.id, status_message.message_id)
    else:
        bot.reply_to(message, "Будь ласка, надішли мені коректне інтернет-посилання.")

# Запуск бота
if __name__ == '__main__':
