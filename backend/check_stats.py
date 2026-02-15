import asyncio
import os
from dotenv import load_dotenv
from database import songs_collection

# 🟢 Load environment variables
load_dotenv()

async def verify_data():
    # 1. Total Count Check
    count = await songs_collection.count_documents({})
    print(f"📊 Total Songs in MongoDB: {count}")

    # 2. Link Check (Kitne gaano mein Telegram ID aa gayi hai)
    linked_count = await songs_collection.count_documents({"telegram_file_id": {"$exists": True, "$ne": None}})
    print(f"🔗 Songs connected to Telegram: {linked_count}")

    # 3. Sample Check (Ek gaana dikhao)
    sample = await songs_collection.find_one({"telegram_file_id": {"$exists": True, "$ne": None}})
    if sample:
        print("\n✅ Sample Data:")
        print(f"   Title: {sample['title']}")
        print(f"   Telegram ID: {sample['telegram_file_id']}")
        print(f"   Cluster: {sample.get('listen', 'Unknown')}")

if __name__ == "__main__":
    # Standard modern asyncio entry point
    asyncio.run(verify_data())