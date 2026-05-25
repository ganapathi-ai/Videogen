"""
THE INNER CITADEL — Audio Mixer
Emotion-based background music ducking.
Narration always dominant; BGM dynamically scales based on segment emotion.
"""

import os
from pathlib import Path
from loguru import logger


class AudioMixer:
    """
    Mixes voice narration with background music using emotion-based ducking.

    Ducking levels (per research spec):
    - minimal / focus: 0.15x BGM volume (quiet = deep focus)
    - All others:      0.25x BGM volume (light presence)
    - 2s fade-out at end
    """

    # Emotion → BGM volume multiplier
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
        Mixes voice + background music with emotion-based ducking per segment.

        Args:
            voice_path:  Path to narration .wav
            bgm_path:    Path to background music file (.mp3 or .wav)
            timeline:    Master timeline (for per-segment emotion-based ducking)
            output_path: Where to write the mixed audio

        Returns:
            str: Path to mixed audio file
        """
        try:
            import moviepy.editor as mp
            import moviepy.audio.fx.all as afx
        except ImportError:
            raise ImportError("Run: pip install moviepy")

        logger.info(f"[AudioMixer] Voice: {voice_path}")
        logger.info(f"[AudioMixer] BGM:   {bgm_path}")

        voice = mp.AudioFileClip(voice_path)
        total_duration = voice.duration

        # Handle missing or silent BGM
        if not bgm_path or not Path(bgm_path).exists():
            logger.warning("[AudioMixer] No BGM file found — outputting voice only")
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            voice.write_audiofile(output_path, fps=44100, logger=None)
            voice.close()
            return output_path

        bgm_raw = mp.AudioFileClip(bgm_path)

        # Loop BGM if shorter than narration
        if bgm_raw.duration < total_duration:
            loops = int(total_duration / bgm_raw.duration) + 2
            bgm_raw = mp.concatenate_audioclips([bgm_raw] * loops)
        bgm_raw = bgm_raw.subclip(0, total_duration)

        # Normalize both tracks
        bgm_raw = afx.audio_normalize(bgm_raw)
        voice = afx.audio_normalize(voice)

        # ─── Per-segment emotion-based ducking ────────────────────
        segments = timeline.get("segments", [])
        ducked_clips = []

        if segments:
            prev_end = 0.0
            for seg in segments:
                seg_start = seg.get("audio_start", prev_end)
                seg_end = seg.get("audio_end", seg_start + 3.0)
                emotion = seg.get("emotion", "deep")
                vol = self.DUCK_MAP.get(emotion, self.DEFAULT_DUCK)

                # Handle any gap before this segment
                if seg_start > prev_end + 0.05:
                    gap_clip = bgm_raw.subclip(prev_end, seg_start).volumex(self.DEFAULT_DUCK)
                    ducked_clips.append(gap_clip)

                seg_bgm = bgm_raw.subclip(seg_start, min(seg_end, total_duration)).volumex(vol)
                ducked_clips.append(seg_bgm)
                prev_end = seg_end

            # Remaining audio after last segment
            if prev_end < total_duration:
                tail = bgm_raw.subclip(prev_end, total_duration).volumex(self.DEFAULT_DUCK)
                ducked_clips.append(tail)

            ducked_bgm = mp.concatenate_audioclips(ducked_clips)
        else:
            # No segments: uniform ducking
            ducked_bgm = bgm_raw.volumex(self.DEFAULT_DUCK)

        # Fade out BGM in last 2 seconds
        ducked_bgm = afx.audio_fadeout(ducked_bgm, duration=2.0)

        # Mix voice + ducked BGM
        final_mix = mp.CompositeAudioClip([ducked_bgm, voice])

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        final_mix.write_audiofile(output_path, fps=44100, logger=None)

        # Cleanup
        voice.close()
        bgm_raw.close()
        ducked_bgm.close()
        final_mix.close()

        logger.info(f"[AudioMixer] ✅ Mixed audio: {output_path} ({total_duration:.2f}s)")
        return output_path
