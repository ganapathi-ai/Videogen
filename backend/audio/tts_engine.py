"""
THE INNER CITADEL — TTS Engine (CPU Mode)
Kokoro-82M runs entirely on CPU — works on Intel integrated graphics.
30GB RAM is more than enough (model uses ~300MB).
"""

import os
import numpy as np
import soundfile as sf
from pathlib import Path
from loguru import logger


VOICE_PRESETS = {
    "af_bella":  {"style": "warm",      "desc": "Bella — Warm American Female"},
    "bm_george": {"style": "resonant",  "desc": "George — Deep British Male"},
    "am_adam":   {"style": "confident", "desc": "Adam — Confident American Male"},
    "bf_emma":   {"style": "elegant",   "desc": "Emma — Elegant British Female"},
    "af_sarah":  {"style": "clear",     "desc": "Sarah — Clear American Female"},
    "am_michael":{"style": "deep",      "desc": "Michael — Deep American Male"},
}


class TTSEngine:
    """
    Kokoro-82M TTS — CPU Mode.
    Intel graphics do not support CUDA. This engine forces CPU.
    30GB RAM provides ample headroom for the 300MB model.
    """

    def __init__(self, voice: str = "af_bella"):
        self.voice = voice if voice in VOICE_PRESETS else "af_bella"
        self.sample_rate = 24000
        self._pipeline = None
        logger.info(f"[TTS] Voice: {VOICE_PRESETS[self.voice]['desc']} | Device: CPU")

    def _load(self):
        """Lazy-load Kokoro pipeline on first call (kokoro 0.7.x for Python 3.13)."""
        if self._pipeline is not None:
            return
        try:
            # Force CPU — no CUDA
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
            from kokoro import KPipeline
            # kokoro 0.7.x: no device param — always CPU when CUDA not available
            self._pipeline = KPipeline(lang_code="a")
            logger.info("[TTS] Kokoro 0.7.x loaded on CPU")
        except ImportError:
            raise ImportError(
                "Kokoro not installed. Run:\n"
                "  pip install kokoro==0.7.16 soundfile\n"
                "The model (~300MB) downloads automatically on first use."
            )

    def synthesize(self, script_data: dict, output_path: str) -> str:
        """
        Synthesizes all script beats into a single WAV file.
        Adds 0.4s natural pause between beats.

        Args:
            script_data: Script dict from ScriptEngine
            output_path: Where to save the WAV

        Returns:
            str: Path to saved WAV
        """
        self._load()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Build full narration text from beats
        beats = script_data.get("beats", [])
        if not beats:
            raise ValueError("Script has no beats — cannot synthesize audio")

        segments = []
        silence_04s = np.zeros(int(self.sample_rate * 0.4), dtype=np.float32)
        silence_08s = np.zeros(int(self.sample_rate * 0.8), dtype=np.float32)

        for i, beat in enumerate(beats):
            text = beat.get("text", "").strip()
            if not text:
                continue

            intent = beat.get("intent", "")
            logger.debug(f"[TTS] Beat {i+1}: '{text[:50]}...'")

            try:
                # kokoro 0.7.x API: generator yields (graphemes, phonemes, audio)
                audio_chunks = []
                generator = self._pipeline(
                    text,
                    voice=self.voice,
                    speed=0.88
                )
                for gs, ps, audio in generator:
                    if audio is not None and len(audio) > 0:
                        audio_chunks.append(
                            audio if isinstance(audio, np.ndarray)
                            else np.array(audio, dtype=np.float32)
                        )

                if audio_chunks:
                    beat_audio = np.concatenate(audio_chunks).astype(np.float32)
                    segments.append(beat_audio)

                    # Longer pause after hook and close beats
                    if intent in ("hook", "close"):
                        segments.append(silence_08s)
                    else:
                        segments.append(silence_04s)

            except Exception as e:
                logger.warning(f"[TTS] Beat {i+1} failed: {e} — skipping")

        if not segments:
            raise RuntimeError("TTS produced no audio segments")

        full_audio = np.concatenate(segments)

        # Normalize to prevent clipping
        max_val = np.abs(full_audio).max()
        if max_val > 0:
            full_audio = full_audio / max_val * 0.92

        sf.write(output_path, full_audio, self.sample_rate, format="WAV")
        duration = len(full_audio) / self.sample_rate
        logger.info(f"[TTS] ✅ Synthesized {len(beats)} beats → {duration:.2f}s → {output_path}")
        return output_path
