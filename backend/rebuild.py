import asyncio
from telethon import TelegramClient
from motor.motor_asyncio import AsyncIOMotorClient

# 1. HARDCODED SETTINGS (Bypasses all .env issues)
MONGO_URL = "mongodb+srv://ishaanchaturvedi444_db_user:DAsKXeTIZk2axyOD@cluster0.6hjkisc.mongodb.net/music_app_pro?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "music_app_pro"
API_ID = 30469270
API_HASH = "82c990aeeded3551c9e37f6c57520c1c"
CHANNEL_ID = -1003681118965

async def atomic_rebuild():
    print("🧨 CONNECTING FOR ATOMIC REBUILD...")
    tg_client = TelegramClient('user_session', API_ID, API_HASH)
    await tg_client.start()
    
    db_client = AsyncIOMotorClient(MONGO_URL)
    db = db_client[DB_NAME]
    col = db["master_library"]

    # --- STEP 1: THE HARD WIPE ---
    print("🔥 DROPPING COLLECTION 'master_library'...")
    await col.drop() 
    
    # --- STEP 2: SCAN TELEGRAM ---
    print("📡 SCANNING TELEGRAM FOR REAL FILES...")
    new_docs = []
    async for message in tg_client.iter_messages(CHANNEL_ID):
        if message.file and message.file.name:
            # Clean name logic
            name = message.file.name.rsplit('.', 1)[0]
            if '-' in name:
                parts = name.rsplit('-', 1)
                if len(parts[-1]) == 11: name = "-".join(parts[:-1])
            clean_name = name.replace('_', ' ').replace('-', ' ').strip()

            new_docs.append({
                "_id": message.id, # Real Telegram ID
                "title": clean_name,
                "msg_id": message.id,
                "artist": "Unknown",
                "album_art": "https://placehold.co/300",
                "is_playable": True
            })

    # --- STEP 3: REBUILD ---
    if new_docs:
        print(f"📦 FOUND {len(new_docs)} REAL FILES. INSERTING...")
        await col.insert_many(new_docs)
        
        # --- STEP 4: VERIFY ---
        check_ghost = await col.find_one({"_id": 4})
        if check_ghost:
            print(f"❌ ERROR: ID 4 still exists as '{check_ghost['title']}'!")
        else:
            print("✅ SUCCESS: The Ghost of ID 4 is dead.")

if __name__ == "__main__":
    asyncio.run(atomic_rebuild())