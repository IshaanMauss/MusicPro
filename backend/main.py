import os
import logging
import re
import httpx
import jwt
import asyncio
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

# 1. Setup & Configuration with Verbose Debugging
logging.basicConfig(
    level=logging.DEBUG, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
load_dotenv()

# --- AUTH CONFIGURATION ---
SECRET_KEY = os.getenv("JWT_SECRET")

if not SECRET_KEY:
    logger.critical("❌ CRITICAL: JWT_SECRET not found in environment variables!")
    raise RuntimeError("JWT_SECRET must be set in environment variables")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Initialize Global Managers
manager = BotManager()
MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    logger.error("❌ MONGO_URL missing from environment")

mongo_client = AsyncIOMotorClient(MONGO_URL)
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

# --- 🚀 100% LOGICAL LIFECYCLE (BACKGROUND INIT) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🤖 System Init: Starting FastAPI...")
    
    # 🟢 LOGICAL FIX: Start Telegram Bots in background to avoid Render Port-Binding Timeout
    logger.debug("📡 Scheduling Bot Swarm initialization in background...")
    bot_task = asyncio.create_task(manager.start())
    
    yield
    
    logger.info("🛑 System Shutdown: Cleaning up background tasks and connections...")
    bot_task.cancel()
    try:
        for worker in manager.workers:
            if worker.client and worker.client.is_connected():
                await worker.client.disconnect()
        logger.debug("✅ All bots disconnected successfully.")
    except Exception as e:
        logger.error(f"⚠️ Error during shutdown cleanup: {e}")

app = FastAPI(lifespan=lifespan)

# --- 🛠️ ROBUST PRODUCTION CORS CONFIG ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://vibestream.onrender.com", 
        "https://music-app-backend-twia.onrender.com",
        "*" # Wildcard for safety during deployment testing
    ],
    allow_credentials=True, 
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    expose_headers=["*"],
)

# --- AUTH HELPERS ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    logger.debug("🔐 Verifying JWT Access Token...")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("🚫 Token validation failed: Missing sub")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except jwt.PyJWTError as e:
        logger.error(f"🚫 JWT Decode Error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

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

# --- ROUTES ---

@app.post("/auth/register")
async def register(user: UserAuth):
    logger.info(f"📝 Registration request for: {user.username}")
    existing = await db.users.find_one({"username": user.username})
    if existing:
        logger.warning(f"⚠️ Registration failed: {user.username} already exists")
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed_password = pwd_context.hash(user.password)
    new_user = {
        "username": user.username,
        "password": hashed_password,
        "state": UserStateSync().dict(),
        "created_at": datetime.utcnow()
    }
    await db.users.insert_one(new_user)
    logger.info(f"✅ User {user.username} registered successfully")
    return {"msg": "Registration successful"}

@app.post("/auth/login")
async def login(user: UserAuth):
    logger.info(f"🔑 Login attempt for: {user.username}")
    db_user = await db.users.find_one({"username": user.username})
    if not db_user or not pwd_context.verify(user.password, db_user["password"]):
        logger.warning(f"🚫 Invalid login for: {user.username}")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = create_access_token(data={"sub": user.username})
    logger.info(f"✅ User {user.username} logged in")
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "username": user.username,
        "state": db_user.get("state")
    }

@app.post("/user/sync")
async def sync_state(state: UserStateSync, username: str = Depends(get_current_user)):
    logger.debug(f"🔄 Syncing state for user: {username}")
    try:
        await db.users.update_one(
            {"username": username},
            {"$set": {"state": state.dict()}}
        )
        return {"msg": "Sync successful"}
    except Exception as e:
        logger.error(f"❌ Sync Error for {username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync user data")

@app.get("/songs")
async def get_songs(
    search: str = None, genre: str = 'all', mood: str = 'all', 
    listen: str = 'all', language: str = 'all', limit: int = 100, skip: int = 0
):
    logger.debug(f"🎵 Fetching songs. Filter: Genre={genre}, Language={language}, Search={search}")
    query = {
        "is_hidden": {"$ne": True}, 
        "artist": {"$not": {"$regex": "various|unknown|va -", "$options": "i"}}
    }
    
    if search:
        search_terms = search.split()
        and_conditions = [{"$or": [{"title": {"$regex": term, "$options": "i"}}, {"artist": {"$regex": term, "$options": "i"}}]} for term in search_terms]
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
        results = [{
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
        } for song in songs]
        return {"results": results}
    except Exception as e:
        logger.error(f"❌ DB Fetch Error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/stream/{msg_id}")
async def stream_song(msg_id: int):
    logger.info(f"🔊 Stream request for ID: {msg_id}")
    worker, message = await manager.get_audio_stream(msg_id)
    if not worker or not message:
        logger.warning(f"❌ Audio file not found for ID: {msg_id}")
        raise HTTPException(status_code=404, detail="File not found")
    
    async def iterfile():
        async for chunk in worker.client.iter_download(message.media):
            yield chunk
    
    return StreamingResponse(iterfile(), media_type=message.file.mime_type or "audio/mpeg")

if __name__ == "__main__":
    import uvicorn
    # Render uses 'PORT' environment variable
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting Uvicorn on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)