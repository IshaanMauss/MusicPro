import os
import time
import logging
from tqdm import tqdm
import pymongo
from pymongo import UpdateOne
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# 1. SETUP
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET")
), requests_timeout=10, retries=3)

client = pymongo.MongoClient(os.getenv("MONGO_URL"))
db = client[os.getenv("DB_NAME", "music_app_pro")]
col = db.master_library

# 🟢 LOGIC 1: UNICODE SCRIPT (Instant Check)
def detect_script_language(text):
    if not text: return None
    for char in text:
        val = ord(char)
        if 0x0900 <= val <= 0x097F: return "Hindi"      # Devanagari
        if 0x0980 <= val <= 0x09FF: return "Bengali"    # Bengali
        if 0x0A00 <= val <= 0x0A7F: return "Punjabi"    # Gurmukhi
        if 0x4E00 <= val <= 0x9FFF: return "Others"     # CJK
        if 0xAC00 <= val <= 0xD7AF: return "Others"     # Korean
    return None

# 🟢 LOGIC 2: GENRE MAPPING
def map_genres_to_language(genres):
    g_str = " ".join(genres).lower()
    if any(x in g_str for x in ["punjabi", "bhangra", "gurmukhi"]): return "Punjabi"
    if any(x in g_str for x in ["bengali", "tollywood", "rabindra", "baul"]): return "Bengali"
    if any(x in g_str for x in ["bollywood", "filmi", "hindi", "desi", "sufi", "ghazal"]): return "Hindi"
    if any(x in g_str for x in ["tamil", "telugu", "k-pop", "anime", "c-pop"]): return "Others"
    return "English" # Default

def run_smart_fix():
    print("🚀 STARTING SMART ARTIST-CENTRIC LANGUAGE FIXER...")
    
    # 1. First, fast pass: Unicode Detection on ALL songs
    print("⚡ Phase 1: Running Unicode Script Detection...")
    all_songs = list(col.find({}, {"title": 1}))
    unicode_updates = []
    
    for song in all_songs:
        lang = detect_script_language(song.get("title", ""))
        if lang:
            unicode_updates.append(UpdateOne({"_id": song["_id"]}, {"$set": {"language": lang}}))
            
    if unicode_updates:
        print(f"   💾 Applying {len(unicode_updates)} native script tags...")
        col.bulk_write(unicode_updates)

    # 2. Identify Artists who still need checking
    # We look for songs where language is still "English" (default) or missing
    # But filtering by 'is_hidden' to skip junk
    print("🔍 Phase 2: Aggregating Unique Artists...")
    pipeline = [
        {"$match": {"language": {"$in": ["English", "all", None]}, "is_hidden": {"$ne": True}}},
        {"$group": {"_id": "$artist"}} # Group by Artist Name
    ]
    unique_artists = list(col.aggregate(pipeline))
    artist_names = [a["_id"] for a in unique_artists if a["_id"] and "Unknown" not in a["_id"]]
    
    print(f"   📊 Found {len(artist_names)} unique artists to check.")

    # 3. Process Artists (With Cache & Rate Limit Safety)
    artist_updates = []
    
    # Progress bar for artists
    pbar = tqdm(artist_names, desc="Fetching Artist Data", unit="artist")
    
    for artist_name in pbar:
        clean_name = artist_name.split(',')[0].split('|')[0].strip()
        lang = "English" # Default
        
        try:
            # API CALL (1 per Artist, not per song!)
            results = sp.search(q=f"artist:{clean_name}", limit=1, type='artist')
            items = results['artists']['items']
            
            if items:
                genres = items[0]['genres']
                lang = map_genres_to_language(genres)
            
            # Add updates for ALL songs by this artist
            # We use update_many logic via bulk write for efficiency
            # But bulk_write uses update_one/many. 
            # Strategy: We will update all songs with this artist name.
            
            # Since bulk_write is per-document, we can just issue an update_many command directly?
            # No, let's just queue an update_many.
            col.update_many(
                {"artist": artist_name},
                {"$set": {"language": lang}}
            )
            
            # Small sleep to be nice to API
            time.sleep(0.1) 

        except Exception as e:
            # If rate limited, pause longer
            time.sleep(2)
            continue

    print("\n✨ SMART FIX COMPLETE. Database is optimized.")

if __name__ == "__main__":
    run_smart_fix()