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
        await self.shorteners.delete_one({"_id": ObjectId(shortener_id)})

# Initialize the database object to be imported elsewhere
db = Database()