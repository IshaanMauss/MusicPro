import asyncio
import logging
import time
import os
from telethon import TelegramClient, errors
from dotenv import load_dotenv

# 🟢 Initialize Environment Variables
load_dotenv()

# --- DYNAMIC CONFIGURATION ---
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# 🟢 THE SWARM: Pulling tokens from .env
BOT_TOKENS = [
    os.getenv("BOT_TOKEN_1"),
    os.getenv("BOT_TOKEN_2"),
    os.getenv("BOT_TOKEN_3")
]

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARNING)
logger = logging.getLogger("BotManager")

class BotWorker:
    def __init__(self, index, token):
        self.index = index
        self.token = token
        
        # 🟢 Defensive Check: Auto-create the sessions directory
        if not os.path.exists('sessions'):
            os.makedirs('sessions')
            print("📁 Created 'sessions' directory.")

        # Now it is safe to connect
        self.client = TelegramClient(f'sessions/bot_worker_{index}', API_ID, API_HASH)
        self.cooldown_until = 0 
        self.is_ready = False

    async def start(self):
        try:
            await self.client.start(bot_token=self.token)
            self.is_ready = True
            print(f"    ✅ Bot {self.index + 1} Connected")
        except Exception as e:
            print(f"    ❌ Bot {self.index + 1} Failed: {e}")
            self.is_ready = False

    def is_available(self):
        """Checks if bot is connected and not in FloodWait cooldown."""
        if not self.is_ready or not self.client.is_connected():
            return False
        if time.time() < self.cooldown_until:
            return False
        return True

    def trigger_cooldown(self, seconds):
        """Locks the bot for X seconds due to FloodWait."""
        print(f"    ⚠️ Bot {self.index + 1} hit FloodWait! Sleeping for {seconds}s.")
        self.cooldown_until = time.time() + seconds

class BotManager:
    def __init__(self):
        self.workers = []
        self.current_index = 0

    async def start(self):
        """Initializes the Swarm."""
        print(f"🤖 [Load Balancer] Initializing {len(BOT_TOKENS)} bots...")
        for i, token in enumerate(BOT_TOKENS):
            worker = BotWorker(i, token)
            await worker.start()
            self.workers.append(worker)
        print("🚀 [Load Balancer] Engine Running.")

    def get_healthy_bot(self):
        """Round-Robin that skips dead/sleeping bots."""
        attempts = 0
        while attempts < len(self.workers):
            # 1. Pick current bot
            worker = self.workers[self.current_index]
            
            # 2. Rotate index for next time
            self.current_index = (self.current_index + 1) % len(self.workers)
            
            # 3. Check health
            if worker.is_available():
                return worker
            
            attempts += 1
        
        # If loop finishes, ALL bots are dead/sleeping
        raise Exception("🔥 ALL BOTS BUSY OR DEAD. System Overload.")

    async def get_audio_stream(self, message_id):
        """
        Smart Fetcher: Handles errors and retries with different bots.
        Returns: (TelegramClient, MessageObject)
        """
        # Try up to 3 times with different bots
        for attempt in range(3):
            try:
                worker = self.get_healthy_bot()
                
                # Fetch message
                message = await worker.client.get_messages(CHANNEL_ID, ids=int(message_id))
                
                if not message or not message.audio:
                    print(f"❌ Message {message_id} not found or not audio.")
                    return None, None

                # Return the worker AND the message (we need the worker to stream it)
                return worker, message

            except errors.FloodWaitError as e:
                # CRITICAL: Mark this specific bot as "Cooling Down"
                worker.trigger_cooldown(e.seconds)
                continue # Loop again to try a different bot
                
            except Exception as e:
                print(f"⚠️ Fetch Error (Attempt {attempt+1}): {e}")
                continue
        
        return None, None