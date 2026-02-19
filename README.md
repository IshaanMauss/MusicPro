🎵 VibeStream: Premium Audio Experience
VibeStream is a high-performance, full-stack music streaming platform. It features a sleek React-based frontend with a FastAPI backend, leveraging a "Bot Swarm" architecture for efficient audio delivery and MongoDB Atlas for real-time user state synchronization.

🚀 Key Features
Premium Auth System: Secure JWT-based authentication with password strength validation.

Real-time Cloud Sync: Your likes, volume, and language preferences follow you across any device.

Smart Deduplication: Automatic library cleaning to prevent duplicate song entries.

Audio Proxying: Seamless streaming of high-fidelity audio via background-initialized Telegram workers.

Dynamic UI: Fully responsive player with auto-scrolling lyrics and Wikipedia-integrated artist info.

🛠️ Tech Stack
Frontend
Framework: React (Vite)

State Management: Zustand + Persistence

Styling: Tailwind CSS + Framer Motion

Icons/Toasts: Lucide React + React Hot Toast

Backend
API: FastAPI (Python 3.13 optimized)

Database: MongoDB Atlas (Motor driver)

Security: PyJWT + Passlib (PBKDF2-SHA256)

Bot Engine: Telethon (Async)

⚙️ Setup Instructions
1. Environment Variables
Create a .env file in the /backend directory:

Code snippet
# Telegram App Credentials
API_ID=your_api_id
API_HASH=your_api_hash

# Bot Swarm
CHANNEL_ID=your_channel_id
BOT_TOKEN_1=token_here
BOT_TOKEN_2=token_here

# Database
MONGO_URL=mongodb+srv://...
DB_NAME=music_app_pro

# Security
JWT_SECRET=your_long_hex_string_here
2. Backend Installation
Bash
cd backend
pip install -r requirements.txt
python main.py
3. Frontend Installation
Bash
cd frontend
npm install
npm run dev
☁️ Deployment Guide (Render)
Backend Service
Environment Variables: Manually add all keys from your .env to the Render Dashboard (specifically JWT_SECRET).

Manual Deploy: Use "Clear build cache & deploy" to ensure the correct bcrypt and JWT libraries are compiled.

Health Check: The backend is configured to bind to the port immediately while bots initialize in the background to prevent timeout errors.

Frontend Service
Build Command: npm run build.

Publish Directory: dist.

Environment Awareness: The api.js automatically switches to your production Render URL when deployed.

🛡️ Security & Edge Cases
Token Expiry: The system automatically logs users out if their 30-day JWT token expires, preventing data synchronization failures.

CORS: Pre-flight OPTIONS requests are explicitly handled to allow cross-origin authentication from your Render frontend.

State Reset: Logout physically wipes local storage and resets the store to "Factory Defaults" to prevent session leakage.
