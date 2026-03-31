import firebase_admin
from firebase_admin import db
from firebase_admin import credentials
import logging
import time

logger = logging.getLogger(__name__)

def save_token_to_firebase(appname: str, telegram_user_id: int, token: str):
    """
    Saves the 16-digit token to Firebase under the specific app user's node.
    """
    try:
        
        firebase_key = f"App_{appname}_{telegram_user_id}"
        created_at = int(time.time())
        expires_at = created_at + 600
        ref = db.reference('tokens')
         
        ref.child(firebase_key).set({
            "token": token,
            "created_at": created_at,
            "expires_at": expires_at,
            "read": 0
        })
        logger.info(f"Successfully saved Firebase token for {appname}_{telegram_user_id}")
        return True
    except Exception as e:
        print(f"🔥 FIREBASE SYNC CRASH: {str(e)}", flush=True)
        logger.error(f"Failed to save token to Firebase for {appname}_{telegram_user_id}: {e}")
        return False



def reload_firebase(new_url: str):
    """Safely tears down the old Firebase connection and starts a new one."""
    try:
        # 1. Check if an app is already running and delete it
        default_app = firebase_admin.get_app()
        firebase_admin.delete_app(default_app)
    except ValueError:
        # If no app exists yet, that's completely fine
        pass

    try:
        # 2. Start a fresh connection with the new downloaded key and URL
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': new_url
        })
        return True, "Success"
    except Exception as e:
        return False, str(e)    