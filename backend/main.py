import os
import mimetypes
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient
from dotenv import load_dotenv
from bson import ObjectId

# 1. Load Environment Variables
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "music_app_pro")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 2. App & Database Setup
app = FastAPI()

# Enable CORS so your Frontend can talk to this Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (Github Pages, Vercel, Localhost)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to MongoDB Atlas
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# 3. Telethon (Telegram) Client Setup for Streaming
# We use a 'bot' session to fetch files faster
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ---------------------------------------------------------
# 🔍 SEARCH ROUTE (Strictly Database Only)
# ---------------------------------------------------------
@app.get("/songs")
async def get_songs(
    search: str = None, 
    limit: int = 50, 
    skip: int = 0
):
    """
    Searches YOUR 10k imported songs in MongoDB.
    No YouTube. No External APIs. Just your data.
    """
    query = {}
    
    # If user types in search bar, filter by Title OR Artist (Case Insensitive)
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

    # Format for Frontend
    results = []
    for song in songs:
        results.append({
            "id": str(song["_id"]),
            "title": song.get("title", "Unknown Title"),
            "artist": song.get("artist", "Unknown Artist"),
            # Ensure this matches your JSON field (some use 'Cover_Image' or 'album_art')
            "album_art": song.get("album_art") or song.get("Cover_Image") or "",
            "duration": song.get("duration", "0:00"),
            "msg_id": song.get("msg_id"), # CRITICAL: This is needed to play the song
            "is_playable": True
        })
    
    return {"results": results}

# ---------------------------------------------------------
# 🎧 STREAMING ROUTE (The Engine)
# ---------------------------------------------------------
@app.get("/stream/{msg_id}")
async def stream_song(msg_id: int):
    """
    Streams the audio file directly from Telegram using the msg_id.
    """
    try:
        # Get the message from your Storage Channel (You might need to specify channel ID if ambiguous)
        # Assuming the bot can see the message in the chat it was forwarded to.
        # If your songs are in a specific channel, replace 'me' with that Channel ID.
        message = await bot.get_messages(None, ids=msg_id)
        
        if not message or not message.media:
            raise HTTPException(status_code=404, detail="Audio file not found on Telegram")

        # Generator function to stream chunks
        async def iterfile():
            async for chunk in bot.iter_download(message.media):
                yield chunk

        # Set headers so browser knows it's an audio file
        headers = {
            "Content-Disposition": f'inline; filename="{message.file.name or "audio.mp3"}"',
            "Content-Type": message.file.mime_type or "audio/mpeg",
        }
        
        return StreamingResponse(iterfile(), headers=headers, media_type=message.file.mime_type)

    except Exception as e:
        print(f"Streaming Error: {e}")
        raise HTTPException(status_code=500, detail="Could not stream song")

# ---------------------------------------------------------
# 🔐 AUTH ROUTE (Include this if you have the file)
# ---------------------------------------------------------
# from routes.auth_routes import router as auth_router
# app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

@app.get("/")
async def root():
    return {"message": "Music App Backend is Live & Connected to Atlas!"}