import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient
from dotenv import load_dotenv

# 1. Load Local .env
load_dotenv()

# --- 🔍 DEBUG: PRINT ALL KEYS (Hidden) ---
print("\n🔍 --- ENVIRONMENT DIAGNOSTIC ---")
# We loop through all keys to find "close matches" in case of typos
for key, value in os.environ.items():
    if "API" in key or "TOKEN" in key or "MONGO" in key:
        # Hide the actual secret, just show length and spaces
        safe_val = value[:5] + "..." if value else "EMPTY"
        print(f"👉 FOUND KEY: '{key}' (Length: {len(key)}) -> VALUE: {safe_val}")
print("----------------------------------\n")

# 2. Robust Variable Loading (Strips spaces)
MONGO_URL = os.getenv("MONGO_URL", "").strip()
DB_NAME = os.getenv("DB_NAME", "music_app_pro").strip()

# Try to find API_ID even if it has accidental spaces
API_ID = os.getenv("API_ID", "").strip()
if not API_ID:
    # Fallback: Look for keys that look like API_ID
    for k in os.environ:
        if k.strip() == "API_ID":
            API_ID = os.environ[k].strip()

API_HASH = os.getenv("API_HASH", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# 3. Database
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# 4. Bot Setup
try:
    real_api_id = int(API_ID)
except ValueError:
    print(f"❌ API_ID ERROR: '{API_ID}' is not a number!")
    real_api_id = 0

bot = TelegramClient('bot_session', real_api_id, API_HASH)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not BOT_TOKEN or not API_ID or not API_HASH:
        print("❌ CRITICAL: Variables still missing. Check the 'DIAGNOSTIC' logs above.")
    else:
        print("🤖 Starting Telegram Bot...")
        try:
            # Pass token directly to avoid input prompt
            await bot.start(bot_token=BOT_TOKEN)
            print("✅ Bot Connected Successfully!")
        except Exception as e:
            print(f"🔥 Bot Connection Failed: {e}")
    yield
    if bot.is_connected():
        await bot.disconnect()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/songs")
async def get_songs(search: str = None, limit: int = 50, skip: int = 0):
    query = {"channel_message_id": {"$exists": True, "$ne": None}}
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"artist": {"$regex": search, "$options": "i"}}
        ]
    cursor = db.songs.find(query).skip(skip).limit(limit).sort("_id", -1)
    songs = await cursor.to_list(length=limit)
    
    results = []
    for song in songs:
        results.append({
            "id": str(song["_id"]),
            "title": song.get("title", "Unknown"),
            "artist": song.get("artist", "Unknown"),
            "album_art": song.get("album_art") or song.get("cover_url") or "",
            "duration": song.get("duration", 0),
            "msg_id": song.get("channel_message_id"), 
            "is_playable": True
        })
    return {"results": results}

@app.get("/stream/{msg_id}")
async def stream_song(msg_id: int):
    try:
        if not bot.is_connected():
             await bot.start(bot_token=BOT_TOKEN)
             
        message = await bot.get_messages(None, ids=msg_id)
        if not message or not message.media:
            raise HTTPException(status_code=404, detail="File not found")

        async def iterfile():
            async for chunk in bot.iter_download(message.media):
                yield chunk
        
        return StreamingResponse(iterfile(), media_type=message.file.mime_type)
    except Exception as e:
        print(f"Streaming Error: {e}")
        raise HTTPException(status_code=500, detail="Stream failed")

@app.get("/")
async def root():
    return {"message": "Music Backend Live"}