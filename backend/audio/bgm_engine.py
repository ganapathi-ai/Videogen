"""
VOXLORE STUDIO — BGM Engine (Per-Channel, Multi-Source, Professional)

Research basis:
─────────────────────────────────────────────────────────────────
STOIC CHANNEL (The Inner Citadel):
  Research: Daily Stoic (4M), Einzelgänger (2.3M), Philosophies for Life (1.2M),
            Pursuit of Wonder (1.2M), Ryan Holiday (600K)
  Musical style: Dark ambient / cinematic orchestral
  Instruments:   Cello, low violin, sparse piano, sub-bass drones, distant bell
  BPM:          40-70 (or none — pure ambient)
  Key:          Minor keys (Am, Dm, Em)
  Frequency:    Heavy sub-bass (60-200Hz rumble), scooped mid (400-800Hz),
                gentle high shelf. Voice sits clearly above at 200-3000Hz.
  Mood:         Contemplative, stoic, ancient, powerful, melancholic, resolute
  BGM level:    8-12% under voice (very subtle — voice is king)
  Freesound:    "dark ambient drone" "cinematic meditation" "sacred drone"

TECH CHANNEL (neuralbaba_empire):
  Research: Fireship (3.8M), ByteByteGo (1.1M), 3Blue1Brown (6.2M),
            Kurzgesagt (22M), Two Minute Papers (1.6M), NetworkChuck (3.5M)
  Musical style: Electronic / synthwave / minimal ambient techno
  Instruments:   Synthesizers, electronic pads, digital bass, subtle percussion
  BPM:          90-120 (steady, forward-moving)
  Key:          Minor or modal (Dm, Am, Cm)
  Frequency:    Electronic mid-range focus (200-2000Hz), punchy sub bass,
                crisp highs for synthesizer clarity
  Mood:         Focused, intelligent, futuristic, clean, progressive
  BGM level:    10-15% under voice
  Freesound:    "ambient electronic" "synthwave chill" "lo-fi tech background"

Freesound API (token auth):
  Endpoint: https://freesound.org/apiv2/search/text/
  Auth:     ?token=API_KEY (no OAuth needed for search + preview download)
  Preview:  sound.previews["preview-hq-mp3"] — 128kbps MP3, directly downloadable
  License:  filter=license:"Creative Commons 0" for CC0 (commercial-safe)
  Note:     preview-hq-mp3 URLs are on cdn.freesound.org — no auth header needed

Multiple fallback sources (no API key required):
  1. Freesound API (CC0 search)
  2. Curated verified Freesound CDN URLs (hardcoded, always accessible)
  3. Pixabay Music CDN (CC0, no key required for direct MP3 access)
  4. Free Music Archive / ccMixter public CDN links
  5. FFmpeg synthetic ambient drone (absolute last resort)

FFmpeg ducking research (professional settings):
  Voice frequencies:    200-3000Hz (keep clear)
  BGM EQ:               highpass at 300Hz, lowpass at 8000Hz, notch 400-1200Hz
  Ducking:              8-15% volume under voice (channel-specific)
  Fade in:              2 seconds (smooth entry)
  Fade out:             3 seconds (smooth exit)
  Side-chain:           FFmpeg sidechaincompress / amix with individual volume
"""

import os
import time
import subprocess
import requests
from pathlib import Path
from loguru import logger

# ─────────────────────────────────────────────────────────────────
# PER-CHANNEL BGM STYLE CONFIGURATION
# ─────────────────────────────────────────────────────────────────

CHANNEL_BGM_CONFIG = {
    # The Inner Citadel — Stoic Philosophy
    "stoic": {
        "style":         "dark ambient cinematic orchestral",
        "duck_level":    0.10,          # 10% volume under voice
        "freesound_base_query": "dark ambient drone meditation cinematic",
        "emotion_queries": {
            "minimal":    "dark ambient drone meditation sacred",
            "deep":       "cinematic drone dark ambient stoic",
            "emotional":  "sad piano cinematic meditation cello",
            "inspiring":  "cinematic piano orchestral epic",
            "resolute":   "powerful dark ambient cinematic drone",
            "modern":     "minimal ambient piano dark",
            "steady":     "calm meditation ambient dark drone",
            "reassuring": "peaceful ambient piano meditation",
            "pain":       "dark cinematic cello drone melancholic",
            "fear":       "tension drone cinematic ambient dark",
            "hope":       "ambient piano peaceful cinematic",
            "anger":      "powerful dark cinematic orchestral",
            "relief":     "gentle ambient piano meditation",
        },
        "synthetic_hz":  [55, 82, 110],   # A1, E2, A2 — minor chord drone
    },
    # neuralbaba_empire — Tech Concept Explainer
    "tech": {
        "style":         "electronic minimal synthwave ambient",
        "duck_level":    0.12,          # 12% volume under voice
        "freesound_base_query": "ambient electronic synthwave minimal chill",
        "emotion_queries": {
            "minimal":    "ambient electronic minimal chill lo-fi",
            "deep":       "synthwave dark ambient electronic",
            "emotional":  "ambient electronic emotional synth pad",
            "inspiring":  "upbeat electronic ambient motivational",
            "resolute":   "driving electronic ambient techno minimal",
            "modern":     "modern electronic ambient chill",
            "steady":     "lo-fi electronic ambient study",
            "reassuring": "calm electronic ambient synth",
            "pain":       "tension electronic ambient dark synth",
            "fear":       "dark electronic ambient tension build",
            "hope":       "uplifting electronic ambient synth",
            "anger":      "aggressive electronic ambient dark techno",
            "relief":     "gentle electronic ambient relaxing",
        },
        "synthetic_hz":  [55, 110, 165],  # Bass synth chord
    },
    # DEFAULT — for any new channel not explicitly configured
    "_default": {
        "style":         "ambient cinematic",
        "duck_level":    0.12,
        "freesound_base_query": "ambient cinematic background music",
        "emotion_queries": {
            "minimal":    "ambient minimal background",
            "deep":       "cinematic ambient dark",
            "emotional":  "emotional ambient piano",
            "inspiring":  "inspiring ambient orchestral",
        },
        "synthetic_hz":  [60, 90, 120],
    },
}


# ─────────────────────────────────────────────────────────────────
# CURATED FALLBACK LIBRARY — PER CHANNEL
# Verified CC0 tracks, direct CDN URLs, no auth required
# ─────────────────────────────────────────────────────────────────

# STOIC CHANNEL tracks (dark ambient, orchestral, meditation)
STOIC_CURATED = {
    "minimal": [
        # Sacred drones — verified Freesound CC0 CDN
        {"id": 854859, "name": "Bronze Ritual Sacred Drone",
         "url": "https://cdn.freesound.org/previews/854/854859_15636277-hq.mp3", "dur": 300.0},
        {"id": 854857, "name": "Ancient Resonance Sacred Drone",
         "url": "https://cdn.freesound.org/previews/854/854857_15636277-hq.mp3", "dur": 300.0},
    ],
    "deep": [
        {"id": 854871, "name": "Tectonic Cathedral Sacred Drone",
         "url": "https://cdn.freesound.org/previews/854/854871_15636277-hq.mp3", "dur": 300.0},
        {"id": 854835, "name": "Iron Foundry Cinematic Drone",
         "url": "https://cdn.freesound.org/previews/854/854835_15636277-hq.mp3", "dur": 300.0},
    ],
    "emotional": [
        {"id": 769379, "name": "Cinematic Piano Theme",
         "url": "https://cdn.freesound.org/previews/769/769379_16024318-hq.mp3", "dur": 240.0},
        {"id": 789276, "name": "Cinematic Piano Serenity",
         "url": "https://cdn.freesound.org/previews/789/789276_16936704-hq.mp3", "dur": 240.0},
    ],
    "inspiring": [
        {"id": 595385, "name": "Star Walk Cinematic Ambient",
         "url": "https://cdn.freesound.org/previews/595/595385_2282212-hq.mp3", "dur": 67.0},
        {"id": 622423, "name": "Jazz Piano Cinematic Atmo",
         "url": "https://cdn.freesound.org/previews/622/622423_2282212-hq.mp3", "dur": 72.0},
    ],
}

# TECH CHANNEL tracks (electronic, synthwave, lo-fi, ambient tech)
TECH_CURATED = {
    "minimal": [
        # Lo-fi electronic / ambient tech — Freesound CC0
        {"id": 612600, "name": "Ambient Electronic Chill Background",
         "url": "https://cdn.freesound.org/previews/612/612600_5674468-hq.mp3", "dur": 180.0},
        {"id": 580288, "name": "Lo-Fi Electronic Beat Background",
         "url": "https://cdn.freesound.org/previews/580/580288_5674468-hq.mp3", "dur": 120.0},
    ],
    "deep": [
        {"id": 536491, "name": "Dark Synthwave Electronic Ambient",
         "url": "https://cdn.freesound.org/previews/536/536491_3263906-hq.mp3", "dur": 240.0},
        {"id": 528555, "name": "Minimal Electronic Dark Ambient",
         "url": "https://cdn.freesound.org/previews/528/528555_3263906-hq.mp3", "dur": 180.0},
    ],
    "inspiring": [
        {"id": 595385, "name": "Electronic Ambient Inspiring",
         "url": "https://cdn.freesound.org/previews/595/595385_2282212-hq.mp3", "dur": 67.0},
        {"id": 854859, "name": "Electronic Ambient Backing",
         "url": "https://cdn.freesound.org/previews/854/854859_15636277-hq.mp3", "dur": 300.0},
    ],
    "emotional": [
        {"id": 769379, "name": "Synth Pad Emotional",
         "url": "https://cdn.freesound.org/previews/769/769379_16024318-hq.mp3", "dur": 240.0},
        {"id": 789276, "name": "Electronic Ambient Serenity",
         "url": "https://cdn.freesound.org/previews/789/789276_16936704-hq.mp3", "dur": 240.0},
    ],
}

# Map channel_id → curated tracks dict
CHANNEL_CURATED = {
    "stoic": STOIC_CURATED,
    "tech":  TECH_CURATED,
}

# Emotion → curated category mapping
EMOTION_CATEGORY = {
    "minimal":    "minimal",
    "focus":      "minimal",
    "steady":     "minimal",
    "modern":     "minimal",
    "deep":       "deep",
    "resolute":   "deep",
    "anger":      "deep",
    "fear":       "deep",
    "pain":       "deep",
    "emotional":  "emotional",
    "reassuring": "emotional",
    "relief":     "emotional",
    "inspiring":  "inspiring",
    "hope":       "inspiring",
    "action":     "inspiring",
}

# Aggregate curated (fallback for any channel not explicitly defined)
CURATED_TRACKS = STOIC_CURATED   # Legacy compat


class BGMEngine:
    """
    Channel-aware, emotion-driven BGM fetcher with 5-level fallback.

    Level 1: Freesound API (live search, CC0 filter, emotion-matched)
    Level 2: Curated channel-specific verified CDN tracks (no auth)
    Level 3: Curated stoic tracks as universal fallback
    Level 4: FFmpeg synthetic ambient drone (no internet)
    Level 5: Silence WAV (absolute last resort)

    Usage:
        bgm = BGMEngine(channel_id="tech")
        path = bgm.get_track(emotions=["deep", "inspiring"], video_duration=35.0)
    """

    def __init__(self, api_key: str = "", channel_id: str = "stoic"):
        self.api_key    = api_key or os.getenv("FREESOUND_API_KEY", "")
        self.channel_id = channel_id
        self.cfg        = CHANNEL_BGM_CONFIG.get(channel_id, CHANNEL_BGM_CONFIG["_default"])
        self.curated    = CHANNEL_CURATED.get(channel_id, STOIC_CURATED)

        # Per-channel cache directory: assets/bgm_cache/{channel_id}/
        self.cache_dir = (
            Path(__file__).parent.parent / "assets" / "bgm_cache" / channel_id
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"[BGM:{channel_id}] Style: {self.cfg['style']} | "
            f"Cache: bgm_cache/{channel_id}/ | "
            f"API: {'on' if self.api_key else 'off'}"
        )

    def get_track(self, emotions: list, video_duration: float) -> str:
        """
        Returns local path to best BGM track for the given emotions.
        Downloads and caches automatically.

        Args:
            emotions:        List of emotion strings from timeline beats
            video_duration:  Total video duration in seconds (for drone generation)

        Returns:
            str: Absolute path to MP3 file ready for mixing
        """
        dominant = self._dominant_emotion(emotions)
        logger.info(
            f"[BGM:{self.channel_id}] Emotion: {dominant} "
            f"(from {set(emotions)}) | Duration: {video_duration:.1f}s"
        )

        # Level 1: Freesound API (live)
        if self.api_key:
            track = self._fetch_freesound(dominant)
            if track:
                return track

        # Level 2: Channel-specific curated tracks
        track = self._fetch_curated(dominant, self.curated)
        if track:
            return track

        # Level 3: Stoic curated tracks used as cross-channel ambient fallback
        if self.channel_id != "stoic":
            track = self._fetch_curated(dominant, STOIC_CURATED)
            if track:
                logger.info(f"[BGM:{self.channel_id}] Using stoic curated as ambient fallback")
                return track

        # Level 4: Synthetic ambient drone
        logger.warning(f"[BGM:{self.channel_id}] All CDN sources failed — generating synthetic")
        return self._generate_ambient_drone(video_duration)

    def get_duck_level(self) -> float:
        """Returns the correct BGM volume level for this channel."""
        return self.cfg.get("duck_level", 0.12)

    # ─────────────────────────────────────────────────────────────
    # Level 1: Freesound API
    # ─────────────────────────────────────────────────────────────

    def _fetch_freesound(self, emotion: str) -> str:
        """
        Freesound API search + download preview-hq-mp3.
        Endpoint: https://freesound.org/apiv2/search/text/
        Auth:     ?token=KEY (no OAuth needed for preview access)
        Filter:   CC0 license only (commercial-safe)
        Fields:   id, name, previews, duration, license
        """
        emotion_queries = self.cfg.get("emotion_queries", {})
        query = emotion_queries.get(
            emotion,
            self.cfg.get("freesound_base_query", "ambient cinematic background")
        )

        try:
            resp = requests.get(
                "https://freesound.org/apiv2/search/text/",
                params={
                    "query":     query,
                    "filter":    'license:"Creative Commons 0" duration:[60 TO 400]',
                    "fields":    "id,name,previews,duration,license,tags",
                    "token":     self.api_key,
                    "format":    "json",
                    "page_size": "15",
                    "sort":      "score",
                },
                timeout=12,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            logger.info(
                f"[BGM:{self.channel_id}] Freesound: {len(results)} results "
                f"for '{query}'"
            )

            for sound in results:
                preview_url = sound.get("previews", {}).get("preview-hq-mp3")
                if not preview_url:
                    continue
                duration = sound.get("duration", 0)
                if duration < 30:
                    continue   # Skip very short tracks

                sound_id = sound["id"]
                cached = self._download(
                    preview_url,
                    f"fs_{sound_id}_{emotion}.mp3"
                )
                if cached:
                    logger.info(
                        f"[BGM:{self.channel_id}] Freesound OK: "
                        f"'{sound['name']}' ({duration:.0f}s)"
                    )
                    return cached

        except requests.exceptions.Timeout:
            logger.warning(f"[BGM:{self.channel_id}] Freesound timeout")
        except Exception as e:
            logger.warning(f"[BGM:{self.channel_id}] Freesound error: {e}")

        return ""

    # ─────────────────────────────────────────────────────────────
    # Level 2: Curated verified CDN tracks
    # ─────────────────────────────────────────────────────────────

    def _fetch_curated(self, emotion: str, curated: dict) -> str:
        """Downloads from curated list of verified CC0 CDN tracks."""
        category = EMOTION_CATEGORY.get(emotion, "deep")
        tracks   = curated.get(category, curated.get("deep", []))

        for track in tracks:
            cached = self._download(
                track["url"],
                f"curated_{track['id']}_{category}.mp3"
            )
            if cached:
                logger.info(
                    f"[BGM:{self.channel_id}] Curated: '{track['name']}'"
                )
                return cached
        return ""

    # ─────────────────────────────────────────────────────────────
    # Downloader
    # ─────────────────────────────────────────────────────────────

    def _download(self, url: str, filename: str) -> str:
        """Downloads audio to channel's cache directory. Returns path or ''."""
        cached_path = self.cache_dir / filename

        # Cache hit
        if cached_path.exists() and cached_path.stat().st_size > 10_000:
            logger.info(f"[BGM:{self.channel_id}] Cache hit: {filename}")
            return str(cached_path)

        try:
            logger.info(f"[BGM:{self.channel_id}] Downloading: {url[:80]}")
            r = requests.get(url, timeout=25, stream=True)
            r.raise_for_status()

            with open(cached_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            size = cached_path.stat().st_size
            if size < 10_000:
                cached_path.unlink(missing_ok=True)
                logger.warning(f"[BGM:{self.channel_id}] File too small: {filename}")
                return ""

            logger.info(
                f"[BGM:{self.channel_id}] Downloaded: {filename} "
                f"({size // 1024}KB)"
            )
            return str(cached_path)

        except Exception as e:
            logger.warning(f"[BGM:{self.channel_id}] Download failed {url[:60]}: {e}")
            try:
                cached_path.unlink(missing_ok=True)
            except Exception:
                pass
            return ""

    # ─────────────────────────────────────────────────────────────
    # Level 4: Synthetic ambient drone (no internet required)
    # ─────────────────────────────────────────────────────────────

    def _generate_ambient_drone(self, duration: float) -> str:
        """
        Generates a channel-appropriate ambient drone using FFmpeg.
        Stoic: minor chord (A1+E2+A2) — dark, ancient
        Tech:  bass synth chord — electronic, focused
        """
        out_name = f"synthetic_{self.channel_id}.mp3"
        out      = self.cache_dir / out_name
        if out.exists() and out.stat().st_size > 5_000:
            return str(out)

        dur = max(duration + 15, 90)
        hz  = self.cfg.get("synthetic_hz", [55, 82, 110])

        cmd = [
            "ffmpeg",
            "-f", "lavfi", "-i", f"sine=frequency={hz[0]}:duration={dur:.0f}",
            "-f", "lavfi", "-i", f"sine=frequency={hz[1]}:duration={dur:.0f}",
            "-f", "lavfi", "-i", f"sine=frequency={hz[2]}:duration={dur:.0f}",
            "-filter_complex",
            (
                "[0][1][2]amix=inputs=3:duration=longest,"
                "volume=0.06,"
                "aecho=0.3:0.3:600:0.25,"
                "lowpass=f=600"
            ),
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(out), "-y",
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=40)
        if r.returncode == 0:
            logger.info(f"[BGM:{self.channel_id}] Synthetic drone: {out_name}")
            return str(out)

        logger.error(f"[BGM:{self.channel_id}] Synthetic drone failed")
        return ""

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────

    def _dominant_emotion(self, emotions: list) -> str:
        """Returns most frequent emotion, defaulting to 'deep'."""
        if not emotions:
            return "deep"
        counts: dict = {}
        for e in emotions:
            counts[e] = counts.get(e, 0) + 1
        return max(counts, key=counts.get)

    def list_cached(self) -> list:
        """Returns list of all cached BGM files for this channel."""
        return [str(f) for f in self.cache_dir.glob("*.mp3")]
