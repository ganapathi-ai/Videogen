"""
THE INNER CITADEL — Video Engine (FFmpeg-native, CPU optimized)

PERFORMANCE FIX: The original MoviePy clip.transform() approach processed every
frame in Python PIL — on a 25s@60fps video that's 1500 frames × PIL resize = 
10-50 minutes on CPU.

This version uses FFmpeg's native zoompan filter which runs at real-time speed
(C code, multi-threaded) — same Ken Burns effect, 50-100x faster on Intel CPU.

Pipeline:
  1. Each clip: FFmpeg zoompan + crop to aspect ratio → temp .mp4
  2. Concatenate all clips: FFmpeg concat demuxer → raw_video.mp4

No MoviePy, no Python frame loops, no PIL per-frame resize.
"""

import math
import os
import subprocess
import tempfile
from pathlib import Path
from loguru import logger


# Resolution map
RESOLUTIONS = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1":  (1080, 1080),
}


class VideoEngine:
    """
    CPU-optimized video compositor using FFmpeg native filters.
    Ken Burns zoom: FFmpeg zoompan (real-time on CPU, not per-frame Python).
    """

    def __init__(self, aspect_ratio: str = "9:16", fps: int = 30):
        # Force 30fps for rendering — looks great and 2x faster than 60fps
        # (60fps can be set in final FFmpeg encode if really needed)
        self.w, self.h = RESOLUTIONS.get(aspect_ratio, (1080, 1920))
        self.fps = 30          # Always render at 30fps — CPU-friendly
        self.out_fps = fps     # Target fps requested (stored for reference)
        self.aspect_ratio = aspect_ratio
        logger.info(f"[VideoEngine] {self.w}x{self.h} @ {self.fps}fps (CPU FFmpeg mode)")

    def compose(self, clips: list, output_path: str, timeline: dict) -> str:
        """
        Composes all scene clips into a single silent video using FFmpeg.

        Args:
            clips:       List of {path, duration, segment}
            output_path: Final output .mp4 path
            timeline:    Master timeline (for emotion → zoom mapping)

        Returns:
            str: Path to output video
        """
        if not clips:
            raise RuntimeError("[VideoEngine] No clips provided")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        processed = []
        tmp_dir = Path(tempfile.mkdtemp())

        for i, clip_info in enumerate(clips):
            src = clip_info.get("path", "")
            duration = clip_info.get("duration", 4.0)
            emotion = clip_info.get("segment", {}).get("emotion", "deep")
            zoom_ratio = self._emotion_to_zoom(emotion)

            logger.info(f"[VideoEngine] Clip {i+1}/{len(clips)}: {duration:.2f}s zoom={zoom_ratio}")

            out_clip = str(tmp_dir / f"clip_{i:03d}.mp4")

            if src and Path(src).exists():
                ok = self._process_clip_ffmpeg(src, out_clip, duration, zoom_ratio)
            else:
                ok = False

            if not ok:
                # Fallback: generate solid dark clip
                ok = self._generate_color_clip(out_clip, duration)

            if ok and Path(out_clip).exists():
                processed.append(out_clip)
            else:
                logger.warning(f"[VideoEngine] Clip {i+1} failed — skipping")

        if not processed:
            raise RuntimeError("[VideoEngine] All clips failed to process")

        # Concatenate all processed clips
        logger.info(f"[VideoEngine] Concatenating {len(processed)} clips → {output_path}")
        self._concat_clips(processed, output_path)

        # Cleanup temp files
        for p in processed:
            try:
                os.unlink(p)
            except Exception:
                pass

        logger.info(f"[VideoEngine] Done: {output_path}")
        return output_path

    # ─────────────────────────────────────────────
    # FFmpeg clip processor — zoompan Ken Burns
    # ─────────────────────────────────────────────

    def _process_clip_ffmpeg(self, src: str, out: str, duration: float,
                              zoom_ratio: float) -> bool:
        """
        Processes a single video clip with FFmpeg:
          1. Crop to target aspect ratio (center crop)
          2. Scale to target resolution
          3. Trim to needed duration (loop if too short)
          4. Apply zoompan Ken Burns effect
          5. Encode as H.264 fast preset
        """
        try:
            # Get source dimensions
            probe = subprocess.run([
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_streams", "-select_streams", "v:0", src
            ], capture_output=True, text=True, timeout=10)

            src_w, src_h, src_dur = self._parse_probe(probe.stdout)
            if not src_w:
                return False

            # Loop count if source too short
            loops = max(1, math.ceil(duration / max(src_dur, 0.1)))
            n_frames = int(duration * self.fps)

            # Ken Burns: zoom from 1.0 → (1.0 + zoom_ratio) over clip duration
            # FFmpeg zoompan z expression: starts at 1.0, increments per frame
            zoom_per_frame = zoom_ratio / max(n_frames, 1)
            max_zoom = 1.0 + zoom_ratio

            # Build crop filter to match target aspect ratio
            crop_filter = self._build_crop_filter(src_w, src_h)

            # zoompan filter — native C, runs in real-time on CPU
            zoom_filter = (
                f"zoompan="
                f"z='min(zoom+{zoom_per_frame:.6f},{max_zoom:.4f})':"
                f"x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':"
                f"d={n_frames}:"
                f"s={self.w}x{self.h}:"
                f"fps={self.fps}"
            )

            # Full filter chain
            vf = f"{crop_filter},{zoom_filter}" if crop_filter else zoom_filter

            # Build FFmpeg command
            # -stream_loop loops the source if it's shorter than needed
            cmd = [
                "ffmpeg",
                "-stream_loop", str(loops),
                "-i", src,
                "-t", f"{duration:.3f}",
                "-vf", vf,
                "-an",                      # No audio in raw video
                "-c:v", "libx264",
                "-preset", "ultrafast",     # Fastest encoding (CPU)
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-r", str(self.fps),
                out, "-y",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                logger.warning(f"[VideoEngine] FFmpeg error clip: {result.stderr[-300:]}")
                return False

            return Path(out).exists() and Path(out).stat().st_size > 1000

        except subprocess.TimeoutExpired:
            logger.warning(f"[VideoEngine] Clip {src} timed out")
            return False
        except Exception as e:
            logger.warning(f"[VideoEngine] Clip error: {e}")
            return False

    def _build_crop_filter(self, src_w: int, src_h: int) -> str:
        """Builds FFmpeg crop filter to match target aspect ratio."""
        target_ratio = self.w / self.h
        current_ratio = src_w / src_h

        if abs(current_ratio - target_ratio) < 0.05:
            # Close enough — just scale
            return f"scale={self.w}:{self.h}"

        if current_ratio > target_ratio:
            # Source too wide → crop width
            crop_w = int(src_h * target_ratio)
            crop_x = (src_w - crop_w) // 2
            return f"crop={crop_w}:{src_h}:{crop_x}:0,scale={self.w}:{self.h}"
        else:
            # Source too tall → crop height
            crop_h = int(src_w / target_ratio)
            crop_y = (src_h - crop_h) // 2
            return f"crop={src_w}:{crop_h}:0:{crop_y},scale={self.w}:{self.h}"

    def _concat_clips(self, clip_paths: list, output_path: str):
        """Concatenates clips using FFmpeg concat demuxer (fastest method)."""
        # Write concat list file
        list_file = output_path + ".concat.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for p in clip_paths:
                # Escape backslashes for FFmpeg on Windows
                safe = p.replace("\\", "/")
                f.write(f"file '{safe}'\n")

        try:
            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c", "copy",           # Stream copy — no re-encode needed
                "-an",
                output_path, "-y",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                logger.warning(f"[VideoEngine] Concat copy failed, trying re-encode: {result.stderr[-200:]}")
                # Fallback: re-encode
                cmd2 = [
                    "ffmpeg",
                    "-f", "concat", "-safe", "0",
                    "-i", list_file,
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                    "-pix_fmt", "yuv420p", "-an",
                    output_path, "-y",
                ]
                subprocess.run(cmd2, capture_output=True, timeout=180, check=True)
        finally:
            try:
                os.unlink(list_file)
            except Exception:
                pass

    def _generate_color_clip(self, out: str, duration: float) -> bool:
        """Generates a solid dark background clip as fallback."""
        try:
            cmd = [
                "ffmpeg",
                "-f", "lavfi",
                "-i", f"color=c=0x0d0d0f:s={self.w}x{self.h}:r={self.fps}",
                "-t", f"{duration:.3f}",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-an",
                out, "-y",
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            return result.returncode == 0
        except Exception:
            return False

    def _parse_probe(self, json_str: str):
        """Parses ffprobe JSON output for width, height, duration."""
        import json
        try:
            data = json.loads(json_str)
            stream = data.get("streams", [{}])[0]
            w = int(stream.get("width", 0))
            h = int(stream.get("height", 0))
            dur = float(stream.get("duration", 0))
            if not dur:
                # Try from tags
                dur = float(stream.get("tags", {}).get("DURATION-eng", "5").split(".")[0])
            return w, h, max(dur, 1.0)
        except Exception:
            return 0, 0, 5.0

    def _emotion_to_zoom(self, emotion: str) -> float:
        """Maps emotional tone to Ken Burns zoom ratio."""
        return {
            "minimal":    0.06,
            "deep":       0.08,
            "emotional":  0.10,
            "modern":     0.07,
            "resolute":   0.07,
            "inspiring":  0.10,
            "steady":     0.06,
            "reassuring": 0.07,
        }.get(emotion, 0.08)
