import os
import asyncio
from telethon import TelegramClient
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# Config
CHANNEL_ID = -1003681118965 
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "music_app_pro")

client = TelegramClient('user_session', API_ID, API_HASH)

def clean_title(filename):
    # 1. Remove extension
    name = filename.rsplit('.', 1)[0]
    # 2. Remove YouTube ID suffix if present
    if '-' in name:
        parts = name.rsplit('-', 1)
        if len(parts[1]) == 11:
            name = parts[0]
    return name.replace('_', ' ').replace('-', ' ').strip()

async def force_sync_v2():
    print("🚨 STARTING FORCE SYNC V2 (Targeting 'master_library')...")
    await client.start()
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    # 🟢 CRITICAL FIX: We force it to use 'master_library'
    # This is the collection your main.py is reading from.
    collection = db.master_library
    
    print(f"📂 Connected to: {collection.name}")
    
    count = 0
    updated = 0
    
    async for message in client.iter_messages(CHANNEL_ID, limit=15000):
        if message.file and message.file.name:
            real_title = clean_title(message.file.name)
            
            # 🟢 CRITICAL FIX 2: Try updating with Integer ID first (Standard)
            # If that fails, try String ID (Legacy)
            
            # Attempt 1: Integer ID (Most likely for master_library)
            result = await collection.update_one(
                {"_id": message.id}, 
                {"$set": {"title": real_title}}
            )
            
            # Attempt 2: String ID (If int failed to find anything)
            if result.matched_count == 0:
                result = await collection.update_one(
                    {"_id": str(message.id)}, 
                    {"$set": {"title": real_title}}
                )

            if result.modified_count > 0:
                updated += 1
                if updated <= 5: # Print first 5 changes
                    print(f"✏️ FIXED ID {message.id}: Now titled '{real_title}'")
            
            count += 1
            if count % 1000 == 0:
                print(f"📡 Scanned {count} messages...")

    print(f"\n✅ SYNC V2 COMPLETE.")
    print(f"📝 Scanned: {count}")
    print(f"💾 Updated: {updated} titles in 'master_library'")

if __name__ == "__main__":
    asyncio.run(force_sync_v2())