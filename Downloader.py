import telebot
import yt_dlp
import os
import re
import asyncio
import threading
import time

bot = telebot.TeleBot('7868993075:AAEWXgddqq_huYD_WpDEwjMH-LA4UFSKDyM')

# ---- Create one global asyncio loop ----
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
threading.Thread(target=loop.run_forever, daemon=True).start()


# ---------------- HANDLERS ----------------
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Welcome to the Downloader Bot!\n\n"
        "📥 Send me one or more video links (YouTube, Instagram, Vimeo, etc.), \n\n"
        "➡️ Paste links separated by space or new lines 👇"
    )


# Validate URLs
def is_valid_url(url):
    pattern = re.compile(
        r'https?://(?:www\.)?(?:youtube\.com|youtu\.be|instagram\.com|vimeo\.com)/'
    )
    return re.match(pattern, url) is not None


# Extract a safe filename from URL
def get_filename_from_url(url, index):
    # Instagram Reel -> use ID part
    ig_match = re.search(r"instagram\.com/reels?/([^/?#]+)", url)
    if ig_match:
        return f"{ig_match.group(1)}.mp4"

    # YouTube -> use video ID
    yt_match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    if yt_match:
        return f"{yt_match.group(1)}.mp4"

    # Default -> timestamp + index
    return f"video_{int(time.time())}_{index}.mp4"


# Blocking download function
def blocking_download(url, chat_id, index):
    try:
        filename = get_filename_from_url(url, index)

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'outtmpl': filename,
            'ffmpeg_location': 'D:/TgBots/ffmpeg/bin',
            'socket_timeout': 600,  # prevent timeout for big files
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # send to Telegram
        with open(filename, 'rb') as f:
            bot.send_video(chat_id, f)

        os.remove(filename)  # cleanup

    except Exception as e:
        bot.send_message(chat_id, f"❌ Error downloading {url}:\n{str(e)}")


# Async wrapper for the handler
@bot.message_handler(func=lambda message: True)
def download_video(message):
    urls = message.text.split()
    chat_id = message.chat.id

    valid_urls = [u for u in urls if is_valid_url(u)]

    if not valid_urls:
        bot.reply_to(message, "⚠️ Please provide valid video URLs (YouTube, Instagram, etc.).")
        return

    for idx, url in enumerate(valid_urls):
        bot.send_message(chat_id, f"⏳ Downloading: {url}")
        # schedule blocking download safely
        asyncio.run_coroutine_threadsafe(
            asyncio.to_thread(blocking_download, url, chat_id, idx), loop
        )


# ---------------- RUN ----------------
print("🚀waiting for links.. Please Wait....")
bot.polling(non_stop=True)
