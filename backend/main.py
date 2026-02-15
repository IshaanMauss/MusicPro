import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

# Configuration
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "music_app_pro")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Database
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Initialize Client
bot = TelegramClient('bot_session', int(API_ID) if API_ID else 0, API_HASH)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # CRITICAL: Prevent EOFError by checking token before starting
    if not BOT_TOKEN or not API_ID or not API_HASH:
        print("❌ ERROR: Missing Environment Variables (BOT_TOKEN, API_ID, or API_HASH)")
    else:
        print(f"🤖 Starting Bot with token: {BOT_TOKEN[:5]}***")
        try:
            # We pass the token directly to avoid the interactive prompt
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
        message = await bot.get_messages(None, ids=msg_id)
        if not message or not message.media:
            raise HTTPException(status_code=404, detail="File not found")

        async def iterfile():
            async for chunk in bot.iter_download(message.media):
                yield chunk

        return StreamingResponse(iterfile(), media_type=message.file.mime_type)
    except Exception as e:
        print(f"🔥 Streaming Error: {e}")
        raise HTTPException(status_code=500, detail="Stream failed")

@app.get("/")
async def root():
    return {"message": "Music Backend Live"}