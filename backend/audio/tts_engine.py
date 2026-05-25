"""
THE INNER CITADEL — TTS Engine (edge-tts + FFmpeg Philosophy Voice Chain)

Targets the sound of top Stoic philosophy YouTube channels:
  Daily Stoic, Einzelgänger, Philosophies for Life, Ryan Holiday narrations

Voice Processing Chain (professional order):
  1. TTS synthesis (edge-tts Neural, slow rate, low pitch)
  2. High-pass filter @80Hz  — remove sub-bass rumble
  3. Bass warmth boost @120Hz +6dB — add depth & body
  4. Mid cut @250Hz -3dB  — remove boxiness
  5. Presence boost @3kHz +2dB — voice cuts through music
  6. Dynamic compression — even out dynamics (4:1 ratio)
  7. Volume boost ×2.5 — loud and authoritative
  8. Loudnorm I=-14 LUFS — YouTube broadcast standard

Python 3.13 compatible. No GPU. FFmpeg required.
"""

import os
import asyncio
import subprocess
import tempfile
import numpy as np
import soundfile as sf
from pathlib import Path
from loguru import logger


# ── 10 Curated Deep Voices ───────────────────────────────────────
# Tuned specifically for philosophy narration — slow, deep, commanding
VOICE_PRESETS = {

    # ── 🇬🇧 British (most popular for philosophy YouTube) ─────────
    "gb_ryan": {
        "edge":  "en-GB-RyanNeural",
        "rate":  "-18%",       # Slow, deliberate — Stoic pacing
        "pitch": "-12Hz",      # Deep and commanding
        "label": "Ryan — Deep British Male",
        "desc":  "🇬🇧 Deep, commanding. Best for Stoicism.",
        "flag":  "🇬🇧",
    },
    "gb_thomas": {
        "edge":  "en-GB-ThomasNeural",
        "rate":  "-15%",
        "pitch": "-8Hz",
        "label": "Thomas — Warm British Male",
        "desc":  "🇬🇧 Warm, mature. Marcus Aurelius tone.",
        "flag":  "🇬🇧",
    },
    "gb_sonia": {
        "edge":  "en-GB-SoniaNeural",
        "rate":  "-14%",
        "pitch": "-5Hz",
        "label": "Sonia — Powerful British Female",
        "desc":  "🇬🇧 Powerful, elegant. Female philosophy voice.",
        "flag":  "🇬🇧",
    },

    # ── 🇺🇸 American ─────────────────────────────────────────────
    "us_christopher": {
        "edge":  "en-US-ChristopherNeural",
        "rate":  "-16%",
        "pitch": "-10Hz",
        "label": "Christopher — Deep American Male",
        "desc":  "🇺🇸 Deep, authoritative. Documentary narrator.",
        "flag":  "🇺🇸",
    },
    "us_andrew": {
        "edge":  "en-US-AndrewNeural",
        "rate":  "-14%",
        "pitch": "-6Hz",
        "label": "Andrew — Calm American Male",
        "desc":  "🇺🇸 Calm, confident. Ryan Holiday style.",
        "flag":  "🇺🇸",
    },
    "us_eric": {
        "edge":  "en-US-EricNeural",
        "rate":  "-16%",
        "pitch": "-8Hz",
        "label": "Eric — Authoritative American Male",
        "desc":  "🇺🇸 Strong, clear. Great for motivational.",
        "flag":  "🇺🇸",
    },

    # ── 🇮🇳 Indian English ───────────────────────────────────────
    "in_prabhat": {
        "edge":  "en-IN-PrabhatNeural",
        "rate":  "-15%",
        "pitch": "-8Hz",
        "label": "Prabhat — Deep Indian Male",
        "desc":  "🇮🇳 Deep, resonant. Philosophical gravitas.",
        "flag":  "🇮🇳",
    },
    "in_neerja": {
        "edge":  "en-IN-NeerjaExpressiveNeural",
        "rate":  "-12%",
        "pitch": "-4Hz",
        "label": "Neerja — Expressive Indian Female",
        "desc":  "🇮🇳 Expressive, warm. Unique accent.",
        "flag":  "🇮🇳",
    },

    # ── 🇦🇺 Australian ───────────────────────────────────────────
    "au_william": {
        "edge":  "en-AU-WilliamMultilingualNeural",
        "rate":  "-15%",
        "pitch": "-8Hz",
        "label": "William — Deep Australian Male",
        "desc":  "🇦🇺 Deep, grounded. Nature documentary feel.",
        "flag":  "🇦🇺",
    },

    # ── 🇮🇪 Irish ────────────────────────────────────────────────
    "ie_connor": {
        "edge":  "en-IE-ConnorNeural",
        "rate":  "-15%",
        "pitch": "-8Hz",
        "label": "Connor — Gravitas Irish Male",
        "desc":  "🇮🇪 Poetic, profound. Celtic depth.",
        "flag":  "🇮🇪",
    },
}

DEFAULT_VOICE = "gb_ryan"
SAMPLE_RATE   = 24000

# ── Legacy key map (backward compat) ────────────────────────────
_LEGACY_MAP = {
    "af_bella":               "us_andrew",
    "bm_george":              "gb_ryan",
    "am_adam":                "us_christopher",
    "bf_emma":                "gb_sonia",
    "af_sarah":               "us_andrew",
    "am_michael":             "us_eric",
    "us_male_deep":           "us_christopher",
    "us_male_calm":           "us_andrew",
    "us_female_warm":         "us_andrew",
    "us_female_clear":        "us_andrew",
    "gb_male_rich":           "gb_ryan",
    "gb_male_warm":           "gb_thomas",
    "gb_female_elegant":      "gb_sonia",
    "in_female_expressive":   "in_neerja",
    "in_female_clear":        "in_neerja",
    "in_male_deep":           "in_prabhat",
    "au_female":              "au_william",
    "au_male":                "au_william",
    "ca_female":              "us_andrew",
    "ca_male":                "us_andrew",
    "ie_male":                "ie_connor",
}


class TTSEngine:
    """
    Microsoft Edge Neural TTS + FFmpeg professional audio chain.

    Philosophy YouTube voice sound achieved via:
      - Slow rate (-14% to -18%) for deliberate Stoic pacing
      - Low pitch (-6Hz to -12Hz) for gravitas and authority
      - FFmpeg: HPF + bass warmth + compression + loudnorm
    """

    def __init__(self, voice: str = DEFAULT_VOICE):
        resolved = VOICE_PRESETS.get(voice) or VOICE_PRESETS.get(_LEGACY_MAP.get(voice, ""))
        if not resolved:
            logger.warning(f"[TTS] Unknown voice '{voice}' — using default {DEFAULT_VOICE}")
            resolved = VOICE_PRESETS[DEFAULT_VOICE]
            voice = DEFAULT_VOICE

        self.voice_key   = voice if voice in VOICE_PRESETS else _LEGACY_MAP.get(voice, DEFAULT_VOICE)
        self.edge_voice  = resolved["edge"]
        self.rate        = resolved["rate"]
        self.pitch       = resolved["pitch"]
        self.sample_rate = SAMPLE_RATE

        logger.info(
            f"[TTS] {resolved['flag']} {resolved['label']} "
            f"| rate={self.rate} pitch={self.pitch}"
        )

    def synthesize(self, script_data: dict, output_path: str) -> str:
        """
        Synthesizes all beats into a single WAV with professional audio processing.

        Args:
            script_data: Script dict with 'beats' list
            output_path: Final WAV path

        Returns:
            str: Path to saved WAV
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

        # Step 1: Synthesize raw TTS
        raw_path = output_path.replace(".wav", "_raw.wav")
        loop.run_until_complete(self._synthesize_raw(beats, raw_path))

        # Step 2: Apply FFmpeg philosophy voice chain
        self._apply_voice_chain(raw_path, output_path)

        try:
            os.unlink(raw_path)
        except Exception:
            pass

        return output_path

    async def _synthesize_raw(self, beats: list, output_path: str) -> str:
        """Synthesize all beats into a single raw WAV (no processing yet)."""
        import edge_tts

        segments = []
        # Pause durations tuned for philosophy — longer pauses feel more profound
        pauses = {
            "hook":    np.zeros(int(self.sample_rate * 1.0), dtype=np.float32),
            "close":   np.zeros(int(self.sample_rate * 1.0), dtype=np.float32),
            "insight": np.zeros(int(self.sample_rate * 0.7), dtype=np.float32),
            "reframe": np.zeros(int(self.sample_rate * 0.7), dtype=np.float32),
            "pain":    np.zeros(int(self.sample_rate * 0.5), dtype=np.float32),
            "action":  np.zeros(int(self.sample_rate * 0.4), dtype=np.float32),
            "default": np.zeros(int(self.sample_rate * 0.5), dtype=np.float32),
        }

        for i, beat in enumerate(beats):
            text = self._clean_text(beat.get("text", "").strip())
            if not text:
                continue

            intent = beat.get("intent", "default")
            logger.debug(f"[TTS] Beat {i+1}/{len(beats)}: '{text}'")

            try:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp_mp3 = tmp.name
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_wav = tmp.name

                # Synthesize MP3 via edge-tts
                comm = edge_tts.Communicate(
                    text=text,
                    voice=self.edge_voice,
                    rate=self.rate,
                    pitch=self.pitch,
                    volume="+0%",
                )
                await comm.save(tmp_mp3)

                # Convert MP3 → WAV via FFmpeg (more reliable than soundfile MP3)
                subprocess.run([
                    "ffmpeg", "-i", tmp_mp3,
                    "-ar", str(self.sample_rate),
                    "-ac", "1",
                    tmp_wav, "-y",
                ], capture_output=True, check=True)

                audio, _ = sf.read(tmp_wav, dtype="float32")
                if audio.ndim > 1:
                    audio = audio.mean(axis=1)

                segments.append(audio)
                segments.append(pauses.get(intent, pauses["default"]))

                logger.info(f"[TTS] Beat {i+1}: {len(audio)/self.sample_rate:.2f}s")

            except Exception as e:
                logger.warning(f"[TTS] Beat {i+1} attempt 1 failed: {e} — retrying")
                # Retry once before giving up
                try:
                    import asyncio as _asyncio
                    await _asyncio.sleep(1.0)  # Brief wait before retry
                    comm2 = edge_tts.Communicate(
                        text=text, voice=self.edge_voice,
                        rate=self.rate, pitch=self.pitch, volume="+0%",
                    )
                    await comm2.save(tmp_mp3)
                    subprocess.run([
                        "ffmpeg", "-i", tmp_mp3,
                        "-ar", str(self.sample_rate), "-ac", "1",
                        tmp_wav, "-y",
                    ], capture_output=True, check=True)
                    audio, _ = sf.read(tmp_wav, dtype="float32")
                    if audio.ndim > 1: audio = audio.mean(axis=1)
                    segments.append(audio)
                    segments.append(pauses.get(intent, pauses["default"]))
                    logger.info(f"[TTS] Beat {i+1}: retry OK")
                except Exception as e2:
                    logger.error(f"[TTS] Beat {i+1} SKIPPED after retry: {e2}")
                    # Add silence placeholder so timing stays aligned
                    segments.append(pauses.get("default", pauses["default"]) * 6)
            finally:
                for p in [tmp_mp3, tmp_wav]:
                    try: os.unlink(p)
                    except: pass

        if not segments:
            raise RuntimeError("[TTS] No audio produced")

        full = np.concatenate(segments).astype(np.float32)
        raw_dur = len(full) / self.sample_rate
        sf.write(output_path, full, self.sample_rate, format="WAV")
        logger.info(f"[TTS] Raw audio: {raw_dur:.2f}s ({len(beats)} beats) -> {output_path}")
        return output_path

    def _apply_voice_chain(self, input_path: str, output_path: str):
        """
        FFmpeg professional philosophy voice chain:

          HPF(80Hz)                — remove sub-bass rumble
          equalizer(120Hz, +6dB)  — add bass body and warmth
          equalizer(250Hz, -3dB)  — cut boxy mid frequencies
          equalizer(3000Hz, +2dB) — presence boost, cuts through music
          acompressor(4:1)        — dynamic compression
          volume(2.5)             — loud and authoritative
          loudnorm(-14 LUFS)      — YouTube broadcast standard

        This chain replicates what Daily Stoic / Einzelgänger use.
        """
        af_chain = (
            # 1. Remove sub-bass rumble
            "highpass=f=80,"
            # 2. Bass body — warmth and depth at 120Hz
            "equalizer=f=120:t=q:w=1.5:g=6,"
            # 3. Cut boxiness at 250Hz
            "equalizer=f=250:t=q:w=1:g=-3,"
            # 4. Presence boost — voice cuts through background music
            "equalizer=f=3000:t=q:w=2:g=2,"
            # 5. Dynamic compression — even out dynamics
            "acompressor=threshold=-18dB:ratio=4:attack=5:release=80:makeup=4dB,"
            # 6. Volume — loud and commanding
            "volume=2.5,"
            # 7. Loudness normalization to YouTube standard (-14 LUFS)
            "loudnorm=I=-14:TP=-1.5:LRA=7"
        )

        # Scale timeout with audio duration for long-form videos
        # loudnorm runs 2 passes: long audio = more processing time
        import soundfile as sf_probe
        try:
            info = sf_probe.info(input_path)
            audio_dur = info.duration
        except Exception:
            audio_dur = 60.0  # Conservative default
        timeout_s = max(120, int(audio_dur * 1.5) + 60)

        cmd = [
            "ffmpeg", "-i", input_path,
            "-af", af_chain,
            "-ar", "44100",
            "-ac", "1",
            output_path, "-y",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            logger.warning(f"[TTS] Voice chain timed out ({timeout_s}s) — using simple chain")
            result = type('obj', (object,), {'returncode': 1, 'stderr': 'timeout'})()

        if result.returncode != 0:
            logger.warning(f"[TTS] Voice chain failed: {result.stderr[-300:]}")
            # Fallback: just copy with volume boost
            subprocess.run([
                "ffmpeg", "-i", input_path,
                "-af", "volume=2.5,loudnorm=I=-14:TP=-1.5",
                "-ar", "44100", "-ac", "1",
                output_path, "-y",
            ], capture_output=True, check=False, timeout=timeout_s)

        logger.info(f"[TTS] Voice chain applied ({audio_dur:.1f}s) -> {output_path}")

    def _clean_text(self, text: str) -> str:
        """
        Cleans text for natural TTS:
        - Strip philosopher names at end of sentence (", Epictetus" or " Epictetus")
        - Remove commas (cause robotic pauses in TTS)
        - Ensure period at end
        """
        STRIP_NAMES = [
            "Epictetus", "Seneca", "Marcus Aurelius", "Aurelius",
            "Stoics", "Stoic", "Zeno", "Chrysippus", "Cleanthes",
        ]
        # Strip names at the very end (with or without comma before)
        for name in STRIP_NAMES:
            for suffix in [f", {name}", f" {name}"]:
                if text.endswith(suffix):
                    text = text[: -len(suffix)]

        # Remove all commas — they cause robotic pauses in TTS
        text = text.replace(",", "")

        text = text.strip()
        if text and text[-1] not in ".!?":
            text += "."

        return text


def get_voice_list() -> list:
    """Returns all 10 voices for the frontend."""
    return [
        {
            "id":    key,
            "label": preset["label"],
            "desc":  preset["desc"],
            "flag":  preset["flag"],
            "edge":  preset["edge"],
        }
        for key, preset in VOICE_PRESETS.items()
    ]
