"""
THE INNER CITADEL — WhisperX Alignment Engine (CPU Mode)
Forces CPU device, int8 compute type for Intel systems.
30GB RAM handles whisper-base easily (~150MB model).

Falls back to character-proportion timing if WhisperX unavailable.
"""

import os
from pathlib import Path
from loguru import logger

# Force CPU — no CUDA for Intel integrated graphics
os.environ["CUDA_VISIBLE_DEVICES"] = ""


class AlignmentEngine:
    """
    Generates word-level timestamps using WhisperX on CPU.
    Uses 'base' Whisper model for speed/accuracy balance on Intel CPU.

    30GB RAM specs:
        - whisper-base: ~150MB model
        - wav2vec2 aligner: ~300MB
        - Total: ~500MB — well within 30GB
    """

    WHISPER_MODEL    = "base"         # fast on CPU, good accuracy
    COMPUTE_TYPE     = "int8"         # CPU-optimized quantization
    DEVICE           = "cpu"
    BATCH_SIZE       = 4              # Low batch size for CPU
    LANGUAGE         = "en"

    def generate_word_timestamps(self, audio_path: str) -> list:
        """
        Runs WhisperX transcription + forced alignment on CPU.

        Args:
            audio_path: Path to WAV audio file

        Returns:
            list: [{"word": str, "start": float, "end": float}, ...]
        """
        try:
            return self._whisperx_align(audio_path)
        except ImportError:
            logger.warning("[Align] WhisperX not installed — using fallback timing")
            return self._fallback_timing(audio_path)
        except Exception as e:
            logger.error(f"[Align] WhisperX failed: {e} — using fallback")
            return self._fallback_timing(audio_path)

    def _whisperx_align(self, audio_path: str) -> list:
        import whisperx

        logger.info(f"[Align] Loading whisper-{self.WHISPER_MODEL} on CPU...")
        model = whisperx.load_model(
            self.WHISPER_MODEL,
            device=self.DEVICE,
            compute_type=self.COMPUTE_TYPE,
            language=self.LANGUAGE,
        )

        logger.info("[Align] Transcribing audio...")
        audio = whisperx.load_audio(audio_path)
        result = model.transcribe(
            audio,
            batch_size=self.BATCH_SIZE,
            language=self.LANGUAGE,
        )

        logger.info("[Align] Running forced word alignment...")
        align_model, metadata = whisperx.load_align_model(
            language_code=self.LANGUAGE,
            device=self.DEVICE,
        )
        aligned = whisperx.align(
            result["segments"],
            align_model, metadata,
            audio, self.DEVICE,
            return_char_alignments=False,
        )

        # Extract flat word list
        words = []
        for seg in aligned.get("word_segments", []):
            w = seg.get("word", "").strip()
            s = seg.get("start", 0.0)
            e = seg.get("end", s + 0.2)
            if w:
                words.append({"word": w, "start": round(s, 3), "end": round(e, 3)})

        # Free memory
        del model, align_model, audio, result, aligned
        import gc; gc.collect()

        logger.info(f"[Align] ✅ WhisperX: {len(words)} words aligned")
        return words

    def _fallback_timing(self, audio_path: str) -> list:
        """
        Proportional timing fallback — no WhisperX needed.
        Distributes words evenly based on character count and audio duration.
        Accurate enough for caption sync on short clips.
        """
        import soundfile as sf
        logger.info("[Align] Using proportional fallback timing...")

        try:
            data, sr = sf.read(audio_path)
            total_duration = len(data) / sr
        except Exception:
            total_duration = 35.0

        # Read script for word list
        script_path = Path(audio_path).parent / "script.json"
        if script_path.exists():
            import json
            script = json.loads(script_path.read_text(encoding="utf-8"))
            all_text = " ".join(b.get("text", "") for b in script.get("beats", []))
        else:
            all_text = "The inner citadel cannot be touched by external forces"

        words_raw = all_text.split()
        if not words_raw:
            return []

        total_chars = sum(len(w) for w in words_raw)
        words = []
        t = 0.5  # 0.5s initial silence

        for w in words_raw:
            char_ratio = len(w) / max(total_chars, 1)
            duration = max(0.12, char_ratio * total_duration * 0.90)
            words.append({"word": w, "start": round(t, 3), "end": round(t + duration, 3)})
            t += duration + 0.04  # tiny gap between words

        logger.info(f"[Align] ✅ Fallback: {len(words)} words timed over {total_duration:.2f}s")
        return words
