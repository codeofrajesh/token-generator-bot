import firebase_admin
from firebase_admin import db as fdb
from firebase_admin import credentials
import logging
import random
import time

logger = logging.getLogger(__name__)

'''def save_token_to_firebase(appname: str, telegram_user_id: int, token: str):
    """
    Saves the 16-digit token to Firebase under the specific app user's node.
    """
    try:
        
        created_at = int(time.time())
        expires_at = created_at + 600
        ref = db.reference('tokens')
         
        ref.child(token).set({
            "appname": appname,
            "user_id": telegram_user_id,
            "created_at": created_at,
            "expires_at": expires_at,
            "read": 0
        })
        logger.info(f"Successfully saved Firebase token for {appname}_{telegram_user_id}")
        return True
    except Exception as e:
        print(f"🔥 FIREBASE SYNC CRASH: {str(e)}", flush=True)
        logger.error(f"Failed to save token to Firebase for {appname}_{telegram_user_id}: {e}")
        return False'''



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

def claim_pregenerated_token(user_id):
    """Fetches an unused token, automatically recycling abandoned ones."""
    try:
        # Connect to your Firebase tokens folder
        ref = fdb.reference('token') 
        
        # 1. Fetch a batch of tokens that the APP says are unused (read == "0")
        # We limit to 200 to keep it lightning fast, but give us a good pool to pick from.
        query_result = ref.order_by_child('read').equal_to("0").limit_to_first(200).get()
        
        # Fallback just in case the app saves it as an integer (0) instead of a string ("0")
        if not query_result:
            query_result = ref.order_by_child('read').equal_to(0).limit_to_first(200).get()
            
        if not query_result:
            return None, "No unused tokens left in the database."

        fresh_keys = []
        abandoned_keys = []
        
        current_time = int(time.time())
        abandon_limit_seconds = 15 * 60  # 15 MINUTES (You can change this)
        
        # 2. Sort the batch into "Fresh" and "Abandoned"
        for key, data in query_result.items():
            dispensed_to = data.get("dispensed_to")
            dispensed_at = data.get("dispensed_at", 0)
            
            if not dispensed_to:
                # Completely untouched by the bot
                fresh_keys.append(key)
            elif current_time - dispensed_at > abandon_limit_seconds:
                # Touched by the bot, but the user abandoned it for over 15 minutes!
                abandoned_keys.append(key)

        # 3. Decide which token to dispense
        selected_key = None
        if fresh_keys:
            # Prioritize completely fresh tokens
            selected_key = random.choice(fresh_keys)
        elif abandoned_keys:
            # If no fresh ones exist, recycle an abandoned one!
            selected_key = random.choice(abandoned_keys)
            print(f"♻️ RECYCLED ABANDONED TOKEN: {selected_key}")
        else:
            return None, "All tokens are currently pending app verification. Please try again in a few minutes."

        actual_token = query_result[selected_key].get("token")

        # 4. Apply the Shadow Tag with a precise Timestamp
        ref.child(selected_key).update({
            "dispensed_to": str(user_id),
            "dispensed_at": current_time
        })

        return actual_token, None
        
    except Exception as e:
        return None, str(e)