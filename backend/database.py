import motor.motor_asyncio
import os
from dotenv import load_dotenv

# 🟢 Load environment variables
load_dotenv()

# 🟢 Pull values from .env with fallbacks
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "music_app_pro")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)

# 🟢 Select the Database
db = client[DB_NAME]

# 🔴 CHANGE THIS: Point to the rebuilt collection
songs_collection = db.master_library 

def song_helper(song) -> dict:
    return {
        "id": str(song["_id"]),
        "title": song.get("title"),
        "artist": song.get("artist", "Unknown"),
        "album_art": song.get("album_art", "https://placehold.co/300"), # Match your rebuild schema
        "msg_id": song.get("msg_id"), # Crucial for your streaming logic
        "genre": song.get("genre")[0] if isinstance(song.get("genre"), list) else song.get("genre", "all"),
        "mood": song.get("mood", "all"),
        "is_playable": song.get("is_playable", True)
    }