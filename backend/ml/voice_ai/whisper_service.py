"""
==============================================================
VibeStream Whisper Service (Cloudflare Workers AI edition)
--------------------------------------------------------------
Drop-in replacement for the local faster-whisper + torch based
service. Same public interface (is_ready, model_info, transcribe,
normalize_text), so voice_router.py requires ZERO changes.

Why this exists
----------------
faster-whisper + torch together are far too heavy for Render's
free tier (RAM/disk limits, slow/failed builds). This routes
transcription to Cloudflare Workers AI's hosted Whisper model
instead — same free Cloudflare account already used by
llm_service.py for greetings, no local model weights, no torch.

Requirements removed by switching to this file:
    torch
    faster-whisper
(scikit-learn / sentence-transformers can stay unless you also
want to move semantic search off-device — separate change.)
==============================================================
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("WhisperService")

# ==========================================================
# CONFIGURATION
# ==========================================================

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

# Cloudflare's hosted Whisper model
CF_WHISPER_MODEL = "@cf/openai/whisper"

REQUEST_TIMEOUT = 60  # transcription can take longer than a chat call

SUPPORTED_AUDIO_FORMATS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".webm",
    ".ogg",
    ".aac",
    ".flac",
}


class WhisperService:
    """
    Cloudflare-backed Whisper service. Loads no local model —
    "readiness" just means Cloudflare credentials are configured.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.model_name = CF_WHISPER_MODEL
        self.device = "cloudflare"
        self.compute_type = "remote"

        self.cloudflare_url = (
            f"https://api.cloudflare.com/client/v4/"
            f"accounts/{ACCOUNT_ID}/ai/run/{CF_WHISPER_MODEL}"
        )

        self.configured = bool(ACCOUNT_ID and API_TOKEN)

        if not self.configured:
            logger.warning(
                "Cloudflare credentials missing — voice transcription disabled. "
                "Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN."
            )
        else:
            logger.info("Whisper (Cloudflare Workers AI) service ready.")

        self._initialized = True

    # ======================================================
    # STATUS
    # ======================================================

    def is_ready(self):
        return self.configured

    def model_info(self):
        return {
            "model": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "cuda_available": False,
            "model_loaded": self.configured,
        }

    def warmup(self):
        # Nothing to warm up — the model lives on Cloudflare's side.
        logger.info("Cloudflare Whisper requires no local warmup.")

    # ======================================================
    # AUDIO VALIDATION
    # ======================================================

    def _validate_audio_file(self, audio_path: str):
        path = Path(audio_path)

        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if path.stat().st_size == 0:
            raise ValueError("Audio file is empty.")

        extension = path.suffix.lower()
        if extension not in SUPPORTED_AUDIO_FORMATS:
            raise ValueError(f"Unsupported audio format: {extension}")

        return path

    # ======================================================
    # TRANSCRIPT NORMALIZATION (unchanged from the original)
    # ======================================================

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""

        normalized = text.lower()

        corrections = {
            "why be i": "vibe ai",
            "why be": "vibe",
            "vive ai": "vibe ai",
            "vibe a i": "vibe ai",
            "vib ai": "vibe ai",
            "arjeet": "arijit",
            "arjeet singh": "arijit singh",
            "kishor": "kishore",
            "latta": "lata",
            "rafy": "rafi",
            "ashabhosle": "asha bhosle",
        }

        for wrong, correct in corrections.items():
            normalized = normalized.replace(wrong, correct)

        return normalized.strip()

    # ======================================================
    # TRANSCRIBE
    # ======================================================

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        beam_size: int = 5,  # kept for interface compatibility, unused here
    ):
        if not self.configured:
            return {
                "success": False,
                "text": "",
                "normalized_text": "",
                "language": None,
                "language_probability": None,
                "segments": [],
                "segment_count": 0,
                "error": "Voice transcription is unavailable — Cloudflare credentials not configured.",
            }

        self._validate_audio_file(audio_path)

        logger.info("=" * 70)
        logger.info("Starting Cloudflare Whisper transcription")
        logger.info("Audio : %s", audio_path)

        try:
            start_time = time.perf_counter()

            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            headers = {
                "Authorization": f"Bearer {API_TOKEN}",
            }

            response = requests.post(
                self.cloudflare_url,
                headers=headers,
                data=audio_bytes,
                timeout=REQUEST_TIMEOUT,
            )

            logger.info("Cloudflare Whisper Status : %s", response.status_code)
            response.raise_for_status()

            data = response.json()

            if not data.get("success"):
                raise RuntimeError(f"Cloudflare returned unsuccessful response: {data}")

            result = data.get("result", {})
            final_text = (result.get("text") or "").strip()

            # Cloudflare's whisper response includes word-level timing under "words"
            words = result.get("words", [])
            segment_data = [
                {
                    "start": round(w.get("start", 0), 2),
                    "end": round(w.get("end", 0), 2),
                    "text": w.get("word", ""),
                }
                for w in words
            ] if words else []

            elapsed = round(time.perf_counter() - start_time, 3)
            normalized_text = self.normalize_text(final_text)

            logger.info("Transcription completed in %.3fs", elapsed)
            logger.info("=" * 70)

            return {
                "success": True,
                "text": final_text,
                "normalized_text": normalized_text,
                "language": language or "en",
                "language_probability": None,
                "segments": segment_data,
                "segment_count": len(segment_data),
                "processing_time": elapsed,
                "audio_file": str(audio_path),
                "file_size": Path(audio_path).stat().st_size,
            }

        except Exception as exc:
            logger.exception("Cloudflare Whisper transcription failed.")
            return {
                "success": False,
                "text": "",
                "normalized_text": "",
                "language": None,
                "language_probability": None,
                "segments": [],
                "segment_count": 0,
                "error": str(exc),
            }


# ==========================================================
# GLOBAL SINGLETON
# ==========================================================

whisper_service = WhisperService()
