from firebase_admin import db
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