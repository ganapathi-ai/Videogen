"""
THE INNER CITADEL — BGM Engine (Freesound API + Curated Fallback)

Fetches context-aware Stoic philosophy background music using:
  1. Freesound API (live search, emotion-aware, CC0 tracks)
  2. Curated hardcoded fallback library (CC0, proven preview URLs)
  3. FFmpeg-generated ambient drone (absolute last resort, no internet)

Style Research (Daily Stoic, Einzelgänger, Philosophies for Life):
  - Minimal, slow-evolving drones or piano
  - No prominent melody (would distract from narration)
  - Dark, cinematic, meditative
  - BPM: 40-70 or none
  - BGM ducked to 8-15% under voice (FFmpeg amix)
  - HP filter at 500Hz on BGM (clears bass frequency for voice chain)

Freesound API token: from FREESOUND_API_KEY env var
"""

import os
import time
import hashlib
import subprocess
import requests
from pathlib import Path
from loguru import logger

# ─────────────────────────────────────────────────────────
# Curated Fallback Library
# CC0 tracks from Freesound (preview URLs = public CDN, no auth)
# Verified via live API. Emotion-tagged for Stoic content.
# ─────────────────────────────────────────────────────────
CURATED_TRACKS = {
    # Sacred drones — CC0, 300s, perfect for Stoic/philosophy
    "minimal": [
        {
            "id": 854859,
            "name": "Bronze Ritual Sacred Drone",
            "url":  "https://cdn.freesound.org/previews/854/854859_15636277-hq.mp3",
            "dur":  300.0,
        },
        {
            "id": 854857,
            "name": "Ancient Resonance Sacred Drone",
            "url":  "https://cdn.freesound.org/previews/854/854857_15636277-hq.mp3",
            "dur":  300.0,
        },
    ],
    "deep": [
        {
            "id": 854871,
            "name": "Tectonic Cathedral Sacred Drone",
            "url":  "https://cdn.freesound.org/previews/854/854871_15636277-hq.mp3",
            "dur":  300.0,
        },
        {
            "id": 854835,
            "name": "Iron Foundry Cinematic Drone",
            "url":  "https://cdn.freesound.org/previews/854/854835_15636277-hq.mp3",
            "dur":  300.0,
        },
    ],
    "emotional": [
        {
            "id": 769379,
            "name": "Cinematic Piano Theme for Dramatic Moments",
            "url":  "https://cdn.freesound.org/previews/769/769379_16024318-hq.mp3",
            "dur":  240.0,
        },
        {
            "id": 789276,
            "name": "Cinematic Piano Serenity",
            "url":  "https://cdn.freesound.org/previews/789/789276_16936704-hq.mp3",
            "dur":  240.0,
        },
    ],
    "inspiring": [
        {
            "id": 595385,
            "name": "Star Walk Cinematic Ambient Fantasy",
            "url":  "https://cdn.freesound.org/previews/595/595385_2282212-hq.mp3",
            "dur":  67.0,
        },
        {
            "id": 622423,
            "name": "Jazz Piano Bar Relax Cinematic Atmo",
            "url":  "https://cdn.freesound.org/previews/622/622423_2282212-hq.mp3",
            "dur":  72.0,
        },
    ],
}

# Map all emotions to one of our curated categories
EMOTION_CATEGORY = {
    "minimal":    "minimal",
    "focus":      "minimal",
    "deep":       "deep",
    "resolute":   "deep",
    "modern":     "deep",
    "steady":     "minimal",
    "emotional":  "emotional",
    "reassuring": "emotional",
    "inspiring":  "inspiring",
    "action":     "inspiring",
}

# Freesound search queries per emotion (used for live API search)
EMOTION_QUERIES = {
    "minimal":    "dark ambient drone meditation sacred",
    "deep":       "cinematic drone dark ambient stoic",
    "emotional":  "sad piano cinematic meditation",
    "inspiring":  "cinematic piano orchestral epic",
    "resolute":   "powerful dark ambient cinematic drone",
    "modern":     "minimal ambient electronic piano",
    "steady":     "calm meditation ambient dark drone",
    "reassuring": "peaceful ambient piano meditation",
}


class BGMEngine:
    """
    Emotion-aware Stoic BGM fetcher.
    Downloads and caches tracks from Freesound API.
    Falls back to curated hardcoded tracks if API fails.
    """

    def __init__(self, api_key: str = ""):
        self.api_key  = api_key or os.getenv("FREESOUND_API_KEY", "")
        self.cache_dir = Path(__file__).parent.parent / "assets" / "bgm_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[BGM] Cache: {self.cache_dir}")
        logger.info(f"[BGM] Freesound API: {'enabled' if self.api_key else 'disabled'}")

    def get_track(self, emotions: list, video_duration: float) -> str:
        """
        Returns path to best BGM track for given emotions.
        Downloads and caches if not already local.

        Args:
            emotions:        List of emotion strings from timeline segments
            video_duration:  Total video duration in seconds

        Returns:
            str: Path to BGM MP3/WAV file ready for mixing
        """
        # Determine dominant emotion
        dominant = self._dominant_emotion(emotions)
        logger.info(f"[BGM] Dominant emotion: {dominant} (from {set(emotions)})")

        # 1. Try Freesound live API
        if self.api_key:
            track = self._fetch_freesound(dominant)
            if track:
                return track

        # 2. Fall back to curated hardcoded tracks
        track = self._fetch_curated(dominant)
        if track:
            return track

        # 3. Absolute last resort: generate FFmpeg ambient drone
        logger.warning("[BGM] All sources failed — generating synthetic ambient drone")
        return self._generate_ambient_drone(video_duration)

    def _dominant_emotion(self, emotions: list) -> str:
        """Returns the most frequent emotion from the list."""
        if not emotions:
            return "deep"
        counts = {}
        for e in emotions:
            counts[e] = counts.get(e, 0) + 1
        return max(counts, key=counts.get)

    # ──────────────────────────────────────────────────
    # Freesound API (live search)
    # ──────────────────────────────────────────────────

    def _fetch_freesound(self, emotion: str) -> str:
        """
        Searches Freesound API and downloads preview MP3.
        Filters to CC0 license only (fully commercial-safe).
        Preview URLs are public CDN (no OAuth needed).
        """
        query = EMOTION_QUERIES.get(emotion, "dark ambient meditation")

        try:
            resp = requests.get(
                "https://freesound.org/apiv2/search/text/",
                params={
                    "query":     query,
                    "filter":    'license:"Creative Commons 0" duration:[60 TO 360]',
                    "fields":    "id,name,previews,duration,license",
                    "token":     self.api_key,
                    "format":    "json",
                    "page_size": "15",
                    "sort":      "score",
                },
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])

            for sound in results:
                preview_url = sound.get("previews", {}).get("preview-hq-mp3")
                if not preview_url:
                    continue
                sound_id = sound["id"]
                duration = sound.get("duration", 0)

                # Download and cache the preview
                cached = self._download_and_cache(preview_url, f"fs_{sound_id}", emotion)
                if cached:
                    logger.info(
                        f"[BGM] Freesound: '{sound['name']}' "
                        f"({duration:.0f}s) → {cached}"
                    )
                    return cached

        except Exception as e:
            logger.warning(f"[BGM] Freesound API error: {e}")

        return ""

    # ──────────────────────────────────────────────────
    # Curated fallback library
    # ──────────────────────────────────────────────────

    def _fetch_curated(self, emotion: str) -> str:
        """Downloads from curated list of verified CC0 Freesound tracks."""
        category = EMOTION_CATEGORY.get(emotion, "deep")
        tracks = CURATED_TRACKS.get(category, CURATED_TRACKS["deep"])

        for track in tracks:
            cached = self._download_and_cache(
                track["url"],
                f"curated_{track['id']}",
                emotion,
            )
            if cached:
                logger.info(f"[BGM] Curated: '{track['name']}' → {cached}")
                return cached

        return ""

    # ──────────────────────────────────────────────────
    # Downloader + cache
    # ──────────────────────────────────────────────────

    def _download_and_cache(self, url: str, cache_key: str, emotion: str) -> str:
        """
        Downloads audio URL to local cache.
        Returns cached path if already exists.
        """
        # Use hash-based filename for cache
        fname = f"{emotion}_{cache_key}.mp3"
        cached_path = self.cache_dir / fname

        # Return immediately if cached
        if cached_path.exists() and cached_path.stat().st_size > 10_000:
            logger.info(f"[BGM] Cache hit: {fname}")
            return str(cached_path)

        try:
            logger.info(f"[BGM] Downloading: {url}")
            r = requests.get(url, timeout=20, stream=True)
            r.raise_for_status()

            with open(cached_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            if cached_path.stat().st_size < 10_000:
                cached_path.unlink()
                return ""

            logger.info(f"[BGM] Downloaded: {fname} ({cached_path.stat().st_size // 1024}KB)")
            return str(cached_path)

        except Exception as e:
            logger.warning(f"[BGM] Download failed ({url}): {e}")
            try:
                cached_path.unlink()
            except Exception:
                pass
            return ""

    # ──────────────────────────────────────────────────
    # Synthetic fallback
    # ──────────────────────────────────────────────────

    def _generate_ambient_drone(self, duration: float) -> str:
        """
        Generates a minimal ambient sine drone using FFmpeg.
        Used ONLY when all internet sources fail.
        Sounds like a soft, low meditation tone.
        """
        out = self.cache_dir / "synthetic_ambient.mp3"
        if out.exists():
            return str(out)

        dur = max(duration + 10, 60)
        # Multi-layer sine waves: 60Hz, 90Hz, 120Hz (sub-bass meditation tones)
        # Mixed at very low volume
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", f"sine=frequency=60:duration={dur:.0f}",
            "-f", "lavfi",
            "-i", f"sine=frequency=90:duration={dur:.0f}",
            "-f", "lavfi",
            "-i", f"sine=frequency=120:duration={dur:.0f}",
            "-filter_complex",
            "[0][1][2]amix=inputs=3:duration=longest,volume=0.08,"
            "aecho=0.3:0.3:500:0.3,"          # subtle echo for space
            "lowpass=f=800",                   # cut highs (only bass drone)
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(out), "-y",
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode == 0:
            logger.info(f"[BGM] Synthetic drone generated: {out}")
            return str(out)

        logger.error("[BGM] Even synthetic drone failed")
        return ""

    def list_cached(self) -> list:
        """Returns list of all cached BGM files."""
        return [str(f) for f in self.cache_dir.glob("*.mp3")]
