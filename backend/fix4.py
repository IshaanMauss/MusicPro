import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def fix_single_record():
    client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
    db = client[os.getenv("DB_NAME", "music_app_pro")]
    
    print("🎯 Target: Update ID 4 to 'Old King Cole'")
    
    # We use update_one with an upsert=False to ensure we only touch existing data
    result = await db.master_library.update_one(
        {"_id": 4},
        {"$set": {"title": "Old King Cole (VERIFIED)"}}
    )
    
    print(f"📈 Matched count: {result.matched_count}")
    print(f"📝 Modified count: {result.modified_count}")
    
    # Immediate Verification
    updated_doc = await db.master_library.find_one({"_id": 4})
    print(f"🧐 Database now shows: {updated_doc.get('title')}")

if __name__ == "__main__":
    asyncio.run(fix_single_record())