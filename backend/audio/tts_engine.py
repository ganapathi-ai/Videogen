"""
THE INNER CITADEL — TTS Engine (edge-tts)
Microsoft Edge Neural TTS — Python 3.13 compatible, no GPU, no system deps.
High-quality neural voices (same engine as Microsoft Edge browser).
Requires internet (same as Groq/Pexels API calls).
"""

import os
import asyncio
import numpy as np
import soundfile as sf
from pathlib import Path
from loguru import logger


# ── Voice map: internal name → Edge TTS voice name ───────────────
VOICE_PRESETS = {
    "af_bella":   {"edge": "en-US-JennyNeural",   "desc": "Bella — Warm American Female"},
    "bm_george":  {"edge": "en-GB-RyanNeural",    "desc": "George — Deep British Male"},
    "am_adam":    {"edge": "en-US-GuyNeural",     "desc": "Adam — Confident American Male"},
    "bf_emma":    {"edge": "en-GB-SoniaNeural",   "desc": "Emma — Elegant British Female"},
    "af_sarah":   {"edge": "en-US-AriaNeural",    "desc": "Sarah — Clear American Female"},
    "am_michael": {"edge": "en-US-DavisNeural",   "desc": "Michael — Deep American Male"},
}

SAMPLE_RATE = 24000   # edge-tts output sample rate


class TTSEngine:
    """
    Microsoft Edge Neural TTS Engine.
    Works on Python 3.13, Windows, Intel CPU — no GPU, no system libraries.
    Uses edge-tts package (wraps Microsoft Edge's neural TTS API).
    """

    def __init__(self, voice: str = "af_bella"):
        self.voice_key = voice if voice in VOICE_PRESETS else "af_bella"
        self.edge_voice = VOICE_PRESETS[self.voice_key]["edge"]
        self.sample_rate = SAMPLE_RATE
        logger.info(
            f"[TTS] Voice: {VOICE_PRESETS[self.voice_key]['desc']} "
            f"({self.edge_voice}) | Engine: edge-tts | Device: CPU"
        )

    def synthesize(self, script_data: dict, output_path: str) -> str:
        """
        Synthesizes all script beats into a single WAV file.
        Adds natural pauses between beats.

        Args:
            script_data: Script dict from ScriptEngine (has 'beats' list)
            output_path: Path to save final WAV

        Returns:
            str: Path to saved WAV file
        """
        beats = script_data.get("beats", [])
        if not beats:
            raise ValueError("[TTS] Script has no beats — cannot synthesize audio")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Run async synthesis in sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        audio_path = loop.run_until_complete(
            self._synthesize_async(beats, output_path)
        )
        return audio_path

    async def _synthesize_async(self, beats: list, output_path: str) -> str:
        """Async core: synthesize each beat and concatenate."""
        import edge_tts
        import tempfile

        segments = []
        silence_04 = np.zeros(int(self.sample_rate * 0.4), dtype=np.float32)
        silence_08 = np.zeros(int(self.sample_rate * 0.8), dtype=np.float32)

        for i, beat in enumerate(beats):
            text = beat.get("text", "").strip()
            if not text:
                continue

            intent = beat.get("intent", "")
            logger.debug(f"[TTS] Beat {i+1}/{len(beats)}: '{text[:60]}'")

            try:
                # Write beat audio to temp MP3, then read as numpy
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp_path = tmp.name

                communicate = edge_tts.Communicate(
                    text=text,
                    voice=self.edge_voice,
                    rate="-12%",    # Slightly slower = more Stoic gravitas
                    volume="+0%",
                )
                await communicate.save(tmp_path)

                # Convert MP3 → numpy float32 via soundfile
                audio, sr = sf.read(tmp_path, dtype="float32")
                os.unlink(tmp_path)   # Clean up temp file

                # Mono-mix if stereo
                if audio.ndim > 1:
                    audio = audio.mean(axis=1)

                segments.append(audio)

                # Pause after each beat
                if intent in ("hook", "close"):
                    segments.append(silence_08)
                else:
                    segments.append(silence_04)

                logger.info(f"[TTS] Beat {i+1} done: {len(audio)/self.sample_rate:.2f}s")

            except Exception as e:
                logger.warning(f"[TTS] Beat {i+1} failed: {e} — skipping")

        if not segments:
            raise RuntimeError("[TTS] No audio segments produced")

        full_audio = np.concatenate(segments).astype(np.float32)

        # Normalize to prevent clipping
        max_val = np.abs(full_audio).max()
        if max_val > 0:
            full_audio = full_audio / max_val * 0.92

        sf.write(output_path, full_audio, self.sample_rate, format="WAV")
        duration = len(full_audio) / self.sample_rate
        logger.info(
            f"[TTS] Synthesized {len(beats)} beats → {duration:.2f}s → {output_path}"
        )
        return output_path
