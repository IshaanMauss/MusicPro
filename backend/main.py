import os
import logging
import re
import httpx
import jwt
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from bot_manager import BotManager 
from dotenv import load_dotenv

# 1. Setup & Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

# --- AUTH CONFIGURATION ---
# 🟢 Logic: Prioritize the secret from Render environment; fallback only for local dev
# --- SECURE AUTH CONFIGURATION ---
# Logic: Only pull from the environment. No hardcoded fallback.
SECRET_KEY = os.getenv("JWT_SECRET")

if not SECRET_KEY:
    # This will show up in your Render logs if you forgot to add the variable
    logger.error("❌ CRITICAL: JWT_SECRET not found in environment variables!")
    # In production, it is safer to raise an error than to use a weak default
    raise RuntimeError("JWT_SECRET must be set in environment variables")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

# Using pbkdf2_sha256 for Python 3.13 stability
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

manager = BotManager()
mongo_client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
DB_NAME = os.getenv("DB_NAME", "music_app_pro")
db = mongo_client[DB_NAME]

# --- SCHEMAS ---
class UserAuth(BaseModel):
    username: str
    password: str

class UserStateSync(BaseModel):
    liked_songs: List[dict] = []
    current_song: Optional[dict] = None
    volume: float = 0.7
    selected_language: str = "all"

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

# --- 100% LOGICAL PRODUCTION CORS FIX ---
# This resolves the '400 Bad Request' on OPTIONS by explicitly allowing the production origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://music-app-backend-twia.onrender.com",
        "https://vibestream.onrender.com" # 🟢 Add your actual frontend URL here
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# --- AUTH HELPERS ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# 🧹 HELPER: Title Cleaner (Preserved)
def clean_title(title):
    if not title: return "Unknown Title"
    title = re.sub(r'\.(mp3|m4a|flac|wav)$', '', title, flags=re.IGNORECASE)
    patterns = [
        r'\(.*?official.*?video.*?\)', r'\[.*?official.*?video.*?\]',
        r'\(.*?lyric.*?video.*?\)', r'\[.*?video.*?\]',
        r'\(.*?audio.*?\)', r'\[.*?4k.*?\]', r'\|.*', r'\d+kbps',
        r'\(.*?\d{4}.*?\)'
    ]
    for p in patterns:
        title = re.sub(p, '', title, flags=re.IGNORECASE)
    return title.strip()

# --- AUTH ROUTES ---
@app.post("/auth/register")
async def register(user: UserAuth):
    existing = await db.users.find_one({"username": user.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed_password = pwd_context.hash(user.password)
    new_user = {
        "username": user.username,
        "password": hashed_password,
        "state": UserStateSync().dict(),
        "created_at": datetime.utcnow()
    }
    await db.users.insert_one(new_user)
    return {"msg": "Registration successful"}

@app.post("/auth/login")
async def login(user: UserAuth):
    db_user = await db.users.find_one({"username": user.username})
    if not db_user or not pwd_context.verify(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "username": user.username,
        "state": db_user.get("state")
    }

# --- USER SYNC ROUTE ---
@app.post("/user/sync")
async def sync_state(state: UserStateSync, username: str = Depends(get_current_user)):
    try:
        await db.users.update_one(
            {"username": username},
            {"$set": {"state": state.dict()}}
        )
        return {"msg": "Sync successful"}
    except Exception as e:
        logger.error(f"Sync Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync user data")

# --- PROXY ROUTES (Preserved) ---
@app.get("/proxy/lyrics")
async def get_lyrics(artist: str, title: str):
    url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=5.0)
            return resp.json() if resp.status_code == 200 else {"lyrics": ""}
        except Exception:
            return {"lyrics": ""}

@app.get("/proxy/wiki")
async def get_wiki_info(query: str, fallback: str = None):
    async with httpx.AsyncClient() as client:
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"
            resp = await client.get(url, timeout=5.0)
            if resp.status_code == 200: return resp.json()
            if fallback:
                url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{fallback}"
                resp = await client.get(url, timeout=5.0)
                if resp.status_code == 200: return resp.json()
        except Exception:
            pass
    return {"extract": "No information available."}

# --- MAIN API ROUTES (Preserved) ---
@app.get("/songs")
async def get_songs(
    search: str = None, 
    genre: str = 'all', 
    mood: str = 'all', 
    listen: str = 'all', 
    language: str = 'all',
    limit: int = 100, 
    skip: int = 0
):
    query = {
        "is_hidden": {"$ne": True}, 
        "artist": {"$not": {"$regex": "various|unknown|va -", "$options": "i"}}
    }
    
    if search:
        search_terms = search.split()
        and_conditions = []
        for term in search_terms:
            regex = {"$regex": term, "$options": "i"}
            and_conditions.append({"$or": [{"title": regex}, {"artist": regex}]})
        query["$and"] = and_conditions
    
    if genre and genre.lower() != 'all': query["genre"] = {"$regex": genre, "$options": "i"}
    if mood and mood.lower() != 'all': query["mood"] = {"$regex": mood, "$options": "i"}
    if language and language.lower() != 'all': query["language"] = {"$regex": language, "$options": "i"}
    
    if listen and listen.lower() != 'all':
        if listen == "Short": query["duration_seconds"] = {"$lt": 180}
        elif listen == "Mid": query["duration_seconds"] = {"$gte": 180, "$lte": 300}
        elif listen == "Long": query["duration_seconds"] = {"$gt": 300}

    try:
        cursor = db.master_library.find(query).skip(skip).limit(limit).sort([("genre", 1), ("title", 1)])
        songs = await cursor.to_list(length=limit)
        results = []
        for song in songs:
            results.append({
                "id": str(song["_id"]),
                "title": clean_title(song.get("title")),
                "artist": song.get("artist") or "Unknown Artist", 
                "album_art": song.get("album_art") or "https://placehold.co/300",
                "msg_id": song["_id"],
                "duration": song.get("duration", "0:00"), 
                "duration_seconds": song.get("duration_seconds", 0), 
                "genre": str(song.get("genre", "Unknown")),
                "mood": str(song.get("mood", "Unknown")),
                "language": str(song.get("language", "Unknown")),
                "is_playable": True
            })
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
    return StreamingResponse(iterfile(), media_type=message.file.mime_type or "audio/mpeg")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)