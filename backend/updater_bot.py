import logging
import asyncio
import difflib
import re
import os
from telethon import TelegramClient, events
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# 🟢 Initialize the vault
load_dotenv()

# --- DYNAMIC CONFIGURATION ---
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN_1")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "music_app_pro")

# Database setup
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client[DB_NAME]
unverified_cache = {}

async def load_cache():
    global unverified_cache
    unverified_cache = {}
    cursor = db.songs.find({"is_verified": {"$ne": True}})
    async for song in cursor:
        clean = song['title'].lower().strip()
        unverified_cache[clean] = song['title']
    print(f"🧠 Watching for {len(unverified_cache)} missing songs.")

async def main():
    await load_cache()
    
    if not os.path.exists('sessions'):
        os.makedirs('sessions')

    bot = TelegramClient('sessions/updater_bot_session', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)

    @bot.on(events.NewMessage)
    async def handler(event):
        if event.audio or event.document:
            file_title = event.file.name or "Unknown"
            clean_input = file_title.lower().strip()
            
            db_title = unverified_cache.get(clean_input)
            if not db_title:
                matches = difflib.get_close_matches(clean_input, unverified_cache.keys(), n=1, cutoff=0.80)
                if matches:
                    db_title = unverified_cache[matches[0]]

            if db_title:
                try:
                    await db.songs.update_one(
                        {"title": db_title},
                        {"$set": {"is_verified": True, "last_updated": asyncio.get_event_loop().time()}}
                    )
                    print(f"✅ Verified: {db_title}")
                    # Remove from local cache to save resources
                    key = [k for k, v in unverified_cache.items() if v == db_title]
                    if key: del unverified_cache[key[0]]
                except:
                    pass

    print("🤖 Updater Bot is Live...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())