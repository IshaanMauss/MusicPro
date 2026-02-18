import os
import asyncio
import re
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

def clean(s):
    # Removes special chars for easier matching
    return re.sub(r'[^a-zA-Z0-9]', '', str(s)).lower().strip()

async def fix_mismatched_titles():
    print("📡 Connecting to Telegram to read REAL filenames...")
    await client.start()
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    # 1. Load OLD songs (Backup) for Metadata Lookup
    # We need this so when we rename the song, we can still find its artist/image
    print("📥 Loading backup metadata...")
    old_songs = await db.songs.find({}).to_list(length=15000)
    
    meta_lookup = {}
    for s in old_songs:
        title = s.get('title')
        if title:
            meta_lookup[clean(title)] = s
            
    print(f"✅ Loaded backup metadata. Starting Reality Sync...")
    
    collection = db.master_library
    fixed_count = 0
    
    # Iterate through every message in the channel
    async for message in client.iter_messages(CHANNEL_ID, limit=15000):
        if message.file and message.file.name:
            try:
                # 1. EXTRACT REAL TITLE
                # "Old King Cole-Bhf0MM_F25I.m4a" -> "Old King Cole"
                real_filename = message.file.name.rsplit('.', 1)[0] 
                
                # Remove YouTube ID suffix if it exists (looks like -Bhf0MM_F25I)
                if '-' in real_filename:
                    parts = real_filename.rsplit('-', 1)
                    if len(parts[1]) == 11:
                        real_filename = parts[0]
                
                clean_real_name = clean(real_filename)
                
                # 2. FIND METADATA FOR THIS REAL TITLE
                correct_meta = meta_lookup.get(clean_real_name)
                
                # 3. PREPARE UPDATE
                # We FORCE the title to match the file
                update_data = {
                    "title": real_filename.strip(), 
                    "file_name": message.file.name
                }
                
                # Recover Artist/Image if we have it in backup
                if correct_meta:
                    update_data["artist"] = correct_meta.get("artist", "Unknown")
                    update_data["album_art"] = correct_meta.get("album_art") or correct_meta.get("cover_url")
                    update_data["genre"] = correct_meta.get("genre", [])
                
                # 4. UPDATE DATABASE RECORD
                await collection.update_one(
                    {"_id": message.id},
                    {"$set": update_data}
                )
                
                fixed_count += 1
                if fixed_count % 500 == 0:
                    print(f"✅ Aligned {fixed_count} songs... (Last: {real_filename})")
            
            except Exception as e:
                print(f"⚠️ Skipped ID {message.id}: {e}")

    print(f"\n✨ DONE! {fixed_count} songs have been renamed to match their actual audio files.")

if __name__ == "__main__":
    asyncio.run(fix_mismatched_titles())