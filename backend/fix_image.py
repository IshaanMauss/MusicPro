import os
import time
import re
import pymongo
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id="fb246c28fe254fbea158589070b6e20c",
    client_secret="93f2f3a2ce5f43e7813d481e5269598b"
))

client = pymongo.MongoClient(os.getenv("MONGO_URL"))
db = client[os.getenv("DB_NAME", "music_app_pro")]
col = db.master_library

def run_fuzzy_rescue():
    # 🟢 TARGET: Only the ones that failed the first round (still have YT links)
    query = {"album_art": {"$regex": "ytimg.com"}}
    
    total = col.count_documents(query)
    print(f"🎯 Attempting Fuzzy Fix for {total} stubborn songs...")

    cursor = col.find(query)
    fixed = 0
    
    for song in cursor:
        title = song.get('title', '')
        artist = song.get('artist', 'Unknown Artist')
        
        # 1. AGGRESSIVE CLEANING
        # Remove everything after: "from", "version", "classic", "-", "feat"
        clean_title = re.split(r'\b(from|version|classic|feat|ft|with|-)\b', title, flags=re.IGNORECASE)[0]
        # Remove Video IDs and brackets
        clean_title = re.sub(r'[A-Za-z0-9_-]{10,12}', '', clean_title)
        clean_title = re.sub(r'\(.*?\)|\[.*?\]', '', clean_title).strip()
        
        main_artist = artist.split(',')[0].split('|')[0].strip()

        if len(clean_title) < 2: continue

        print(f"🚀 Fuzzy Search: {clean_title}...", end="", flush=True)
        
        try:
            # Broad search instead of track:artist strict search
            results = sp.search(q=f"{clean_title} {main_artist}", limit=1, type='track')
            items = results['tracks']['items']
            
            if items:
                new_cover = items[0]['album']['images'][0]['url']
                col.update_one({"_id": song["_id"]}, {"$set": {"album_art": new_cover}})
                print(" ✅ FIXED")
                fixed += 1
            else:
                # 🔴 FINAL FALLBACK: If still not found, set to professional music placeholder
                fallback = "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=500&q=80"
                col.update_one({"_id": song["_id"]}, {"$set": {"album_art": fallback}})
                print(" ⚠️ FALLBACK")

        except Exception:
            time.sleep(1)

    print(f"\n✨ FUZZY RESCUE COMPLETE. Fixed: {fixed}")

if __name__ == "__main__":
    run_fuzzy_rescue()