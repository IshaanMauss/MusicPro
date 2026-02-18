import json
import os
import re
import pymongo
from dotenv import load_dotenv

# 1. Setup & Config
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "music_app_pro")

# 2. Heuristic Maps (Fallback Logic)
MOOD_MAP = {
    "Happy": ["Pop", "Disco", "Ska", "Reggae", "Funk", "Joy", "Upbeat"],
    "Sad": ["Blues", "Sentimental", "Tragedy", "Sad", "Heartbreak"],
    "Chill": ["Lo-Fi", "Jazz", "Classical", "Folk", "Acoustic", "Ambient", "Slow"],
    "Energetic": ["Rock", "Metal", "Electronic", "House", "Techno", "Hip-Hop", "Dance", "Workout"],
    "Romantic": ["Bollywood", "R&B", "Soul", "Love", "Romance"],
    "Focus": ["Instrumental", "Soundtrack", "Study", "Concentration"],
    "Party": ["Club", "Latin", "Salsa", "Bhangra", "Party"]
}

def normalize_text(text):
    """
    Strict normalization for accurate matching.
    'The  Beatles!!!' -> 'thebeatles'
    """
    if not text: return ""
    # Lowercase, remove special chars, remove spaces
    return re.sub(r'[^a-z0-9]', '', str(text).lower())

def parse_duration_to_seconds(d_val):
    """
    Robust duration parser. Handles integers (seconds) and strings ("MM:SS").
    """
    if isinstance(d_val, (int, float)):
        return int(d_val)
    
    if isinstance(d_val, str):
        d_val = d_val.strip()
        try:
            parts = d_val.split(':')
            if len(parts) == 2: # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3: # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except:
            pass
    return 0

def get_duration_category(seconds):
    if seconds < 180: return "Short"      # < 3 min
    if seconds <= 300: return "Mid"       # 3-5 min
    return "Long"                         # > 5 min

def run_pro_fix():
    print("🚀 INITIALIZING PROFESSIONAL REPAIR SYSTEM...")
    
    # --- STEP 1: CONNECT TO DB ---
    try:
        client = pymongo.MongoClient(MONGO_URL)
        db = client[DB_NAME]
        col = db.master_library
        total_songs = col.count_documents({})
        print(f"✅ DB Connected. Scanning {total_songs} songs.")
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        return

    # --- STEP 2: LOAD JSON REFERENCE (The "Source of Truth") ---
    json_lookup = {}
    try:
        with open('../duration_fix.json', 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            # Handle if JSON is list or dict wrapper
            source_list = raw_data.get('results', raw_data) if isinstance(raw_data, dict) else raw_data
            
            print(f"📂 Loading {len(source_list)} songs from JSON reference...")
            
            for item in source_list:
                # Create a composite key: title|artist
                t_raw = item.get('title', '')
                a_raw = item.get('artist_name') or item.get('artist') or ''
                
                key = f"{normalize_text(t_raw)}|{normalize_text(a_raw)}"
                
                # Store valuable data for this key
                json_lookup[key] = {
                    "mood": item.get('mood'),
                    "duration": item.get('duration'),
                    "genre": item.get('genre')
                }
            print(f"✅ Indexed {len(json_lookup)} unique signatures from JSON.")
    except FileNotFoundError:
        print("⚠️ 'duration_fix.json' not found. Skipping JSON enrichment (using Heuristics only).")

    # --- STEP 3: THE FIX LOOP ---
    print("\n🛠️ STARTING BATCH PROCESSING...")
    
    cursor = col.find({})
    stats = {
        "json_match": 0,
        "heuristic_fix": 0,
        "various_hidden": 0,
        "processed": 0
    }

    batch_updates = []
    
    for song in cursor:
        updates = {}
        
        # A. Identity Extraction
        db_title = song.get('title', '')
        db_artist = song.get('artist', '')
        
        # B. Generate Signature
        signature = f"{normalize_text(db_title)}|{normalize_text(db_artist)}"
        
        # C. Strategy Selection
        ref_data = json_lookup.get(signature)
        
        # --- 1. DURATION LOGIC ---
        final_duration_sec = 0
        
        # Try JSON first
        if ref_data and ref_data.get('duration'):
            final_duration_sec = parse_duration_to_seconds(ref_data['duration'])
        
        # Fallback to DB current value
        if final_duration_sec == 0:
            final_duration_sec = parse_duration_to_seconds(song.get('duration'))
            
        if final_duration_sec > 0:
            updates['duration_seconds'] = final_duration_sec
            updates['duration_category'] = get_duration_category(final_duration_sec)

        # --- 2. MOOD LOGIC ---
        final_mood = "all"
        
        # Try JSON first
        if ref_data and ref_data.get('mood') and ref_data['mood'].lower() != "all":
            final_mood = ref_data['mood']
            stats["json_match"] += 1
        else:
            # Fallback to Heuristic (Genre Mapping)
            genre_str = str(song.get('genre', '')).lower()
            inferred = "Happy" # Default
            
            for m_key, keywords in MOOD_MAP.items():
                for k in keywords:
                    if k.lower() in genre_str:
                        inferred = m_key
                        break
                if inferred != "Happy": break
            
            final_mood = inferred
            stats["heuristic_fix"] += 1

        updates['mood'] = final_mood

        # --- 3. CLEANUP LOGIC ---
        # Hide "Various Artists" or empty artists
        a_lower = db_artist.lower()
        if "various artists" in a_lower or "unknown" in a_lower or not db_artist.strip():
            updates['is_hidden'] = True
            stats["various_hidden"] += 1
        else:
            updates['is_hidden'] = False

        # D. Queue Update
        if updates:
            col.update_one({"_id": song["_id"]}, {"$set": updates})

        stats["processed"] += 1
        if stats["processed"] % 1000 == 0:
            print(f"   ...processed {stats['processed']} songs")

    print("\n✨ REPAIR COMPLETE!")
    print(f"📊 Stats:")
    print(f"   - Matched & Fixed via JSON: {stats['json_match']}")
    print(f"   - Fixed via Heuristics:     {stats['heuristic_fix']}")
    print(f"   - Hidden (Various/Unknown): {stats['various_hidden']}")
    print("------------------------------------------------")
    print("👉 YOU MUST RESTART 'main.py' NOW.")

if __name__ == "__main__":
    run_pro_fix()