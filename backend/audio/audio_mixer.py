"""
THE INNER CITADEL — Audio Mixer (Professional Philosophy BGM Ducking)

Philosophy YouTube BGM mixing (Daily Stoic / Einzelgänger style):

  Voice: Full volume, already processed through 7-stage chain
  BGM:   - HP filter @500Hz (clears bass for voice — no frequency clash)
         - Volume: 8-15% (emotion-based) — barely perceptible but present
         - Fade in: 1.5s (smooth entry)
         - Fade out: 3s (graceful exit)
         - Looped seamlessly if shorter than narration

FFmpeg filter_complex chain:
  [BGM] → volume → HP filter → fade in → fade out → loop
  [BGM + Voice] → amix → output

Professional touch: BGM sits BELOW 500Hz, voice ABOVE — no competition.
"""

import os
import subprocess
from pathlib import Path
from loguru import logger


class AudioMixer:
    """
    Professional philosophy-style BGM mixer.
    BGM is EQ'd to sit below voice, ducked to 8-15%, faded in/out.
    """

    # Per-emotion BGM duck levels (% of original volume)
    # Research: Philosophy YouTube uses 8-12% BGM under narration
    DUCK_MAP = {
        "minimal":    0.09,   # Very quiet — near-silent background
        "focus":      0.09,
        "steady":     0.10,
        "deep":       0.12,   # Subtle presence
        "reassuring": 0.12,
        "modern":     0.13,
        "resolute":   0.13,
        "emotional":  0.15,   # Slightly more present on emotional beats
        "inspiring":  0.15,
        "action":     0.14,
    }
    DEFAULT_DUCK = 0.12

    def mix(self, voice_path: str, bgm_path: str, timeline: dict,
            output_path: str = "exports/audio_mixed.wav") -> str:
        """
        Mixes processed voice narration with Stoic BGM.

        Processing applied to BGM:
          1. HP filter @500Hz  — BGM only in upper-mid/high, no bass clash
          2. Volume duck       — 8-15% (emotion-weighted average)
          3. Fade in 1.5s      — smooth BGM entry
          4. Fade out 3s       — graceful BGM exit at end
          5. Loop if needed    — BGM shorter than narration

        Args:
            voice_path:  Processed narration WAV (already has bass chain applied)
            bgm_path:    BGM track path (MP3 or WAV)
            timeline:    Master timeline (for emotion-weighted duck)
            output_path: Mixed output WAV path
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        logger.info(f"[Mixer] Voice: {voice_path}")
        logger.info(f"[Mixer] BGM:   {bgm_path}")

        if not bgm_path or not Path(bgm_path).exists():
            logger.warning("[Mixer] No BGM file — voice-only output")
            import shutil
            shutil.copy2(voice_path, output_path)
            return output_path

        # Compute emotion-weighted average duck level
        segments   = timeline.get("segments", [])
        total_dur  = timeline.get("duration", 30.0)
        fade_out_t = max(0, total_dur - 3.0)

        if segments:
            weighted_sum = 0.0
            total_weight = 0.0
            for seg in segments:
                dur     = seg.get("audio_end", 0) - seg.get("audio_start", 0)
                emotion = seg.get("emotion", "deep")
                level   = self.DUCK_MAP.get(emotion, self.DEFAULT_DUCK)
                weighted_sum += level * dur
                total_weight += dur
            avg_duck = weighted_sum / max(total_weight, 1.0)
        else:
            avg_duck = self.DEFAULT_DUCK

        logger.info(f"[Mixer] BGM duck level: {avg_duck:.3f} ({avg_duck*100:.1f}%)")

        # Professional FFmpeg mix:
        # [1:a] = BGM track
        # - stream_loop: loop BGM if shorter than voice
        # - highpass f=500: cut bass from BGM (leaves bass to voice chain)
        # - volume: duck to emotion-weighted level
        # - afade in: 1.5s smooth start
        # - afade out: 3s smooth end
        # [0:a] = voice (full volume)
        # amix: blend, voice duration is master

        filter_complex = (
            f"[1:a]"
            f"highpass=f=500,"                          # Cut BGM bass (no clash with voice)
            f"volume={avg_duck:.4f},"                    # Duck to emotion level
            f"afade=t=in:st=0:d=1.5,"                   # Fade in over 1.5s
            f"afade=t=out:st={fade_out_t:.3f}:d=3"      # Fade out 3s before end
            f"[bgm];"
            f"[0:a][bgm]amix=inputs=2:duration=first:"  # Mix, voice is master duration
            f"dropout_transition=2[out]"
        )

        cmd = [
            "ffmpeg",
            "-i", voice_path,
            "-stream_loop", "-1",   # Loop BGM indefinitely
            "-i", bgm_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-ac", "2",             # Stereo output
            "-ar", "44100",
            "-shortest",
            output_path,
            "-y",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.warning(f"[Mixer] FFmpeg mix failed: {result.stderr[-300:]}")
            logger.warning("[Mixer] Trying simple fallback mix...")
            self._simple_mix(voice_path, bgm_path, avg_duck, output_path)
        else:
            logger.info(f"[Mixer] Mixed: {output_path}")

        return output_path

    def _simple_mix(self, voice: str, bgm: str, duck: float, out: str):
        """Simple fallback mix without filter_complex (wider FFmpeg compat)."""
        cmd = [
            "ffmpeg",
            "-i", voice,
            "-stream_loop", "-1",
            "-i", bgm,
            "-filter_complex",
            f"[1:a]volume={duck:.4f}[b];[0:a][b]amix=inputs=2:duration=first[o]",
            "-map", "[o]",
            "-ac", "2", "-ar", "44100",
            "-shortest", out, "-y",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"[Mixer] Simple mix also failed — voice only")
            import shutil
            shutil.copy2(voice, out)
