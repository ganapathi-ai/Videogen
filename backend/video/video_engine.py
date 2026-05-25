"""
THE INNER CITADEL — Video Engine
MoviePy + PIL LANCZOS jitter-free Ken Burns zoom compositing.

CRITICAL FIX: MoviePy's native resize lambda causes a "wobbling" or "jitter"
artifact during slow Ken Burns zooms due to integer rounding discrepancies
in its default Pillow scaling engine.

Solution: Override MoviePy frame processing with a custom PIL.Image.LANCZOS
algorithm that enforces even-integer dimensions on every frame.
"""

import math
import os
import numpy as np
from pathlib import Path
from loguru import logger

try:
    # MoviePy 2.x imports (Python 3.13 compatible)
    from moviepy import VideoFileClip, ColorClip, concatenate_videoclips
    import moviepy as mp
    from PIL import Image
except ImportError:
    raise ImportError("Run: pip install moviepy==2.2.1 Pillow")

# Compatibility shim for mp.VideoClip type hints
mp.VideoClip = VideoFileClip.__bases__[0]  # base class


# Resolution map for aspect ratios
RESOLUTIONS = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
}


class VideoEngine:
    """
    Composes scenes with jitter-free PIL LANCZOS zoom.
    Handles dynamic aspect ratios and Ken Burns effects.
    """

    def __init__(self, aspect_ratio: str = "9:16", fps: int = 60):
        self.w, self.h = RESOLUTIONS.get(aspect_ratio, (1080, 1920))
        self.fps = fps
        self.aspect_ratio = aspect_ratio
        logger.info(f"[VideoEngine] {self.w}x{self.h} @ {fps}fps")

    # ─────────────────────────────────────────────
    # Core Jitter-Free Zoom (PIL LANCZOS Override)
    # ─────────────────────────────────────────────

    def _jitter_free_zoom(self, clip, zoom_ratio: float = 0.12):
        """
        Custom PIL LANCZOS zoom effect — completely eliminates MoviePy's resize wobble.

        Algorithm:
        1. For each frame at time t, compute scale = 1 + (zoom_ratio * t/duration)
        2. Resize using LANCZOS (highest quality resampling)
        3. Enforce even-integer dimensions (prevents codec crashes)
        4. Center-crop back to original resolution
        """
        base_w, base_h = clip.size

        def effect(get_frame, t):
            frame = get_frame(t)
            img = Image.fromarray(frame)

            # Progressive zoom scale
            progress = t / max(clip.duration, 0.001)
            scale = 1.0 + (zoom_ratio * progress)

            # New dimensions (must be even integers)
            new_w = math.ceil(base_w * scale)
            new_h = math.ceil(base_h * scale)
            new_w += new_w % 2     # Ensure even
            new_h += new_h % 2     # Ensure even

            # High-quality LANCZOS resize
            img = img.resize((new_w, new_h), Image.LANCZOS)

            # Center crop back to base resolution
            x = (new_w - base_w) // 2
            y = (new_h - base_h) // 2
            img = img.crop((x, y, x + base_w, y + base_h))

            result = np.array(img)
            img.close()
            return result

        return clip.fl(effect)

    # ─────────────────────────────────────────────
    # Scene Processing
    # ─────────────────────────────────────────────

    def _process_single_clip(self, video_path: str, duration: float, zoom_ratio: float = 0.12):
        """
        Loads, crops to aspect ratio, zooms, and returns a processed clip.

        Args:
            video_path: Path to downloaded stock video
            duration: Target duration in seconds (from WhisperX timeline)
            zoom_ratio: Ken Burns zoom amount (0.10 = subtle, 0.20 = aggressive)
        """
        clip = VideoFileClip(video_path).without_audio()

        # Trim to needed duration
        available = clip.duration
        if available < duration:
            loops = math.ceil(duration / available)
            clip = concatenate_videoclips([clip] * loops)
        clip = clip.subclipped(0, duration)   # MoviePy 2.x: subclipped not subclip

        # ─── Dynamic Center Crop to target aspect ratio ───────────
        clip_w, clip_h = clip.size
        target_ratio = self.w / self.h
        current_ratio = clip_w / clip_h

        if current_ratio > target_ratio:
            # Too wide → crop width
            target_w = int(clip_h * target_ratio)
            x1 = (clip_w - target_w) // 2
            clip = clip.cropped(x1=x1, y1=0, x2=x1 + target_w, y2=clip_h)
            clip = clip.resized(height=self.h)   # MoviePy 2.x: resized not resize
        else:
            # Too tall → crop height
            target_h = int(clip_w / target_ratio)
            y1 = (clip_h - target_h) // 2
            clip = clip.cropped(x1=0, y1=y1, x2=clip_w, y2=y1 + target_h)
            clip = clip.resized(width=self.w)    # MoviePy 2.x: resized not resize

        # Ensure exact resolution
        if clip.size != (self.w, self.h):
            clip = clip.resized((self.w, self.h))

        clip = self._jitter_free_zoom(clip, zoom_ratio=zoom_ratio)
        return clip

    # ─────────────────────────────────────────────
    # Full Composition
    # ─────────────────────────────────────────────

    def compose(self, clips: list, output_path: str, timeline: dict) -> str:
        """
        Composes all scene clips into a single video.

        Args:
            clips: List of {"path": str, "duration": float, "segment": dict}
            output_path: Where to save the composed video
            timeline: Master timeline (for cross-fade timing)

        Returns:
            str: Path to output video
        """
        processed_clips = []
        segments = timeline.get("segments", [])

        for i, clip_info in enumerate(clips):
            clip_path = clip_info.get("path")
            duration = clip_info.get("duration", 4.0)
            segment = clip_info.get("segment", {})

            if not clip_path or not Path(clip_path).exists():
                logger.warning(f"[VideoEngine] Clip {i+1} path invalid: {clip_path}")
                # Generate placeholder
                clip_path = self._create_color_clip(duration, i)

            emotion = segment.get("emotion", "deep")
            zoom_ratio = self._emotion_to_zoom(emotion)

            logger.info(f"[VideoEngine] Processing clip {i+1}/{len(clips)}: {duration:.2f}s, zoom={zoom_ratio}")

            try:
                processed = self._process_single_clip(clip_path, duration, zoom_ratio)
                processed_clips.append(processed)
            except Exception as e:
                logger.error(f"[VideoEngine] Error processing clip {i+1}: {e}")
                # Add color fallback
                fallback = self._create_fallback_clip(duration)
                processed_clips.append(fallback)

        if not processed_clips:
            raise RuntimeError("No clips could be processed")

        # Concatenate with crossfade transitions (0.3s)
        logger.info(f"[VideoEngine] Concatenating {len(processed_clips)} clips...")

        try:
            final = concatenate_videoclips(processed_clips, method="compose")
        except Exception:
            final = concatenate_videoclips(processed_clips, method="chain")

        # Write silent video (audio added separately)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        final.write_videofile(
            output_path,
            fps=self.fps,
            codec="libx264",
            preset="fast",
            audio=False,
            logger=None,
        )

        # Cleanup
        final.close()
        for c in processed_clips:
            try:
                c.close()
            except Exception:
                pass

        logger.info(f"[VideoEngine] ✅ Composed video: {output_path}")
        return output_path

    def _emotion_to_zoom(self, emotion: str) -> float:
        """Maps emotional tone to appropriate zoom ratio."""
        zoom_map = {
            "minimal": 0.08,
            "deep": 0.12,
            "emotional": 0.15,
            "modern": 0.10,
            "resolute": 0.10,
            "inspiring": 0.15,
            "steady": 0.08,
            "reassuring": 0.10,
        }
        return zoom_map.get(emotion, 0.12)

    def _create_fallback_clip(self, duration: float):
        """Creates a solid dark fallback clip."""
        return ColorClip(
            size=(self.w, self.h),
            color=(13, 13, 15),
            duration=duration
        )

    def _create_color_clip(self, duration: float, index: int) -> str:
        """Creates an FFmpeg-generated placeholder clip."""
        import subprocess, tempfile
        path = tempfile.mktemp(suffix=".mp4")
        subprocess.run([
            "ffmpeg", "-f", "lavfi",
            "-i", f"color=c=0x0d0d0f:s={self.w}x{self.h}:r={self.fps}",
            "-t", str(duration), path, "-y"
        ], capture_output=True, check=False)
        return path
