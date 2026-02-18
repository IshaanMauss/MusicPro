import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def scout_structure():
    client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
    db = client[os.getenv("DB_NAME", "music_app_pro")]
    
    print("🔍 SCOUTING TOP 10 RECORDS...")
    cursor = db.master_library.find().limit(10)
    async for doc in cursor:
        print(f"🆔 ID: {doc['_id']} | Type: {type(doc['_id'])} | Title: {doc.get('title')}")

if __name__ == "__main__":
    asyncio.run(scout_structure())