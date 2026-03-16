import os
from dotenv import load_dotenv

# Load environment variables from a .env file for local testing
load_dotenv()

class Config:
    # Telegram Bot Credentials
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    MONGO_URI = os.environ.get("MONGO_URI", "")
    ADMIN_IDS = set(map(int, os.environ.get("ADMIN_IDS", "").split(",")))
    #SHORTENER_API_URL = os.environ.get("SHORTENER_API_URL", "https://example-shortener.com/api")
    #SHORTENER_API_KEY = os.environ.get("SHORTENER_API_KEY", "")

    # Firebase Configuration
    FIREBASE_KEY_PATH = os.environ.get("FIREBASE_KEY_PATH", "serviceAccountKey.json")
    FIREBASE_DB_URL = os.environ.get("FIREBASE_DB_URL", "https://your-project.firebaseio.com/")
    MIN_BYPASS_TIME = int(os.environ.get("MIN_BYPASS_TIME", "15"))

    # --- NEW ADDITIONS FOR DEMO/MENU MODE ---

    LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", "-1000000000000"))
    

    JOIN_CHANNEL_URL = os.environ.get("JOIN_CHANNEL_URL", "https://t.me/+eFDx981rC5thMWNl")

    """const firebaseConfig = {
  apiKey: "AIzaSyCErJLSFA1tRJnHp_GlGpWHgM3RH3giZTQ",
  authDomain: "testapp-49380.firebaseapp.com",
  projectId: "testapp-49380",
  storageBucket: "testapp-49380.firebasestorage.app",
  messagingSenderId: "353884696585",
  appId: "1:353884696585:web:bb60f050c464739d1788d8",
  measurementId: "G-8V6RQJ7TYW"
};"""

#https://testapp-49380-default-rtdb.asia-southeast1.firebasedatabase.app/