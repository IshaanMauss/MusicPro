import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def get_clean_env(key, default=None):
    val = os.getenv(key, default)
    if val:
        return val.strip()
    return val

MONGO_URL = get_clean_env("MONGO_URL")
DB_NAME = get_clean_env("DB_NAME", "music_app_pro")
API_ID = get_clean_env("API_ID")
API_HASH = get_clean_env("API_HASH")

# 🟢 FIX: We look for 'BOT_TOKEN_1' first, because that is what is in your logs
BOT_TOKEN = get_clean_env("BOT_TOKEN_1") or get_clean_env("BOT_TOKEN")

# Initialize Database
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Initialize Bot (Safe Mode)
try:
    real_api_id = int(API_ID) if API_ID else 0
except:
    real_api_id = 0

bot = TelegramClient('bot_session', real_api_id, API_HASH or "empty_hash")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # CRITICAL CHECK
    if not BOT_TOKEN or not API_ID or not API_HASH:
        logger.error("❌ CRITICAL ERROR: 'BOT_TOKEN_1' (or API_ID/HASH) is missing.")
    else:
        logger.info(f"🤖 Starting Telegram Bot using token starting with {BOT_TOKEN[:5]}...")
        try:
            # Force login with the found token
            await bot.start(bot_token=BOT_TOKEN)
            logger.info("✅ Bot Connected Successfully!")
        except Exception as e:
            logger.error(f"🔥 Bot Failed to Start: {e}")
            
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

# --- ROUTES ---

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
        # Emergency Reconnect
        if not bot.is_connected():
             if BOT_TOKEN:
                 await bot.start(bot_token=BOT_TOKEN)
             else:
                 raise HTTPException(status_code=500, detail="Server Configuration Error")

        message = await bot.get_messages(None, ids=msg_id)
        if not message or not message.media:
            raise HTTPException(status_code=404, detail="Audio file not found")

        async def iterfile():
            async for chunk in bot.iter_download(message.media):
                yield chunk

        fname = message.file.name if message.file else "audio.mp3"
        mtype = message.file.mime_type if message.file else "audio/mpeg"
        
        return StreamingResponse(iterfile(), headers={
            "Content-Disposition": f'inline; filename="{fname}"'
        }, media_type=mtype)

    except Exception as e:
        logger.error(f"Streaming Error: {e}")
        raise HTTPException(status_code=500, detail="Stream failed")

@app.get("/")
async def root():
    return {"message": "Music App Backend is Live"}