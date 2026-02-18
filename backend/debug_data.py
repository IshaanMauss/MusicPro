import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def check_the_truth():
    client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
    db = client[os.getenv("DB_NAME", "music_app_pro")]

    print("🕵️ INVESTIGATING SONG ID 4...")

    # 1. Check 'master_library' (The New Collection)
    master_song = await db.master_library.find_one({"_id": 4})
    if master_song:
        print(f"✅ master_library says ID 4 is: '{master_song.get('title')}'")
    else:
        print("❌ ID 4 not found in master_library")

    # 2. Check 'songs' (The Old Collection)
    old_song = await db.songs.find_one({"_id": 4}) # It might be a string "4" or int 4
    if not old_song:
        # Try string lookup just in case
        old_song = await db.songs.find_one({"_id": "4"})
        
    if old_song:
        print(f"⚠️ old 'songs' collection says ID 4 is: '{old_song.get('title')}'")
    else:
        print("ℹ️ ID 4 not found in old songs collection (This is good)")

if __name__ == "__main__":
    asyncio.run(check_the_truth())