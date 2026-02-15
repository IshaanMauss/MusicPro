import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
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

# Use BOT_TOKEN_1 to match your Render Environment
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
    if not BOT_TOKEN or not API_ID or not API_HASH:
        logger.error("❌ CRITICAL ERROR: Environment Variables are missing.")
    else:
        logger.info(f"🤖 Starting Telegram Bot...")
        try:
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
async def get_songs(
    search: str = None, 
    genre: str = 'all', 
    mood: str = 'all', 
    listen: str = 'all', 
    limit: int = 100, 
    skip: int = 0
):
    # 1. Base Query: Only show songs that have a valid Telegram message mapping
    query = {"channel_message_id": {"$exists": True, "$ne": None}}
    
    # 2. Apply Search Filter (Title or Artist)
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"artist": {"$regex": search, "$options": "i"}}
        ]

    # 3. Apply Sidebar Filters (Genre, Mood, Duration)
    # Using regex for case-insensitive matching in case Atlas data varies
    if genre and genre != 'all':
        query["genre"] = {"$regex": f"^{genre}$", "$options": "i"}
        
    if mood and mood != 'all':
        # Check both field names commonly used in your JSON
        query["$or"] = [
            {"mood": {"$regex": f"^{mood}$", "$options": "i"}},
            {"moods": {"$regex": f"^{mood}$", "$options": "i"}}
        ]
        
    if listen and listen != 'all':
        # 'listen' from frontend maps to 'duration_category' in your database
        query["duration_category"] = {"$regex": f"^{listen}$", "$options": "i"}

    try:
        # 4. Execute Query with ORIGINAL IMPORT ORDER
        # .sort("_id", 1) ensures it follows the order of your mysongs.json
        cursor = db.songs.find(query).skip(skip).limit(limit).sort("_id", 1)
        songs = await cursor.to_list(length=limit)

        results = []
        for song in songs:
            # 5. Diagnostic ID Mapping
            # We map 'channel_message_id' to 'msg_id' so the stream route knows exactly 
            # which Telegram message to fetch.
            actual_telegram_id = song.get("channel_message_id")
            
            results.append({
                "id": str(song["_id"]),
                "title": song.get("title", "Unknown"),
                "artist": song.get("artist", "Unknown"),
                "album_art": song.get("album_art") or song.get("cover_url") or "",
                "duration": song.get("duration", 0),
                "duration_category": song.get("duration_category", "Mid"),
                "genre": song.get("genre", "all"),
                "mood": song.get("mood") or song.get("moods") or "all",
                "msg_id": actual_telegram_id, # THE CRITICAL KEY FOR PLAYBACK
                "is_playable": True
            })

        logger.info(f"✅ Fetched {len(results)} songs (Order: Original, Filter: {genre}/{mood}/{listen})")
        return {"results": results}

    except Exception as e:
        logger.error(f"❌ Database Query Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch songs from database")

@app.get("/stream/{msg_id}")
async def stream_song(msg_id: int):
    try:
        if not bot.is_connected():
             await bot.start(bot_token=BOT_TOKEN)

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