import motor.motor_asyncio
import os
from dotenv import load_dotenv

# 🟢 Load environment variables
load_dotenv()

# 🟢 Pull values from .env with fallbacks
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "music_app_pro")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)

# 🟢 Select the Database using the dynamic name
db = client[DB_NAME]

# 🟢 Select the Collection
songs_collection = db.songs

def song_helper(song) -> dict:
    return {
        "id": str(song["_id"]),
        "title": song.get("title"),
        "artist": song.get("artist"),
        "cover_url": song.get("cover_url"),
        "video_id": song.get("video_id"),
        "telegram_file_id": song.get("telegram_file_id"),
        "genre": song.get("genre")[0] if isinstance(song.get("genre"), list) else song.get("genre", "all"),
        "listen": song.get("listen", "all")
    }