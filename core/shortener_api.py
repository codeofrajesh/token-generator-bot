import requests
import logging
from config import Config

logger = logging.getLogger(__name__)

'''def get_short_link(long_url: str) -> str:
    try:
        api_url = f"{Config.SHORTENER_API_URL}?api={Config.SHORTENER_API_KEY}&url={long_url}"
        
        response = requests.get(api_url)
        data = response.json()
        if data.get("status") == "success" or "shortenedUrl" in data:
            return data.get("shortenedUrl")
        else:
            logger.error(f"Shortener API returned an error: {data}")
            return long_url  # Fallback to the long URL if the API fails
            
    except Exception as e:
        logger.error(f"Failed to connect to Shortener API: {e}")
        return long_url # Fallback to the long URL if there's a connection error'''

def get_short_link(api_url: str, api_key: str, long_url: str) -> str:
    try:
        # Most shorteners use this standard format
        api_link = f"{api_url}?api={api_key}&url={long_url}"
        response = requests.get(api_link, timeout=5).json()
        
        if response.get("status") == "success":
            return response.get("shortenedUrl")
        else:
            return long_url # Fallback to long URL if shortener fails
    except Exception as e:
        print(f"Shortener API Error: {e}")
        return long_url