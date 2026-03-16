import logging
from pyrogram import Client
from config import Config
import firebase_admin
from firebase_admin import credentials
from keep_alive import keep_alive

# Set up logging to monitor bot activity and errors
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def initialize_firebase():
    """Initializes the Firebase Admin SDK securely."""
    try:
        cred = credentials.Certificate(Config.FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': Config.FIREBASE_DB_URL
        })
        logger.info("Firebase initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")

# Initialize the Pyrogram Client
# The 'plugins' argument tells Pyrogram to look for handlers in the plugins/ folder
app = Client(
    "token_generator_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="plugins")
)

if __name__ == "__main__":
    logger.info("Starting the Token Generator Bot...")
    initialize_firebase()
# START THE FLASK SERVER FIRST
    logger.info("Triggering Flask keep_alive thread...")
    keep_alive()
    time.sleep(2)
    # THEN START THE BOT
    print("Starting bot...")
    app.run()    