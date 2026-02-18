import os
import time
import asyncio
import logging
from telethon import TelegramClient, errors
from dotenv import load_dotenv

load_dotenv()

# Setup internal logger
logger = logging.getLogger("BotManager")

class BotWorker:
    def __init__(self, index, token, api_id, api_hash):
        self.index = index
        self.token = token
        # Automatically handle the session directory
        if not os.path.exists('sessions'):
            os.makedirs('sessions')
        self.client = TelegramClient(f'sessions/bot_worker_{index}', api_id, api_hash)
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
        """Checks if bot is active and not cooling down."""
        return self.is_ready and self.client.is_connected() and time.time() >= self.cooldown_until

    def trigger_cooldown(self, seconds):
        print(f"    ⚠️ Bot {self.index + 1} hit FloodWait! Sleeping for {seconds}s.")
        self.cooldown_until = time.time() + seconds

class BotManager:
    def __init__(self):
        self.workers = []
        self.current_index = 0
        self.api_id = int(os.getenv("API_ID"))
        self.api_hash = os.getenv("API_HASH")
        self.channel_id = int(os.getenv("CHANNEL_ID"))
        # Swarm configuration from .env
        self.tokens = [
            os.getenv("BOT_TOKEN_1"),
            os.getenv("BOT_TOKEN_2"),
            os.getenv("BOT_TOKEN_3")
        ]

    async def start(self):
        print(f"🤖 [Load Balancer] Initializing Swarm...")
        for i, token in enumerate(self.tokens):
            if token:
                worker = BotWorker(i, token, self.api_id, self.api_hash)
                await worker.start()
                self.workers.append(worker)
        print(f"🚀 [Load Balancer] {len(self.workers)} Bots Active.")

    def get_healthy_bot(self):
        """Round-Robin bot selection."""
        attempts = 0
        while attempts < len(self.workers):
            worker = self.workers[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.workers)
            if worker.is_available():
                return worker
            attempts += 1
        raise Exception("🔥 ALL BOTS BUSY OR DEAD.")

    async def get_audio_stream(self, message_id):
        """Fetches the message using a healthy bot from the swarm."""
        for attempt in range(len(self.workers)):
            try:
                worker = self.get_healthy_bot()
                message = await worker.client.get_messages(self.channel_id, ids=int(message_id))
                
                # Check for files (handles both audio and document types)
                if not message or not message.file:
                    return None, None

                return worker, message

            except errors.FloodWaitError as e:
                worker.trigger_cooldown(e.seconds)
                continue
            except Exception as e:
                print(f"⚠️ Fetch Error: {e}")
                continue
        return None, None