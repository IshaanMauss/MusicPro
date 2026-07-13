import asyncio
import logging
import math
import os
import re
import time
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import List, Optional

import jwt
import httpx
from bot_manager import BotManager
from dotenv import load_dotenv
load_dotenv()
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware


from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from pydantic import BaseModel
from routes.bot_router import router as bot_router
from routes.voice_router import router as voice_router
from ml.semantic_search import semantic_engine
from ml.mood_engine import mood_engine
from ml.recommender import recommendation_engine
from ml.explainability import explainability_engine
from ml.anomaly_detector import anomaly_detector
from routes.tts_router import router as tts_router
from fastapi import APIRouter
from ml.llm_service import llm_service 
router = APIRouter()



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
# Silence noisy third-party libraries
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
logging.getLogger("pymongo.serverSelection").setLevel(logging.WARNING)

logging.getLogger("motor").setLevel(logging.WARNING)

logging.getLogger("telethon").setLevel(logging.WARNING)
logging.getLogger("telethon.network").setLevel(logging.WARNING)

logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)

logging.getLogger("torch").setLevel(logging.ERROR)
load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    logger.critical("JWT_SECRET missing from environment variables")
    raise RuntimeError("JWT_SECRET must be set in environment variables")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

manager = BotManager()
MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    logger.error("MONGO_URL missing from environment")

mongo_client = AsyncIOMotorClient(MONGO_URL)
DB_NAME = os.getenv("DB_NAME", "music_app_pro")
db = mongo_client[DB_NAME]

SONGS_CACHE_TTL_SECONDS = 45
RECOMMENDATION_CACHE_TTL_SECONDS = 30
MAX_STREAM_WORKERS = int(os.getenv("MAX_STREAM_WORKERS", "120"))
MIN_RECOMMENDATION_SIGNALS = 5

songs_cache = {}
recommendation_cache = {}
stream_semaphore = asyncio.Semaphore(MAX_STREAM_WORKERS)


class UserAuth(BaseModel):
    username: str
    password: str


class UserStateSync(BaseModel):
    liked_songs: List[dict] = []
    current_song: Optional[dict] = None
    recently_played: List[dict] = []
    play_events: List[dict] = []
    volume: float = 0.7
    selected_language: str = "all"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("STEP 1: Lifespan started")
    
    # Ensure indexes in MongoDB
    await ensure_indexes()
    print("STEP 2: Mongo indexes ensured")
    logger.info("System init: starting FastAPI")

    # Helper function to normalize song data
    def as_list(val):
        if isinstance(val, list): return val
        if not val: return []
        return [str(val)]

    try:
        # Fetch raw data
        raw_songs = await db.master_library.find({"is_hidden": {"$ne": True}}).to_list(length=100000)
        print(f"STEP 3: Loaded {len(raw_songs)} songs from DB")

        normalized_songs = []
        for song in raw_songs:
            # Elite Fix: Use your existing normalize_song function so the 
            # AI engines actually store the album_art and msg_id (audio link)!
            normalized_songs.append(normalize_song(song))

        # Build Engines
        if normalized_songs:
            print("STEP 4: Building indexes...")
            
            semantic_engine.build_index(normalized_songs)
            print("STEP 4.1: Semantic index built")
            
            mood_engine.build_index(normalized_songs)
            print("STEP 6: Mood index built")
            
            recommendation_engine.build_index(normalized_songs)
            print("STEP 8: Recommendation index built")
            
            anomaly_detector.build_index(normalized_songs)
            print("STEP 10: Anomaly engine ready")
            
            logger.info(f"AI Engines initialized with {len(normalized_songs)} songs.")
        else:
            logger.warning("No songs found. ML indexes skipped.")

    except Exception as exc:
        logger.error("Failed to build ML indexes: %s", exc)
        print(f"STEP 11: Failed to build indexes: {exc}")

    # Start Background Bot Task
    bot_task = asyncio.create_task(manager.start())
    print("STEP 12: Bot task started")

    yield  # Application running

    # Cleanup on shutdown
    logger.info("System shutdown: disconnecting Telegram workers")
    bot_task.cancel()
    try:
        for worker in manager.workers:
            if hasattr(worker, 'client') and worker.client and worker.client.is_connected():
                await worker.client.disconnect()
    except Exception as exc:
        logger.error("Error during shutdown cleanup: %s", exc)


async def ensure_indexes():
    try:
        await db.master_library.create_index([("is_hidden", 1), ("genre", 1), ("title", 1)])
        await db.master_library.create_index([("artist", 1)])
        await db.master_library.create_index([("mood", 1)])
        await db.master_library.create_index([("language", 1)])
        await db.users.create_index([("username", 1)], unique=True)
        logger.info("Mongo indexes ready")
    except Exception as exc:
        logger.warning("Index setup skipped/failed: %s", exc)


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://vibestream.onrender.com",
        "https://musicpro-jbap.onrender.com",
        "https://music-app-backend-twia.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With", "Range"],
    expose_headers=["Accept-Ranges", "Content-Length", "Content-Range"],
)


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
    except jwt.PyJWTError as exc:
        logger.error("JWT decode error: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in re.split(r"[,/|]", str(value)) if part.strip()]


def first_value(value, fallback="Unknown"):
    values = as_list(value)
    return values[0] if values else fallback


def normalize_text(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def compact_text(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def token_set(*values):
    tokens = []
    for value in values:
        if isinstance(value, list):
            tokens.extend(token_set(*value))
        else:
            tokens.extend(re.findall(r"[a-z0-9]+", str(value or "").lower()))
    return tokens


def clean_title(title):
    if not title:
        return "Unknown Title"
    title = str(title)
    title = re.sub(r"\.(mp3|m4a|flac|wav)$", "", title, flags=re.IGNORECASE)
    title = title.replace("_", " ")
    title = re.sub(r"\s*[-_][A-Za-z0-9_-]{8,16}$", "", title)
    patterns = [
        r"\(.*?official.*?video.*?\)",
        r"\[.*?official.*?video.*?\]",
        r"\(.*?lyric.*?video.*?\)",
        r"\[.*?video.*?\]",
        r"\(.*?audio.*?\)",
        r"\[.*?4k.*?\]",
        r"\|.*",
        r"\d+kbps",
        r"\b(stereo|remaster(?:ed)?|full song|video song|lyrics?)\b",
        r"\(.*?\d{4}.*?\)",
    ]
    for pattern in patterns:
        title = re.sub(pattern, "", title, flags=re.IGNORECASE)
    title = strip_telegram_suffix(title)
    title = re.sub(r"[\s,.-]+(?:pt|part)\.?\s*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title)
    return title.strip() or "Unknown Title"


def looks_like_random_suffix(token):
    token = re.sub(r"[^A-Za-z0-9]", "", str(token or ""))
    if len(token) < 4 or len(token) > 14:
        return False
    if token[:1].isupper() and token[1:].islower():
        return False
    has_digit = any(char.isdigit() for char in token)
    has_lower = any(char.islower() for char in token)
    has_upper = any(char.isupper() for char in token)
    vowel_count = len(re.findall(r"[aeiouAEIOU]", token))
    consonant_count = len(re.findall(r"[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]", token))
    if has_digit and (has_lower or has_upper):
        return True
    if has_lower and has_upper and vowel_count <= 1 and consonant_count >= 3:
        return True
    return False


def strip_telegram_suffix(title):
    words = re.split(r"\s+", str(title or "").strip())
    # Telegram/YouTube filenames often leave a split 8-12 char id:
    # "Song Name AX85 3l gzc" -> "Song Name".
    while len(words) > 2:
        tail = "".join(re.sub(r"[^A-Za-z0-9]", "", word) for word in words[-4:])
        if 8 <= len(tail) <= 16 and looks_like_random_suffix(tail):
            words.pop()
            continue
        tail = "".join(re.sub(r"[^A-Za-z0-9]", "", word) for word in words[-3:])
        if 8 <= len(tail) <= 16 and looks_like_random_suffix(tail):
            words.pop()
            continue
        tail = "".join(re.sub(r"[^A-Za-z0-9]", "", word) for word in words[-2:])
        if 8 <= len(tail) <= 16 and looks_like_random_suffix(tail):
            words.pop()
            continue
        break
    while len(words) > 1 and looks_like_random_suffix(words[-1]):
        words.pop()
    return " ".join(words)


def clean_artist(artist):
    artist = str(artist or "").strip()
    if not artist or re.search(r"unknown|various artists|^va\s*-", artist, re.I):
        return "Unknown Artist"
    return re.sub(r"\s+", " ", artist)


def infer_language(song):
    raw_language = first_value(song.get("language"), "")
    artist = clean_artist(song.get("artist") or song.get("artist_name"))
    title = str(song.get("title") or "")
    genre_text = " ".join(as_list(song.get("genre"))).lower()
    mood_text = " ".join(as_list(song.get("moods") or song.get("mood"))).lower()
    blob = f"{raw_language} {title} {genre_text} {mood_text}".lower()

    language_markers = {
        "hindi": "Hindi",
        "bollywood": "Hindi",
        "filmi": "Hindi",
        "punjabi": "Punjabi",
        "bhangra": "Punjabi",
        "bengali": "Bengali",
        "bangla": "Bengali",
        "english": "English",
        "rock": "English",
        "k-pop": "Others",
        "kpop": "Others",
        "korean": "Others",
    }
    for marker, label in language_markers.items():
        if marker in blob:
            return label

    bad_values = {artist.lower(), "unknown", "all", "none", "na", ""}
    if raw_language.lower() not in bad_values:
        return raw_language.title()
    return "Others"


def build_description(title, artist, genres, moods, language, year=None, album=""):
    genre = first_value(genres, "music")
    mood = first_value(moods, "")
    era = ""
    if isinstance(year, int) and year:
        if year < 1980:
            era = "golden-era "
        elif year < 2000:
            era = "classic "
        elif year < 2015:
            era = "modern "
    elif language == "Hindi" or "bollywood" in " ".join(genres).lower():
        era = "classic "

    artist_text = f" by {artist}" if artist and artist != "Unknown Artist" else ""
    album_text = f" from {album}" if album else ""
    mood_text = f" with a {mood.lower()} feel" if mood and mood.lower() != "unknown" else ""
    language_text = f" {language}" if language and language != "Others" else ""

    return (
        f"{title} is a {era}{language_text} {genre.lower()} track{artist_text}{album_text}"
        f"{mood_text}. It is selected for listeners who enjoy similar voices, era, mood, and musical texture."
    ).replace("  ", " ").strip()


def normalize_song(song):
    title = clean_title(song.get("title") or song.get("file_name"))
    artist = clean_artist(song.get("artist") or song.get("artist_name"))
    genres = as_list(song.get("genre"))
    moods = as_list(song.get("moods") or song.get("mood"))
    language = infer_language(song)
    album = song.get("album") or ""
    duration_seconds = int(song.get("duration_seconds") or 0)
    description = str(song.get("description") or "").strip()
    if not description or description.lower().startswith(("enjoy this track", "the story of this song")):
        description = build_description(title, artist, genres, moods, language, song.get("year"), album)
    search_text = normalize_text(
        " ".join([title, artist, " ".join(genres), " ".join(moods), str(album)])
    )

    return {
        "id": str(song["_id"]),
        "title": title,
        "artist": artist,
        "album": album,
        "album_art": song.get("album_art") or song.get("cover_url") or "https://placehold.co/300",
        "msg_id": song.get("msg_id") or song["_id"],
        "duration": song.get("duration", "0:00"),
        "duration_seconds": duration_seconds,
        "genre": first_value(genres, "Unknown"),
        "genres": genres,
        "mood": first_value(moods, "Unknown"),
        "moods": moods,
        "language": language,
        "description": description,
        "year": song.get("year"),
        "is_playable": song.get("is_playable", True),
        "search_text": search_text,
        "signature": song_signature(title, artist),
    }


def public_song(song):
    return {key: value for key, value in song.items() if key not in {"search_text", "signature"}}


def song_signature(title, artist):
    return f"{compact_text(title)}|{compact_text(artist)}"


def dedupe_songs(songs):
    unique = []
    seen = set()
    for song in songs:
        signature = song.get("signature") or song_signature(song.get("title"), song.get("artist"))
        if not signature or signature in seen:
            continue
        seen.add(signature)
        unique.append(song)
    return unique


def classic_hindi_score(song):
    title = normalize_text(song.get("title"))
    artist = normalize_text(song.get("artist"))
    genres = normalize_text(" ".join(song.get("genres", [])))
    moods = normalize_text(" ".join(song.get("moods", [])))
    blob = f"{title} {artist} {genres} {moods} {song.get('language', '')}".lower()
    score = 0
    classic_artists = [
        "kishore kumar",
        "mohammed rafi",
        "mukesh",
        "lata mangeshkar",
        "asha bhosle",
        "rd burman",
        "r d burman",
        "manna dey",
        "hemant kumar",
    ]
    if song.get("language") == "Hindi":
        score += 35
    if "bollywood" in blob or "filmi" in blob or "indian film" in blob:
        score += 30
    if any(name in blob for name in classic_artists):
        score += 60
    year = song.get("year")
    if isinstance(year, int):
        if 1940 <= year <= 1995:
            score += 25
        elif year > 2010:
            score -= 10
    if "romantic" in blob or "nostalgic" in blob or "soulful" in blob:
        score += 8
    if song.get("album_art") and "placehold.co" not in song.get("album_art", ""):
        score += 3
    return score


def sort_library_songs(songs, search, genre, mood, listen, language):
    has_filters = any(value and value.lower() != "all" for value in [genre, mood, listen, language])
    if search or has_filters:
        return songs
    return sorted(
        songs,
        key=lambda song: (-classic_hindi_score(song), song["title"].lower(), song["artist"].lower()),
    )


def build_base_query():
    return {
        "is_hidden": {"$ne": True},
        "artist": {"$not": {"$regex": "various|unknown|va -", "$options": "i"}},
    }


def fuzzy_score(query, song):
    query = normalize_text(query)
    if not query:
        return 1.0
    haystack = song["search_text"]
    if query in haystack:
        return 1.0
    query_tokens = query.split()
    hay_tokens = set(haystack.split())
    overlap = sum(1 for token in query_tokens if token in hay_tokens)
    token_score = overlap / max(len(query_tokens), 1)
    ratio = max(
        SequenceMatcher(None, query, normalize_text(song["title"])).ratio(),
        SequenceMatcher(None, query, normalize_text(song["artist"])).ratio(),
        SequenceMatcher(None, query, haystack[:120]).ratio(),
    )
    if len(query_tokens) >= 2 and overlap == 0:
        ratio *= 0.45
    return max(token_score, ratio)


def matches_filter(song, genre, mood, listen, language):
    if genre and genre.lower() != "all":
        genres = [item.lower() for item in song.get("genres", [])] + [song.get("genre", "").lower()]
        if not any(genre.lower() in item for item in genres):
            return False
    if mood and mood.lower() != "all":
        moods = [item.lower() for item in song.get("moods", [])] + [song.get("mood", "").lower()]
        if not any(mood.lower() in item for item in moods):
            return False
    if language and language.lower() != "all":
        if song.get("language", "").lower() != language.lower():
            return False
    if listen and listen.lower() != "all":
        seconds = int(song.get("duration_seconds") or 0)
        if listen == "Short" and not (seconds and seconds < 180):
            return False
        if listen == "Mid" and not (seconds == 0 or 180 <= seconds <= 300):
            return False
        if listen == "Long" and not (seconds > 300):
            return False
    return True


def vectorize_song(song):
    weights = Counter()
    for token in token_set(song.get("title")):
        weights[f"title:{token}"] += 1.2
    for token in token_set(song.get("artist")):
        weights[f"artist:{token}"] += 1.5
    for token in token_set(song.get("genres") or song.get("genre")):
        weights[f"genre:{token}"] += 2.0
    for token in token_set(song.get("moods") or song.get("mood")):
        weights[f"mood:{token}"] += 2.0
    if song.get("language"):
        weights[f"language:{song['language'].lower()}"] += 1.8
    duration = int(song.get("duration_seconds") or 0)
    if duration:
        bucket = "short" if duration < 180 else "mid" if duration <= 300 else "long"
        weights[f"duration:{bucket}"] += 0.7
    return weights


def cosine_similarity(left, right):
    if not left or not right:
        return 0
    dot = sum(weight * right.get(token, 0) for token, weight in left.items())
    left_norm = math.sqrt(sum(weight * weight for weight in left.values()))
    right_norm = math.sqrt(sum(weight * weight for weight in right.values()))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0


def merge_profile(*weighted_songs):
    profile = Counter()
    for song, strength in weighted_songs:
        for token, weight in vectorize_song(song).items():
            profile[token] += weight * strength
    return profile


def cache_get(cache, key):
    entry = cache.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if expires_at < time.time():
        cache.pop(key, None)
        return None
    return value


def cache_set(cache, key, value, ttl):
    if len(cache) > 500:
        now = time.time()
        expired = [item_key for item_key, (expires_at, _) in cache.items() if expires_at < now]
        for item_key in expired[:100]:
            cache.pop(item_key, None)
        if len(cache) > 500:
            cache.pop(next(iter(cache)), None)
    cache[key] = (time.time() + ttl, value)


def state_fingerprint(state):
    liked_ids = [str(song.get("id") or song.get("msg_id")) for song in state.get("liked_songs", [])[:50]]
    recent_ids = [str(song.get("id") or song.get("msg_id")) for song in state.get("recently_played", [])[:50]]
    event_count = len(state.get("play_events", []))
    return "|".join(liked_ids + ["recent"] + recent_ids + ["events", str(event_count)])


def recommendation_signal_count(liked, recent, events):
    meaningful_events = 0
    for event in events:
        played = float(event.get("played_seconds") or 0)
        completion = float(event.get("completion") or 0)
        if played >= 45 or completion >= 0.35:
            meaningful_events += 1
    return len(liked) * 2 + min(len(recent), 10) + meaningful_events * 2


@app.post("/auth/register")
async def register(user: UserAuth):
    existing = await db.users.find_one({"username": user.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = {
        "username": user.username,
        "password": pwd_context.hash(user.password),
        "state": UserStateSync().dict(),
        "created_at": datetime.utcnow(),
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
        "state": db_user.get("state"),
    }


@app.post("/user/sync")
async def sync_state(state: UserStateSync, username: str = Depends(get_current_user)):
    try:
        await db.users.update_one({"username": username}, {"$set": {"state": state.dict()}})
        return {"msg": "Sync successful"}
    except Exception as exc:
        logger.error("Sync error for %s: %s", username, exc)
        raise HTTPException(status_code=500, detail="Failed to sync user data")


@app.get("/songs")
async def get_songs(
    search: str = None,
    genre: str = "all",
    mood: str = "all",
    listen: str = "all",
    language: str = "all",
    limit: int = 100,
    skip: int = 0,
):
    logger.debug("Fetching songs: genre=%s mood=%s language=%s search=%s", genre, mood, language, search)
    cache_key = (
        normalize_text(search or ""),
        genre.lower(),
        mood.lower(),
        listen.lower(),
        language.lower(),
        int(limit),
        int(skip),
    )
    cached = cache_get(songs_cache, cache_key)
    if cached is not None:
        return cached

    try:
        db_query = build_base_query()
        if genre and genre.lower() != "all":
            db_query["genre"] = {"$regex": re.escape(genre), "$options": "i"}
        if mood and mood.lower() != "all":
            db_query["$or"] = [
                {"mood": {"$regex": re.escape(mood), "$options": "i"}},
                {"moods": {"$regex": re.escape(mood), "$options": "i"}},
            ]

        fetch_limit = max(limit + skip + 300, 700 if search else 5000)
        cursor = db.master_library.find(db_query).limit(fetch_limit).sort([("genre", 1), ("title", 1)])
        raw_songs = await cursor.to_list(length=fetch_limit)
        normalized = [normalize_song(song) for song in raw_songs]
        filtered = [
            song
            for song in normalized
            if matches_filter(song, genre, mood, listen, language)
        ]
        filtered = sort_library_songs(dedupe_songs(filtered), search, genre, mood, listen, language)

        if search:
            scored = []
            for song in filtered:
                score = fuzzy_score(search, song)
                if score >= 0.56:
                    result = public_song(song)
                    result["match_score"] = round(score, 3)
                    scored.append(result)
            scored.sort(key=lambda item: (-item["match_score"], item["title"].lower()))
            results = scored[skip : skip + limit]
        else:
            results = [public_song(song) for song in filtered[skip : skip + limit]]

        payload = {"results": results, "total": len(filtered)}
        cache_set(songs_cache, cache_key, payload, SONGS_CACHE_TTL_SECONDS)
        return payload
    except Exception as exc:
        logger.error("DB fetch error: %s", exc)
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/recommendations")
async def get_recommendations(limit: int = 40, username: str = Depends(get_current_user)):
    try:
        limit = min(max(int(limit), 1), 40)
        db_user = await db.users.find_one({"username": username})
        state = db_user.get("state", {}) if db_user else {}
        cache_key = (username, int(limit), state_fingerprint(state))
        cached = cache_get(recommendation_cache, cache_key)
        if cached is not None:
            return cached

        liked = state.get("liked_songs", [])[:80]
        recent = state.get("recently_played", [])[:80]
        events = state.get("play_events", [])[-200:]

        if recommendation_signal_count(liked, recent, events) < MIN_RECOMMENDATION_SIGNALS:
            payload = {"results": []}
            cache_set(recommendation_cache, cache_key, payload, RECOMMENDATION_CACHE_TTL_SECONDS)
            return payload

        weighted = []
        weighted.extend((song, 3.0) for song in liked)
        weighted.extend((song, max(1.0, 2.2 - index * 0.04)) for index, song in enumerate(recent))
        for event in events:
            song = event.get("song") or {}
            played = float(event.get("played_seconds") or 0)
            completion = float(event.get("completion") or 0)
            strength = 0.7 + min(2.5, played / 90) + min(1.2, completion)
            weighted.append((song, strength))

        if not weighted:
            payload = {"results": []}
            cache_set(recommendation_cache, cache_key, payload, RECOMMENDATION_CACHE_TTL_SECONDS)
            return payload

        profile = merge_profile(*weighted)
        known_ids = {str(song.get("id") or song.get("msg_id")) for song, _ in weighted}
        cursor = db.master_library.find(build_base_query()).limit(1600)
        candidates = dedupe_songs([normalize_song(song) for song in await cursor.to_list(length=1600)])

        ranked = []
        for song in candidates:
            if str(song["id"]) in known_ids or str(song["msg_id"]) in known_ids:
                continue
            score = cosine_similarity(profile, vectorize_song(song))
            if score <= 0:
                continue
            result = public_song(song)
            result["recommendation_score"] = round(score, 4)
            ranked.append(result)

        ranked.sort(key=lambda item: (-item["recommendation_score"], item["title"].lower()))
        payload = {"results": ranked[:limit]}
        cache_set(recommendation_cache, cache_key, payload, RECOMMENDATION_CACHE_TTL_SECONDS)
        return payload
    except Exception as exc:
        logger.error("Recommendation error for %s: %s", username, exc)
        raise HTTPException(status_code=500, detail="Failed to build recommendations")


@app.get("/stream/{msg_id}")
async def stream_song(msg_id: int, range: Optional[str] = Header(None)):
    try:
        await asyncio.wait_for(stream_semaphore.acquire(), timeout=5)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Audio service is busy. Please retry.")

    worker, message = await manager.get_audio_stream(msg_id)
    if not worker or not message:
        stream_semaphore.release()
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_size = int(getattr(message.file, "size", 0) or 0)
        media_type = message.file.mime_type or "audio/mpeg"
        start = 0
        end = file_size - 1 if file_size else None
        status_code_value = 200
        headers = {"Accept-Ranges": "bytes"}

        if range and file_size:
            match = re.match(r"bytes=(\d+)-(\d*)", range)
            if not match:
                raise HTTPException(status_code=416, detail="Invalid range")
            start = int(match.group(1))
            if start >= file_size:
                raise HTTPException(status_code=416, detail="Range not satisfiable")
            end = int(match.group(2)) if match.group(2) else file_size - 1
            end = min(end, file_size - 1)
            status_code_value = 206
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

        content_length = (end - start + 1) if end is not None else file_size
        if content_length:
            headers["Content-Length"] = str(content_length)

        async def iterfile():
            sent = 0
            try:
                async for chunk in worker.client.iter_download(message.media, offset=start):
                    if content_length and sent + len(chunk) > content_length:
                        yield chunk[: content_length - sent]
                        break
                    yield chunk
                    sent += len(chunk)
                    if content_length and sent >= content_length:
                        break
            finally:
                stream_semaphore.release()

        return StreamingResponse(
            iterfile(),
            status_code=status_code_value,
            media_type=media_type,
            headers=headers,
        )
    except Exception:
        stream_semaphore.release()
        raise


app.include_router(bot_router)
app.include_router(voice_router)
app.include_router(tts_router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    logger.info("Starting Uvicorn on port %s", port)
    uvicorn.run(app, host="0.0.0.0", port=port)