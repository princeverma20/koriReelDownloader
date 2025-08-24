from flask import Flask, request
import os
from Downloader import bot, start_bot_webhook, TOKEN

app = Flask("start_init")  # Flask app name

# ---------------- FLASK ROUTES ----------------
@app.route("/")
def home():
    return "Telegram Downloader Bot is running!"

@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    json_data = request.get_json(force=True)
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return "OK", 200

# ---------------- RUN FLASK ----------------
if __name__ == "__main__":
    domain = "https://<YOUR_DOMAIN>"  # Replace with your deployed URL
    start_bot_webhook(domain)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
