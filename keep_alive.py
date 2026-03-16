from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running!"

def run():
    # Render assigns a dynamic port, we must use it
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port,

use_reloader=False)

def keep_alive():
    """Starts the Flask server in a separate thread so it doesn't block the bot"""
    t = Thread(target=run)
    t.daemon = True
    t.start()