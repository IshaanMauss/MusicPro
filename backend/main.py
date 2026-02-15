import os
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

# 2. App & Database Setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# 3. Telethon Client (Bot Mode)
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ---------------------------------------------------------
# 🔍 SEARCH ROUTE (Fixed for your DB Keys)
# ---------------------------------------------------------
@app.get("/songs")
async def get_songs(search: str = None, limit: int = 50, skip: int = 0):
    """
    Fetches songs from Atlas.
    CRITICAL FIX: Maps 'channel_message_id' -> 'msg_id' so the player works.
    """
    query = {}
    if search:
        query = {
            "$or": [
                {"title": {"$regex": search, "$options": "i"}},
                {"artist": {"$regex": search, "$options": "i"}}
            ]
        }

    # Fetch from DB (Sorted by newest first)
    cursor = db.songs.find(query).skip(skip).limit(limit).sort("_id", -1)
    songs = await cursor.to_list(length=limit)

    results = []
    for song in songs:
        results.append({
            "id": str(song["_id"]),
            "title": song.get("title", "Unknown Title"),
            "artist": song.get("artist", "Unknown Artist"),
            
            # FIX 1: Checks both 'album_art' and 'cover_url' (based on your debug logs)
            "album_art": song.get("album_art") or song.get("cover_url") or "",
            
            "duration": song.get("duration", 0),
            "duration_category": song.get("duration_category", "Unknown"),
            
            # FIX 2: CRITICAL! Maps your DB's 'channel_message_id' to 'msg_id'
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
        # We use the ID passed from the frontend (which is the mapped channel_message_id)
        message = await bot.get_messages(None, ids=msg_id)
        
        if not message or not message.media:
            raise HTTPException(status_code=404, detail="Audio file not found on Telegram")

        async def iterfile():
            async for chunk in bot.iter_download(message.media):
                yield chunk

        headers = {
            "Content-Disposition": f'inline; filename="{message.file.name or "audio.mp3"}"',
            "Content-Type": message.file.mime_type or "audio/mpeg",
        }
        
        return StreamingResponse(iterfile(), headers=headers, media_type=message.file.mime_type)

    except Exception as e:
        print(f"Streaming Error: {e}")
        raise HTTPException(status_code=500, detail="Could not stream song")

@app.get("/")
async def root():
    return {"message": "Music App Backend is Live!"}