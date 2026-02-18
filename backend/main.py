import os
import logging
import re
import httpx  # 🟢 Required for Proxy Routes
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from bot_manager import BotManager 
from dotenv import load_dotenv

# 1. Setup & Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

manager = BotManager()
mongo_client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
DB_NAME = os.getenv("DB_NAME", "music_app_pro")
db = mongo_client[DB_NAME]

# --- LIFECYCLE MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🤖 System Starting... Initializing Bot Swarm...")
    await manager.start()
    yield
    print("🛑 System Shutting Down... Disconnecting Bots...")
    for worker in manager.workers:
        if worker.client.is_connected():
            await worker.client.disconnect()

app = FastAPI(lifespan=lifespan)

# --- CORS CONFIGURATION ---
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# 🧹 HELPER: Title Cleaner (Regex Engine)
def clean_title(title):
    if not title: return "Unknown Title"
    # Remove file extensions
    title = re.sub(r'\.(mp3|m4a|flac|wav)$', '', title, flags=re.IGNORECASE)
    
    # Remove common video noise
    patterns = [
        r'\(.*?official.*?video.*?\)',
        r'\[.*?official.*?video.*?\]',
        r'\(.*?lyric.*?video.*?\)',
        r'\[.*?video.*?\]',
        r'\(.*?audio.*?\)',
        r'\[.*?4k.*?\]',
        r'\|.*',       # Remove anything after a pipe |
        r'\d+kbps',    # Remove bitrates
        r'\(.*?\d{4}.*?\)' # Try to remove years in brackets if needed
    ]
    for p in patterns:
        title = re.sub(p, '', title, flags=re.IGNORECASE)
    
    return title.strip()

# --- PROXY ROUTES (FIXES CORS & 404s) ---

@app.get("/proxy/lyrics")
async def get_lyrics(artist: str, title: str):
    """
    Fetches lyrics from lyrics.ovh via backend to bypass CORS.
    """
    url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=5.0)
            if resp.status_code == 200:
                return resp.json()
            return {"lyrics": ""} 
        except Exception as e:
            logger.error(f"Lyrics Error: {e}")
            return {"lyrics": ""}

@app.get("/proxy/wiki")
async def get_wiki_info(query: str, fallback: str = None):
    """
    Fetches Wikipedia summary. Tries song specific query first, 
    falls back to Artist name if song page is 404.
    """
    async with httpx.AsyncClient() as client:
        try:
            # 1. Try specific Query (Song)
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"
            resp = await client.get(url, timeout=5.0)
            
            if resp.status_code == 200:
                return resp.json()
            
            # 2. If 404 and fallback provided, try Fallback (Artist)
            if fallback:
                print(f"Wiki 404 for '{query}', trying fallback '{fallback}'...")
                url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{fallback}"
                resp = await client.get(url, timeout=5.0)
                if resp.status_code == 200:
                    return resp.json()
                    
        except Exception as e:
            logger.error(f"Wiki Error: {e}")
            
    return {"extract": "No information available."}

# --- MAIN API ROUTES ---

@app.get("/songs")
async def get_songs(
    search: str = None, 
    genre: str = 'all', 
    mood: str = 'all', 
    listen: str = 'all',  # Duration Logic
    language: str = 'all', # 🟢 Language Logic
    limit: int = 100, 
    skip: int = 0
):
    print(f"\n📥 [API] Search='{search}' | Genre='{genre}' | Mood='{mood}' | Duration='{listen}' | Language='{language}'")

    # 1. Base Exclusion Logic
    query = {
        "is_hidden": {"$ne": True}, 
        "artist": {
            "$not": {
                "$regex": "various|unknown|unknown artist|va -", 
                "$options": "i"
            }
        }
    }
    
    # 2. Search Logic
    if search:
        search_terms = search.split()
        and_conditions = []
        for term in search_terms:
            regex = {"$regex": term, "$options": "i"}
            and_conditions.append({"$or": [{"title": regex}, {"artist": regex}]})
        
        if and_conditions:
            query["$and"] = and_conditions
    
    # 3. Filters
    if genre and genre.lower() != 'all':
        query["genre"] = {"$regex": genre, "$options": "i"}
        
    if mood and mood.lower() != 'all':
        query["mood"] = {"$regex": mood, "$options": "i"}

    # 🟢 Language Filter
    if language and language.lower() != 'all':
        query["language"] = {"$regex": language, "$options": "i"}
        
    # 🟢 Duration Filter
    if listen and listen.lower() != 'all':
        if listen == "Short":
            query["duration_seconds"] = {"$lt": 180} 
        elif listen == "Mid":
            query["duration_seconds"] = {"$gte": 180, "$lte": 300} 
        elif listen == "Long":
            query["duration_seconds"] = {"$gt": 300} 

    try:
        # Smart Sort: Genre > Title
        cursor = db.master_library.find(query).skip(skip).limit(limit).sort([("genre", 1), ("title", 1)])
        songs = await cursor.to_list(length=limit)

        results = []
        for song in songs:
            # Data Hygiene
            artist_name = song.get("artist") or "Unknown Artist"
            album_art = song.get("album_art")
            if not album_art or str(album_art).strip() == "":
                album_art = "https://placehold.co/300"

            final_title = clean_title(song.get("title"))

            results.append({
                "id": str(song["_id"]),
                "title": final_title,
                "artist": artist_name, 
                "album_art": album_art,
                "msg_id": song["_id"],
                "duration": song.get("duration", "0:00"), 
                "duration_seconds": song.get("duration_seconds", 0), 
                "genre": str(song.get("genre", "Unknown")),
                "mood": str(song.get("mood", "Unknown")),
                "language": str(song.get("language", "Unknown")), # 🟢 Return Language
                "is_playable": True
            })
        
        print(f"✅ [API] Returning {len(results)} songs.")
        return {"results": results}

    except Exception as e:
        logger.error(f"❌ DB Error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/stream/{msg_id}")
async def stream_song(msg_id: int):
    worker, message = await manager.get_audio_stream(msg_id)
    if not worker or not message:
        raise HTTPException(status_code=404, detail="File not found")

    async def iterfile():
        async for chunk in worker.client.iter_download(message.media):
            yield chunk

    filename = message.file.name if message.file else "audio.mp3"
    return StreamingResponse(
        iterfile(),
        media_type=message.file.mime_type or "audio/mpeg",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)