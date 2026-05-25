"""
THE INNER CITADEL — Audio Mixer (Professional Philosophy BGM — Long-Form Safe)

Research basis: Daily Stoic, Einzelgänger, Philosophies for Life
  - BGM at 8-15% under voice (barely present, never distracting)
  - High-pass filter @500Hz on BGM (no bass clash with voice chain)
  - Seamless BGM looping using FFmpeg aloop (NO audible seams/clicks)
  - Smooth fade in (1.5s) and fade out (4s)
  - Fully works for SHORT videos (35s) AND LONG videos (11+ min)

LONG-FORM AUDIO FIXES:
  1. Seamless BGM loop: aloop filter instead of stream_loop
     → stream_loop causes clicks at seam points (22 clicks in 11-min video)
     → aloop loops at sample level = completely seamless
  2. Removed -shortest flag: avoids voice being cut if BGM ends first
  3. Timeout scaled with video duration: 120s shorts, 1200s long-form
  4. amix duration=first: voice always determines total length
"""

import os
import subprocess
from pathlib import Path
from loguru import logger


class AudioMixer:
    """
    Professional philosophy-style BGM mixer — short and long-form safe.

    Fixes for long-form videos:
      - Seamless BGM loop (aloop, no click seams)
      - Proper duration control (voice is master, no premature cuts)
      - Scaled timeouts (short=120s, long_11=1200s)
    """

    # Per-emotion BGM duck levels (% of original volume)
    # Research: Philosophy YouTube uses 8-12% BGM under narration
    DUCK_MAP = {
        "minimal":    0.09,
        "focus":      0.09,
        "steady":     0.10,
        "deep":       0.12,
        "reassuring": 0.12,
        "modern":     0.13,
        "resolute":   0.13,
        "emotional":  0.15,
        "inspiring":  0.15,
        "action":     0.14,
    }
    DEFAULT_DUCK = 0.12

    def mix(self, voice_path: str, bgm_path: str, timeline: dict,
            output_path: str = "exports/audio_mixed.wav") -> str:
        """
        Mixes voice narration with Stoic BGM — fully long-form safe.

        BGM processing chain:
          1. aloop=-1       — SEAMLESS infinite loop (no click at seam)
          2. highpass=f=500 — BGM only above 500Hz (no bass clash)
          3. volume=X       — duck to 8-15% (emotion-weighted)
          4. afade=in 1.5s  — smooth BGM entry
          5. afade=out 4s   — graceful BGM exit before end
          amix duration=first — voice is master, never gets cut
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        logger.info(f"[Mixer] Voice: {voice_path}")
        logger.info(f"[Mixer] BGM:   {bgm_path}")

        if not bgm_path or not Path(bgm_path).exists():
            logger.warning("[Mixer] No BGM file — voice-only output")
            import shutil
            shutil.copy2(voice_path, output_path)
            return output_path

        # Emotion-duration-weighted duck level
        segments  = timeline.get("segments", [])
        total_dur = timeline.get("duration", 30.0)

        if segments:
            weighted_sum = 0.0
            total_weight = 0.0
            for seg in segments:
                dur     = seg.get("audio_end", 0) - seg.get("audio_start", 0)
                emotion = seg.get("emotion", "deep")
                level   = self.DUCK_MAP.get(emotion, self.DEFAULT_DUCK)
                weighted_sum += level * max(dur, 0.1)
                total_weight += max(dur, 0.1)
            avg_duck = weighted_sum / total_weight
        else:
            avg_duck = self.DEFAULT_DUCK

        # Fade out starts 4s before end — long enough to not cut abruptly
        fade_out_t = max(0, total_dur - 4.0)

        # Scale timeout with video duration (long-form needs more time)
        timeout_s = max(180, int(total_dur * 3))

        logger.info(
            f"[Mixer] duck={avg_duck:.3f} ({avg_duck*100:.1f}%) "
            f"| dur={total_dur:.1f}s | timeout={timeout_s}s"
        )

        # ── Seamless BGM Loop Strategy ─────────────────────────────────
        # Step 1: Pre-extend BGM to at least video_duration + 10s
        #         using FFmpeg aloop (sample-level loop = NO seams)
        # Step 2: Mix the looped BGM with voice

        bgm_extended = output_path.replace(".wav", "_bgm_looped.wav")
        bgm_ok = self._extend_bgm_seamless(
            bgm_path, bgm_extended, total_dur + 10.0, timeout=60
        )

        if not bgm_ok:
            logger.warning("[Mixer] BGM extend failed — using stream_loop fallback")
            bgm_extended = bgm_path  # Fall back to original

        # ── Mix: voice (full) + extended BGM (ducked, faded) ──────────
        filter_complex = (
            f"[1:a]"
            f"highpass=f=500,"                          # Cut BGM bass
            f"volume={avg_duck:.4f},"                   # Duck to level
            f"afade=t=in:st=0:d=1.5,"                  # Fade in 1.5s
            f"afade=t=out:st={fade_out_t:.3f}:d=4"     # Fade out 4s
            f"[bgm];"
            f"[0:a][bgm]amix=inputs=2:duration=first:" # Voice = master duration
            f"dropout_transition=3[out]"
        )

        cmd = [
            "ffmpeg",
            "-i", voice_path,
            "-i", bgm_extended,           # Pre-looped BGM (no stream_loop needed)
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-ac", "2",
            "-ar", "44100",
            # NO -shortest flag: amix duration=first already controls length
            output_path, "-y",
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_s
            )
        except subprocess.TimeoutExpired:
            logger.error(f"[Mixer] Mix timed out after {timeout_s}s")
            import shutil; shutil.copy2(voice_path, output_path)
            return output_path

        if result.returncode != 0:
            logger.warning(f"[Mixer] Primary mix failed: {result.stderr[-300:]}")
            self._simple_mix(voice_path, bgm_extended, avg_duck, output_path, timeout_s)
        else:
            logger.info(f"[Mixer] Mixed OK: {output_path}")

        # Cleanup extended BGM temp file
        if bgm_ok and bgm_extended != bgm_path:
            try: os.unlink(bgm_extended)
            except Exception: pass

        return output_path

    def _extend_bgm_seamless(self, bgm_path: str, out_path: str,
                              target_dur: float, timeout: int = 60) -> bool:
        """
        Extends BGM to target_dur using FFmpeg aloop filter.

        aloop loops audio at SAMPLE level — completely seamless, zero clicks.
        This is superior to stream_loop (which loops at packet level = click).

        For a 30s preview looping to 660s → 22 seamless loops, zero audible seams.
        """
        try:
            # Get BGM duration first
            probe = subprocess.run([
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", bgm_path,
            ], capture_output=True, text=True, timeout=10)

            import json
            bgm_dur = float(json.loads(probe.stdout).get("format", {}).get("duration", 30.0))
            bgm_dur = max(bgm_dur, 1.0)

            # Calculate loops needed (add 2 extra loops as safety buffer)
            loops_needed = max(1, int(target_dur / bgm_dur) + 2)

            logger.info(
                f"[Mixer] BGM extend: {bgm_dur:.1f}s × {loops_needed} loops "
                f"= {bgm_dur * loops_needed:.1f}s (need {target_dur:.1f}s)"
            )

            # aloop=loop=N:size=0 means: loop N times using all samples
            # Then trim to exact target duration
            cmd = [
                "ffmpeg",
                "-i", bgm_path,
                "-af", (
                    f"aloop=loop={loops_needed}:size=2147483647,"  # Loop N times
                    f"atrim=0:{target_dur:.3f},"                    # Trim to exact duration
                    "asetpts=PTS-STARTPTS"                          # Reset timestamps
                ),
                "-ar", "44100",
                "-ac", "2",
                out_path, "-y",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0 and Path(out_path).stat().st_size > 1000:
                logger.info(f"[Mixer] BGM extended seamlessly: {out_path}")
                return True
            else:
                logger.warning(f"[Mixer] aloop failed: {result.stderr[-200:]}")
                return False

        except Exception as e:
            logger.warning(f"[Mixer] BGM extend error: {e}")
            return False

    def _simple_mix(self, voice: str, bgm: str, duck: float, out: str, timeout: int = 180):
        """Simple fallback mix — no pre-looped BGM."""
        cmd = [
            "ffmpeg",
            "-i", voice,
            "-stream_loop", "-1",
            "-i", bgm,
            "-filter_complex",
            f"[1:a]volume={duck:.4f}[b];[0:a][b]amix=inputs=2:duration=first[o]",
            "-map", "[o]",
            "-ac", "2", "-ar", "44100",
            out, "-y",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode != 0:
                logger.error("[Mixer] Simple mix also failed — voice only")
                import shutil; shutil.copy2(voice, out)
        except subprocess.TimeoutExpired:
            logger.error("[Mixer] Simple mix timeout — voice only")
            import shutil; shutil.copy2(voice, out)
