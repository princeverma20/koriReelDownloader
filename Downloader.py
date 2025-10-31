import telebot
import yt_dlp
import os
import re
import asyncio
import threading
import time
import traceback
from flask import Flask, request  # ✅ added request import

# ==================== BOT SETUP ====================
BOT_TOKEN = '7868993075:AAEWXgddqq_huYD_WpDEwjMH-LA4UFSKDyM' 
bot = telebot.TeleBot(BOT_TOKEN)

# Create async loop in background thread
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
threading.Thread(target=loop.run_forever, daemon=True).start()

# ==================== FLASK WEB SERVER SETUP ====================
app = Flask(__name__)

@app.route('/')
def index():
    return "🚀 Universal Downloader Bot is running on Render!"

# ==================== HELPERS ====================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 *Welcome to Universal Downloader Bot!*\n\n"
        "📥 Supports: YouTube, Instagram, Vimeo, Terabox & others.\n\n"
        "➡️ Just send one or more video links below 👇",
        parse_mode="Markdown"
    )

def is_valid_url(url: str) -> bool:
    pattern = re.compile(
        r'https?://(?:www\.)?(?:youtube\.com|youtu\.be|instagram\.com|vimeo\.com|terabox(?:link)?\.com|1024tera\.com)/'
    )
    return re.match(pattern, url) is not None

def get_filename_from_url(url: str, index: int) -> str:
    patterns = {
        "instagram": r"instagram\.com/reels?/([^/?#]+)",
        "youtube": r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})",
        "terabox": r"(?:terabox(?:link)?\.com)/s/([A-Za-z0-9_-]+)",
    }
    for key, regex in patterns.items():
        match = re.search(regex, url)
        if match:
            return f"{key}_{match.group(1)}.mp4"
    return f"video_{int(time.time())}_{index}.mp4"

# ==================== DOWNLOAD CORE ====================
def blocking_download(url: str, chat_id: int, index: int):
    filename = get_filename_from_url(url, index)
    temp_name = f"{filename}.part"

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': filename,
        'ffmpeg_location': '/usr/bin/ffmpeg',  # ✅ path for Render/Linux
        'socket_timeout': 900,
        'retries': 10,
        'continuedl': True,
        'noplaylist': True,
        'ignoreerrors': True,
        'quiet': True,
        'no_warnings': True,
    }

    BOT_LIMIT = 50 * 1024 * 1024
    TG_USER_LIMIT = 2 * 1024 * 1024 * 1024
    
    try:
        bot.send_message(chat_id, f"📡 Fetching info from:\n{url}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                bot.send_message(chat_id, f"⚠️ Could not extract info for this URL.")
                return

            filesize = info.get("filesize") or info.get("filesize_approx") or 0
            title = info.get("title", "Untitled")
            formats = info.get("formats", [])
            best = max(formats, key=lambda f: f.get("filesize", 0) or 0)
            direct_url = best.get("url") or info.get("url")

            if filesize > BOT_LIMIT:
                if filesize <= TG_USER_LIMIT:
                    msg = (
                        f"⚠️ *File too large to upload (>50MB)*\n\n"
                        f"🎬 *Title:* {title}\n"
                        f"💾 *Size:* {round(filesize / 1024 / 1024, 2)} MB\n"
                        f"🔗 [Click here to download]({direct_url})"
                    )
                else:
                    msg = (
                        f"❌ *File exceeds Telegram’s 2GB limit!*\n\n"
                        f"🎬 *Title:* {title}\n"
                        f"🔗 Original link: {url}"
                    )
                bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=False)
                return

            bot.send_message(chat_id, "⬇️ Downloading video... please wait.")
            ydl.download([url])

        if os.path.exists(filename):
            try:
                with open(filename, "rb") as f:
                    bot.send_video(chat_id, f, caption=f"🎬 {title}", timeout=600)
                bot.send_message(chat_id, "✅ Upload complete!")
            except Exception as upload_error:
                bot.send_message(chat_id, f"⚠️ Downloaded but failed to upload: {upload_error}")
            finally:
                os.remove(filename)
        else:
            bot.send_message(chat_id, "❌ Download failed or file missing.")

    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")
        traceback.print_exc()
    finally:
        for f in [filename, temp_name]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

# ==================== MESSAGE HANDLER ====================
@bot.message_handler(func=lambda message: True)
def handle_links(message):
    urls = message.text.split()
    chat_id = message.chat.id
    valid_urls = [u for u in urls if is_valid_url(u)]

    if not valid_urls:
        bot.reply_to(message, "⚠️ Please send valid video URLs (YouTube, Instagram, etc.).")
        return

    for idx, url in enumerate(valid_urls):
        bot.send_message(chat_id, f"⏳ Processing: {url}")
        asyncio.run_coroutine_threadsafe(
            asyncio.to_thread(blocking_download, url, chat_id, idx),
            loop
        )

# ==================== WEBHOOK SETUP ====================
WEBHOOK_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'OK', 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print(f"🚀 Webhook set to {WEBHOOK_URL}")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
