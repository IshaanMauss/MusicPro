import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# 1. Load your secrets
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "music_app_pro")

async def run_debug():
    print(f"📡 Connecting to Atlas...")
    
    if not MONGO_URL:
        print("❌ ERROR: MONGO_URL is missing from .env file!")
        return

    try:
        # 2. Test Connection
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        
        # 3. Test Song Count
        count = await db.songs.count_documents({})
        print(f"✅ Connection Success!")
        print(f"📊 Total Songs found in DB: {count}")

        if count == 0:
            print("❌ CRITICAL FAILURE: Your database is empty. The backend has nothing to send.")
            return

        # 4. Test Data Integrity (The most common failure point)
        sample = await db.songs.find_one()
        print("\n🔍 DATA STRUCTURE CHECK (First Song):")
        print(f"   Name: {sample.get('title', 'NO TITLE FOUND')}")
        print("   --- Keys in your Database ---")
        for key in sample.keys():
            print(f"   🔑 {key} : {type(sample[key]).__name__}")

        # 5. Check for Critical Fields
        required_fields = ["title", "msg_id"]
        missing = [field for field in required_fields if field not in sample]
        
        if missing:
            print(f"\n❌ CRITICAL FAILURE: Your JSON is missing these fields: {missing}")
            print("   The frontend cannot play music without 'msg_id'.")
        else:
            print("\n✅ Data Structure looks GOOD.")

    except Exception as e:
        print(f"\n❌ CONNECTION ERROR: {e}")

# Run the test
if __name__ == "__main__":
    asyncio.run(run_debug())