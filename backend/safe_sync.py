import os
import asyncio
import re
from telethon import TelegramClient
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import InsertOne
from dotenv import load_dotenv

load_dotenv()

CHANNEL_ID = -1003681118965 
client = TelegramClient('user_session', int(os.getenv("API_ID")), os.getenv("API_HASH"))

def clean(s):
    # Removes everything except alphanumeric characters
    return re.sub(r'[^a-zA-Z0-9]', '', str(s)).lower().strip()

async def safe_rebuild():
    print("📡 Connecting...")
    await client.start()
    db = AsyncIOMotorClient(os.getenv("MONGO_URL"))[os.getenv("DB_NAME")]
    
    print("📥 Loading Metadata into RAM...")
    all_songs = await db.songs.find({}).to_list(length=15000)
    
    # 💡 Optimization: We store songs by their first "Clean Word" to speed up fuzzy matching
    meta_dict = {}
    for s in all_songs:
        title = s.get('title', '')
        words = title.split()
        if words:
            first_word = clean(words[0])
            if first_word not in meta_dict:
                meta_dict[first_word] = []
            meta_dict[first_word].append(s)

    master = db["master_library"]
    await master.delete_many({})
    
    print("🚀 Matching with Fuzzy Logic (Keyword Anchoring)...")
    bulk_ops = []
    scanned = 0
    matched = 0

    async for message in client.iter_messages(CHANNEL_ID, limit=15000):
        scanned += 1
        if scanned % 500 == 0: print(f"📡 Progress: Scanned {scanned}...")

        if message.file and message.file.name:
            tg_name = message.file.name.rsplit('.', 1)[0]
            tg_words = tg_name.split()
            if not tg_words: continue
            
            first_word_tg = clean(tg_words[0])
            potential_matches = meta_dict.get(first_word_tg, [])

            # Fuzzy Match Check
            for match in potential_matches:
                db_title_clean = clean(match['title'])
                tg_title_clean = clean(tg_name)
                
                # If DB title is inside TG name or vice versa
                if db_title_clean in tg_title_clean or tg_title_clean in db_title_clean:
                    new_doc = {
                        "_id": message.id,
                        "title": match['title'],
                        "artist": match.get('artist', 'Unknown'),
                        "album_art": match.get('album_art') or match.get('cover_url'),
                        "genre": match.get('genre', []),
                        "msg_id": message.id,
                        "is_verified": True
                    }
                    bulk_ops.append(InsertOne(new_doc))
                    matched += 1
                    break

    if bulk_ops:
        print(f"💾 Saving {len(bulk_ops)} accurate matches to Atlas...")
        await master.bulk_write(bulk_ops)
        print("✨ SUCCESS!")
    else:
        print("❌ Still no matches. Check naming convention.")

if __name__ == "__main__":
    asyncio.run(safe_rebuild())