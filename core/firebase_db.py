import firebase_admin
from firebase_admin import db
from firebase_admin import credentials
import logging
import time

logger = logging.getLogger(__name__)

def save_token_to_firebase(app_user_id: str, token: str, validity_minutes: int = 10) -> bool:
    """
    Saves the 16-digit token to Firebase under the specific app user's node.
    """
    try:
        # Creates a reference like: /users/app_User123/auth
        ref = db.reference(f'users/{app_user_id}/auth')
        
        expires_at = time.time() + (validity_minutes * 60)
        
        # Overwrite any existing token data for this user
        ref.set({
            'token': token,
            'expires_at': expires_at,
            'created_at': time.time(),
            'is_valid': True
        })
        logger.info(f"Successfully saved Firebase token for {app_user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to save token to Firebase for {app_user_id}: {e}")
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