"""
THE INNER CITADEL — TTS Engine (edge-tts, Microsoft Neural)
15 curated voices from 8 countries. Natural prosody settings.
Python 3.13 compatible, no GPU, no system deps, internet required.
"""

import os
import asyncio
import numpy as np
import soundfile as sf
from pathlib import Path
from loguru import logger


# ── Voice Registry ───────────────────────────────────────────────
# 15 curated voices across 8 English-speaking regions
# rate: speech speed (-20% = slower/more gravitas, +5% = slightly faster)
# pitch: voice pitch (-10Hz = deeper, +5Hz = higher)
VOICE_PRESETS = {
    # ── American English ─────────────────────────────────────────
    "us_male_deep": {
        "edge":  "en-US-ChristopherNeural",
        "rate":  "-8%",
        "pitch": "-5Hz",
        "label": "Christopher (Deep American Male)",
        "flag":  "🇺🇸",
    },
    "us_male_calm": {
        "edge":  "en-US-AndrewNeural",
        "rate":  "-10%",
        "pitch": "-3Hz",
        "label": "Andrew (Calm American Male)",
        "flag":  "🇺🇸",
    },
    "us_female_warm": {
        "edge":  "en-US-AriaNeural",
        "rate":  "-8%",
        "pitch": "+0Hz",
        "label": "Aria (Warm American Female)",
        "flag":  "🇺🇸",
    },
    "us_female_clear": {
        "edge":  "en-US-JennyNeural",
        "rate":  "-6%",
        "pitch": "+0Hz",
        "label": "Jenny (Clear American Female)",
        "flag":  "🇺🇸",
    },

    # ── British English ──────────────────────────────────────────
    "gb_male_rich": {
        "edge":  "en-GB-RyanNeural",
        "rate":  "-12%",
        "pitch": "-8Hz",
        "label": "Ryan (Rich British Male)",
        "flag":  "🇬🇧",
    },
    "gb_male_warm": {
        "edge":  "en-GB-ThomasNeural",
        "rate":  "-10%",
        "pitch": "-5Hz",
        "label": "Thomas (Warm British Male)",
        "flag":  "🇬🇧",
    },
    "gb_female_elegant": {
        "edge":  "en-GB-SoniaNeural",
        "rate":  "-8%",
        "pitch": "+0Hz",
        "label": "Sonia (Elegant British Female)",
        "flag":  "🇬🇧",
    },

    # ── Indian English ───────────────────────────────────────────
    "in_female_expressive": {
        "edge":  "en-IN-NeerjaExpressiveNeural",
        "rate":  "-6%",
        "pitch": "+0Hz",
        "label": "Neerja (Expressive Indian Female)",
        "flag":  "🇮🇳",
    },
    "in_female_clear": {
        "edge":  "en-IN-NeerjaNeural",
        "rate":  "-8%",
        "pitch": "+0Hz",
        "label": "Neerja Classic (Indian Female)",
        "flag":  "🇮🇳",
    },
    "in_male_deep": {
        "edge":  "en-IN-PrabhatNeural",
        "rate":  "-10%",
        "pitch": "-5Hz",
        "label": "Prabhat (Deep Indian Male)",
        "flag":  "🇮🇳",
    },

    # ── Australian English ───────────────────────────────────────
    "au_female": {
        "edge":  "en-AU-NatashaNeural",
        "rate":  "-8%",
        "pitch": "+0Hz",
        "label": "Natasha (Australian Female)",
        "flag":  "🇦🇺",
    },
    "au_male": {
        "edge":  "en-AU-WilliamMultilingualNeural",
        "rate":  "-8%",
        "pitch": "-3Hz",
        "label": "William (Australian Male)",
        "flag":  "🇦🇺",
    },

    # ── Canadian English ─────────────────────────────────────────
    "ca_female": {
        "edge":  "en-CA-ClaraNeural",
        "rate":  "-8%",
        "pitch": "+0Hz",
        "label": "Clara (Canadian Female)",
        "flag":  "🇨🇦",
    },
    "ca_male": {
        "edge":  "en-CA-LiamNeural",
        "rate":  "-10%",
        "pitch": "-3Hz",
        "label": "Liam (Canadian Male)",
        "flag":  "🇨🇦",
    },

    # ── Irish English ────────────────────────────────────────────
    "ie_male": {
        "edge":  "en-IE-ConnorNeural",
        "rate":  "-10%",
        "pitch": "-3Hz",
        "label": "Connor (Irish Male)",
        "flag":  "🇮🇪",
    },
}

# Default voice — deep American male for Stoic content
DEFAULT_VOICE = "gb_male_rich"

SAMPLE_RATE = 24000


class TTSEngine:
    """
    Microsoft Edge Neural TTS Engine.
    15 curated voices from 8 English-speaking countries.
    Natural prosody optimized for Stoic spoken-word content.
    """

    def __init__(self, voice: str = DEFAULT_VOICE):
        # Accept both the key (gb_male_rich) and legacy keys (af_bella)
        if voice in VOICE_PRESETS:
            self.voice_key = voice
        else:
            # Legacy key fallback mapping
            legacy_map = {
                "af_bella":   "us_female_warm",
                "bm_george":  "gb_male_rich",
                "am_adam":    "us_male_deep",
                "bf_emma":    "gb_female_elegant",
                "af_sarah":   "us_female_clear",
                "am_michael": "us_male_calm",
            }
            self.voice_key = legacy_map.get(voice, DEFAULT_VOICE)

        preset = VOICE_PRESETS[self.voice_key]
        self.edge_voice = preset["edge"]
        self.rate       = preset["rate"]
        self.pitch      = preset["pitch"]
        self.sample_rate = SAMPLE_RATE

        logger.info(
            f"[TTS] {preset['flag']} {preset['label']} "
            f"| rate={self.rate} pitch={self.pitch} | Engine: edge-tts"
        )

    def synthesize(self, script_data: dict, output_path: str) -> str:
        """
        Synthesizes all script beats into a single WAV file.

        Args:
            script_data: Script dict with 'beats' list
            output_path: Path to save final WAV

        Returns:
            str: Path to saved WAV file
        """
        beats = script_data.get("beats", [])
        if not beats:
            raise ValueError("[TTS] Script has no beats")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._synthesize_async(beats, output_path)
        )

    async def _synthesize_async(self, beats: list, output_path: str) -> str:
        """Synthesize each beat and concatenate with natural pauses."""
        import edge_tts
        import tempfile

        segments = []
        # Natural pause durations
        pause_short  = np.zeros(int(self.sample_rate * 0.30), dtype=np.float32)
        pause_medium = np.zeros(int(self.sample_rate * 0.55), dtype=np.float32)
        pause_long   = np.zeros(int(self.sample_rate * 0.85), dtype=np.float32)

        for i, beat in enumerate(beats):
            # Clean text: remove commas (they cause unnatural pauses in TTS)
            # and strip philosopher name attributions at end
            text = self._clean_text(beat.get("text", "").strip())
            if not text:
                continue

            intent = beat.get("intent", "")
            logger.debug(f"[TTS] Beat {i+1}/{len(beats)}: '{text}'")

            try:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp_path = tmp.name

                communicate = edge_tts.Communicate(
                    text=text,
                    voice=self.edge_voice,
                    rate=self.rate,
                    pitch=self.pitch,
                    volume="+0%",
                )
                await communicate.save(tmp_path)

                # Load MP3 as numpy float32
                audio, sr = sf.read(tmp_path, dtype="float32")
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

                if audio.ndim > 1:
                    audio = audio.mean(axis=1)

                segments.append(audio)

                # Pause selection by intent
                if intent in ("hook", "close"):
                    segments.append(pause_long)
                elif intent in ("insight", "reframe"):
                    segments.append(pause_medium)
                else:
                    segments.append(pause_short)

                logger.info(f"[TTS] Beat {i+1} done: {len(audio)/self.sample_rate:.2f}s")

            except Exception as e:
                logger.warning(f"[TTS] Beat {i+1} failed: {e} — skipping")

        if not segments:
            raise RuntimeError("[TTS] No audio segments produced")

        full_audio = np.concatenate(segments).astype(np.float32)

        # Normalize — prevents clipping without changing character
        max_val = np.abs(full_audio).max()
        if max_val > 0:
            full_audio = full_audio / max_val * 0.92

        sf.write(output_path, full_audio, self.sample_rate, format="WAV")
        duration = len(full_audio) / self.sample_rate
        logger.info(f"[TTS] {len(beats)} beats → {duration:.2f}s → {output_path}")
        return output_path

    def _clean_text(self, text: str) -> str:
        """
        Cleans TTS text for natural speech:
        - Strips trailing philosopher names (Epictetus, Seneca, etc.)
        - Removes commas (cause TTS to pause awkwardly)
        - Ensures sentence ends with period
        """
        # List of known philosopher/attribution words that should be stripped
        philosopher_names = [
            "Epictetus", "Seneca", "Marcus Aurelius", "Aurelius",
            "Stoics", "Stoic", "Zeno", "Chrysippus", "Cleanthes",
        ]
        for name in philosopher_names:
            # Remove ", Name" or " Name" at end of sentence
            if text.endswith(f", {name}"):
                text = text[: -(len(name) + 2)]
            elif text.endswith(f" {name}"):
                text = text[: -(len(name) + 1)]

        # Remove commas — they cause TTS to pause at wrong places
        text = text.replace(",", "")

        # Ensure ends with period for clean TTS termination
        text = text.strip()
        if text and text[-1] not in ".!?":
            text += "."

        return text


def get_voice_list() -> list:
    """Returns all available voices for the frontend API."""
    return [
        {
            "id":    key,
            "label": preset["label"],
            "flag":  preset["flag"],
            "edge":  preset["edge"],
        }
        for key, preset in VOICE_PRESETS.items()
    ]
