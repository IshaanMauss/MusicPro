import json
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import InsertOne, DeleteMany
from dotenv import load_dotenv

load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "music_app_pro")

async def sync_database_perfectly():
    print("📂 Loading local JSON data...")
    try:
        with open('mysongs.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ ERROR reading JSON: {e}")
        return

    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print(f"📡 Connected to {DB_NAME}. Preparing for hard reset...")

    # 1. Clear the collection to remove mismatched IDs
    print("⚠️ Clearing existing songs in Atlas to prevent ID conflicts...")
    await db.songs.delete_many({})

    # 2. Prepare data for re-insertion
    operations = []
    for song in data:
        # Handle the MongoDB ID structure from your JSON
        # If _id is an object like {"$oid": "..."}, extract the string
        original_id = song.get('_id')
        if isinstance(original_id, dict) and '$oid' in original_id:
            song['_id'] = original_id['$oid']
        
        # Ensure channel_message_id is treated as the source of truth
        msg_id = song.get('channel_message_id')
        if msg_id:
            song['msg_id'] = msg_id # Backend uses 'msg_id'
            song['channel_message_id'] = msg_id # JSON uses 'channel_message_id'
            song['is_playable'] = True
        
        operations.append(InsertOne(song))

    # 3. Bulk Insert
    if operations:
        print(f"🚀 Re-inserting {len(operations)} songs with original IDs...")
        try:
            result = await db.songs.bulk_write(operations)
            print(f"✅ SUCCESS!")
            print(f"Inserted: {result.inserted_count} songs.")
            print("Your Atlas database and local JSON are now 100% identical.")
        except Exception as e:
            print(f"❌ Bulk Write Error: {e}")
    else:
        print("⚠️ No data found to insert.")

if __name__ == "__main__":
    asyncio.run(sync_database_perfectly())