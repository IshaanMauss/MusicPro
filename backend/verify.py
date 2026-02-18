import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def check_language_field():
    client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
    db = client[os.getenv("DB_NAME", "music_app_pro")]
    col = db.master_library

    # Count how many songs have a 'language' field
    count = await col.count_documents({"language": {"$exists": True}})
    total = await col.count_documents({})
    
    print(f"📊 {count} out of {total} songs have a 'language' field.")
    
    if count == 0:
        print("❌ CRITICAL: Your database is missing the 'language' field. The filter cannot work.")

if __name__ == "__main__":
    asyncio.run(check_language_field())