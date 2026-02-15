import uvicorn
import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Import your sanitized BotManager
from bot_manager import BotManager 

# 🟢 Load Vault (Environment Variables)
load_dotenv()

# --- CONFIGURATION ---
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "music_app_pro")

# Initialize MongoDB Client
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client[DB_NAME]

# Initialize Bot Swarm Manager
bot_manager = BotManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles system startup and shutdown events."""
    print("🤖 Starting Bot Swarm Swarm...")
    await bot_manager.start()
    yield
    print("🛑 Shutting down Bot Swarm Swarm...")

# Create FastAPI App instance
app = FastAPI(lifespan=lifespan, title="MusicAppPro API")

# --- MIDDLEWARE ---
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
    limit: int = 50, 
    skip: int = 0, 
    search: str = "", 
    genre: str = "all", 
    mood: str = "all", 
    listen: str = "all"
):
    """Fetches songs from MongoDB with advanced filtering and search."""
    query = {}
    
    # 1. Search Logic (Title or Artist)
    if search and search.strip():
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"artist": {"$regex": search, "$options": "i"}}
        ]
    
    # 2. Filter Logic
    if genre != "all":
        query["genre"] = genre
    if mood != "all":
        query["moods"] = mood
    if listen != "all":
        query["duration_category"] = listen

    cursor = db.songs.find(query).skip(skip).limit(limit)
    songs = []
    
    async for song in cursor:
        songs.append({
            "id": str(song["_id"]),
            "title": song.get("title", "Unknown"),
            "artist": song.get("artist") or "Unknown Artist",
            "album_art": song.get("album_art") or song.get("cover_url") or "https://placehold.co/300x300/1a1a1a/FFF?text=Music",
            "msg_id": song.get("channel_message_id"),
            "is_playable": True,
            "duration": song.get("duration", 0),
            "duration_category": song.get("duration_category", "Mid")
        })
        
    return {"results": songs}

@app.get("/stream/{message_id}")
async def stream_audio(message_id: int):
    """Streams audio data directly from Telegram through a healthy bot."""
    # Select an available worker from the swarm
    worker, message = await bot_manager.get_audio_stream(message_id)
    
    if not worker or not message:
        raise HTTPException(status_code=404, detail="Song not found or bots busy")

    async def audio_generator():
        try:
            # Iteratively download and yield chunks for real-time streaming
            async for chunk in worker.client.iter_download(message.media):
                yield chunk
        except Exception as e:
            print(f"Stream interrupted: {e}")

    file_name = message.file.name if message.file.name else "audio.mp3"
    mime_type = message.file.mime_type if message.file.mime_type else "audio/mpeg"

    return StreamingResponse(
        audio_generator(),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{file_name}"',
            "Accept-Ranges": "bytes"
        }
    )

# --- SERVER ENTRY POINT ---
if __name__ == "__main__":
    # Image of FastAPI architecture showing the Uvicorn server handling requests
    
    print(f"📡 MusicAppPro API is live on http://localhost:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)