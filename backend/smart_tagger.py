import asyncio
import re
import aiohttp
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import sys

# 🟢 Load environment variables
load_dotenv()

# --- DYNAMIC CONFIGURATION ---
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "music_app_pro")
ITUNES_API = "https://itunes.apple.com/search"

# Cleaning Regex patterns
CLEAN_PATTERNS = [
    r"\(.*?\)",           # Remove content in brackets ()
    r"\[.*?\]",           # Remove content in brackets []
    r"\.mp3|\.m4a|\.wav", # Remove extensions
    r"official video",
    r"lyrics",
    r"ft\.",
    r"feat\.",
    r"with lyrics",
    r"128kbps",
    r"320kbps",
    r"_"                  # Replace underscores
]

def clean_title(title):
    clean = title.lower()
    for pattern in CLEAN_PATTERNS:
        clean = re.sub(pattern, " ", clean)
    return clean.strip()

def get_duration_category(milliseconds):
    if not milliseconds: return "Mid"
    try:
        sec = int(milliseconds) / 1000
        if sec < 180: return "Short"    # < 3 mins
        if sec < 300: return "Mid"      # 3-5 mins
        return "Long"                   # > 5 mins
    except:
        return "Mid"

async def fetch_metadata(session, title):
    """Hits iTunes API to get clean Artist, Genre, and Album Art."""
    term = clean_title(title)
    try:
        async with session.get(ITUNES_API, params={"term": term, "limit": 1, "media": "music"}) as resp:
            data = await resp.json()
            if data["resultCount"] > 0:
                result = data["results"][0]
                return {
                    "artist": result.get("artistName"),
                    "genre": result.get("primaryGenreName"),
                    "album_art": result.get("artworkUrl100").replace("100x100", "600x600"),
                    "duration_ms": result.get("trackTimeMillis")
                }
    except:
        pass
    return None

async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db.songs

    # Only process songs that haven't been enriched yet
    songs_to_tag = collection.find({"is_enriched": {"$ne": True}})
    total_found = await collection.count_documents({"is_enriched": {"$ne": True}})
    
    if total_found == 0:
        print("✅ All songs are already enriched.")
        return

    print(f"🚀 Starting Smart Tagger for {total_found} songs...")
    
    async with aiohttp.ClientSession() as session:
        batch = []
        counter = 0
        async for song in songs_to_tag:
            batch.append(song)
            
            if len(batch) >= 10: # Process in small batches to be nice to API
                results = await asyncio.gather(*[fetch_metadata(session, s["title"]) for s in batch])
                
                for s, meta in zip(batch, results):
                    if meta:
                        duration_cat = get_duration_category(meta["duration_ms"])
                        await collection.update_one(
                            {"_id": s["_id"]},
                            {"$set": {
                                "artist": meta["artist"], 
                                "genre": meta["genre"],
                                "album_art": meta["album_art"],
                                "duration_category": duration_cat,
                                "is_enriched": True
                            }}
                        )
                    else:
                        # Mark as enriched but with fallback genre to avoid re-scanning
                        await collection.update_one(
                            {"_id": s["_id"]}, 
                            {"$set": {"is_enriched": True, "genre": "Misc"}}
                        )
                
                counter += len(batch)
                print(f"✅ Processed {counter}/{total_found} songs...", end="\r")
                batch = []
                await asyncio.sleep(0.2)

        # Handle leftovers
        if batch:
            results = await asyncio.gather(*[fetch_metadata(session, s["title"]) for s in batch])
            for s, meta in zip(batch, results):
                if meta:
                     duration_cat = get_duration_category(meta["duration_ms"])
                     await collection.update_one(
                        {"_id": s["_id"]},
                        {"$set": {
                            "artist": meta["artist"], 
                            "genre": meta["genre"],
                            "album_art": meta["album_art"],
                            "duration_category": duration_cat,
                            "is_enriched": True
                        }}
                    )
                else:
                    await collection.update_one({"_id": s["_id"]}, {"$set": {"is_enriched": True, "genre": "Misc"}})
            print(f"✅ Processed {total_found}/{total_found} songs.")

    print("\n🎉 Tagger Finished! Restart your server (main.py) to see changes.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())