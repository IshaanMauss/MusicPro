import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "music_app_pro")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 2. Database Setup
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# 3. Initialize Bot (But don't start it yet!)
bot = TelegramClient('bot_session', API_ID, API_HASH)

# 4. LIFESPAN MANAGER (The Fix for the "Coroutine" Error)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🤖 Starting Telegram Bot...")
    await bot.start(bot_token=BOT_TOKEN)
    print("✅ Bot Connected Successfully!")
    yield
    print("🛑 Stopping Bot...")
    await bot.disconnect()

# 5. Create App with Lifespan
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# 🔍 SEARCH ROUTE
# ---------------------------------------------------------
@app.get("/songs")
async def get_songs(search: str = None, limit: int = 50, skip: int = 0):
    query = {
        "channel_message_id": {"$exists": True, "$ne": None}
    }
    
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
            "title": song.get("title", "Unknown Title"),
            "artist": song.get("artist", "Unknown Artist"),
            "album_art": song.get("album_art") or song.get("cover_url") or song.get("Cover_Image") or "",
            "duration": song.get("duration", 0),
            "msg_id": song.get("channel_message_id"), 
            "is_playable": True
        })
    
    return {"results": results}

# ---------------------------------------------------------
# 🎧 STREAMING ROUTE
# ---------------------------------------------------------
@app.get("/stream/{msg_id}")
async def stream_song(msg_id: int):
    try:
        # Use the bot to get the message
        # Since we awaited start() in lifespan, 'bot' is now a ready client, not a coroutine.
        message = await bot.get_messages(None, ids=msg_id)
        
        if not message or not message.media:
            print(f"❌ Error: Message {msg_id} not found or has no audio.")
            raise HTTPException(status_code=404, detail="Audio file not found on Telegram")

        async def iterfile():
            async for chunk in bot.iter_download(message.media):
                yield chunk

        fname = message.file.name if message.file else "audio.mp3"
        mtype = message.file.mime_type if message.file else "audio/mpeg"

        headers = {
            "Content-Disposition": f'inline; filename="{fname}"',
            "Content-Type": mtype,
        }
        
        return StreamingResponse(iterfile(), headers=headers, media_type=mtype)

    except Exception as e:
        print(f"🔥 Streaming Error: {e}")
        raise HTTPException(status_code=500, detail="Could not stream song")

@app.get("/")
async def root():
    return {"message": "Music App Backend is Live!"}