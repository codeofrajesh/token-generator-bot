# core/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self.client["TokenBotDB"]
        self.settings = self.db["settings"]
        self.shorteners = self.db["shorteners"]

    async def get_bypass_time(self):
        data = await self.settings.find_one({"_id": "config"})
        return data.get("bypass_time", Config.MIN_BYPASS_TIME) if data else Config.MIN_BYPASS_TIME

    async def set_bypass_time(self, seconds: int):
        await self.settings.update_one(
            {"_id": "config"}, 
            {"$set": {"bypass_time": seconds}}, 
            upsert=True
        )

    async def get_all_shorteners(self):
        cursor = self.shorteners.find({})
        return await cursor.to_list(length=4) # Max 4 as you requested

    async def add_shortener(self, name: str, api_url: str, api_key: str):
        await self.shorteners.insert_one({
            "name": name,
            "api_url": api_url,
            "api_key": api_key
        })
        
    async def remove_shortener(self, shortener_id: str):
        from bson.objectid import ObjectId
        result = await self.shorteners.delete_one({"_id": ObjectId(shortener_id)})
        return result.deleted_count > 0

    async def get_main_url(self):
        data = await self.settings.find_one({"_id": "config"})
        return data.get("main_url", "https://t.me/telegram") if data else "https://t.me/telegram"

    async def set_main_url(self, url: str):
        await self.settings.update_one(
            {"_id": "config"}, 
            {"$set": {"main_url": url}}, 
            upsert=True
        )  

    # --- USER TRACKING FOR STATS & BROADCAST ---
    async def add_user(self, user_id: int, first_name: str, username: str):
        """Saves a user ID, name, and username to the database."""
        await self.db.users.update_one(
            {"_id": user_id}, 
            {"$set": {
                "_id": user_id,
                "first_name": first_name or "Unknown",
                "username": username or "None"
            }}, 
            upsert=True
        )

    async def get_total_users(self):
        """Counts the total number of users who have started the bot."""
        return await self.db.users.count_documents({})

    async def get_all_users(self):
        """Fetches a list of all user IDs for broadcasting."""
        # Returns a list of dictionaries like [{"_id": 12345}, {"_id": 67890}]
        return await self.db.users.find({}).to_list(length=None)    

    # --- CO-ADMIN MANAGEMENT ---
    async def is_coadmin(self, user_id: int) -> bool:
        """Checks if a user is in the co-admin list."""
        user = await self.db.coadmins.find_one({"_id": user_id})
        return bool(user)

    async def add_coadmin(self, user_id: int):
        """Grants a user co-admin privileges."""
        await self.db.coadmins.update_one({"_id": user_id}, {"$set": {"_id": user_id}}, upsert=True)

    async def remove_coadmin(self, user_id: int):
        """Revokes co-admin privileges."""
        await self.db.coadmins.delete_one({"_id": user_id})

    async def get_how_to_use_url(self):
        data = await self.settings.find_one({"_id": "config"})
        # Fallback to Telegram home if admin hasn't set it yet to prevent crashes
        return data.get("how_to_use_url", "https://t.me/telegram")

    async def set_how_to_use_url(self, url: str):
        await self.settings.update_one(
            {"_id": "config"}, 
            {"$set": {"how_to_use_url": url}}, 
            upsert=True
        )    

    async def get_welcome_config():
        """Fetches the welcome text and image ID from the database."""
        config = await db.bot_config.find_one({"_id": "welcome_settings"})
        if config:
            return config.get("text"), config.get("image_id")
        # Default fallback if admin hasn't set anything yet
        return "👋 Welcome to the Bot!", None

    async def set_welcome_config(text, image_id):
        """Saves the custom welcome text and image ID."""
        await db.bot_config.update_one(
            {"_id": "welcome_settings"}, 
            {"$set": {"text": text, "image_id": image_id}}, 
            upsert=True
        )    

# Initialize the database object to be imported elsewhere
db = Database()