import os
import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

async def backup_database():
    print("🛡️ STARTING SAFETY BACKUP...")
    client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
    db = client[os.getenv("DB_NAME", "music_app_pro")]
    
    # Check which collection we are using
    collection_name = "songs"
    if await db.master_library.count_documents({}) > 0:
        collection_name = "master_library"
    
    print(f"📦 Backing up collection: '{collection_name}'...")
    
    songs = await db[collection_name].find({}).to_list(length=20000)
    
    # Save to a local file with a timestamp
    filename = f"backup_songs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        # Convert ObjectId and ints to strings for JSON compatibility
        json_ready = []
        for s in songs:
            s["_id"] = str(s["_id"])
            json_ready.append(s)
        json.dump(json_ready, f, indent=4)
        
    print(f"✅ BACKUP SAVED: {filename}")
    print(f"🔒 You have {len(songs)} songs saved safely on your computer.")

if __name__ == "__main__":
    asyncio.run(backup_database())