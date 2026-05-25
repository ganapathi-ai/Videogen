"""
THE INNER CITADEL — Audio Mixer (MoviePy 2.x compatible)
Emotion-based background music ducking.
Narration always dominant; BGM dynamically scales based on segment emotion.
"""

import os
from pathlib import Path
from loguru import logger


class AudioMixer:
    """
    Mixes voice narration with background music using emotion-based ducking.
    Uses FFmpeg directly for Python 3.13 + MoviePy 2.x compatibility.
    """

    DUCK_MAP = {
        "minimal":    0.12,
        "focus":      0.12,
        "deep":       0.20,
        "emotional":  0.25,
        "modern":     0.22,
        "resolute":   0.18,
        "inspiring":  0.28,
        "steady":     0.15,
        "reassuring": 0.18,
    }
    DEFAULT_DUCK = 0.22

    def mix(self, voice_path: str, bgm_path: str, timeline: dict,
            output_path: str = "exports/audio_mixed.wav") -> str:
        """
        Mixes voice + background music using FFmpeg directly.
        More reliable than MoviePy audio on Python 3.13 Windows.

        Args:
            voice_path:  Path to narration .wav
            bgm_path:    Path to background music file (.mp3 or .wav)
            timeline:    Master timeline (for per-segment emotion)
            output_path: Where to write the mixed audio

        Returns:
            str: Path to mixed audio file
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        logger.info(f"[AudioMixer] Voice: {voice_path}")
        logger.info(f"[AudioMixer] BGM:   {bgm_path}")

        # If no BGM file — output voice only (copy)
        if not bgm_path or not Path(bgm_path).exists():
            logger.warning("[AudioMixer] No BGM file — using voice only")
            import shutil
            shutil.copy2(voice_path, output_path)
            return output_path

        # Compute average duck level from timeline segments
        segments = timeline.get("segments", [])
        if segments:
            emotions = [s.get("emotion", "deep") for s in segments]
            avg_duck = sum(self.DUCK_MAP.get(e, self.DEFAULT_DUCK) for e in emotions) / len(emotions)
        else:
            avg_duck = self.DEFAULT_DUCK

        logger.info(f"[AudioMixer] Average BGM duck level: {avg_duck:.2f}")

        # Use FFmpeg to mix: voice at full volume + BGM ducked
        import subprocess
        cmd = [
            "ffmpeg",
            "-i", voice_path,
            "-stream_loop", "-1",   # Loop BGM if shorter than voice
            "-i", bgm_path,
            "-filter_complex",
            (
                f"[1:a]volume={avg_duck:.3f},afade=t=out:st=0:d=2[bgm];"
                f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[out]"
            ),
            "-map", "[out]",
            "-ac", "2",
            "-ar", "44100",
            "-shortest",
            output_path,
            "-y",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.warning(f"[AudioMixer] FFmpeg mix failed: {result.stderr[-200:]}")
            logger.warning("[AudioMixer] Falling back to voice-only output")
            import shutil
            shutil.copy2(voice_path, output_path)
        else:
            logger.info(f"[AudioMixer] Mixed audio: {output_path}")

        return output_path
