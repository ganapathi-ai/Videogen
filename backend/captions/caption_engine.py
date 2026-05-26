"""
VOXLORE STUDIO — Caption Engine
Generates word-level karaoke ASS subtitles using pysubs2.

Format: Advanced SubStation Alpha (.ass)

SYNC ALGORITHM (research-based):
  1. Timestamps come from edge-tts WordBoundary events (100ns precision)
  2. All timestamps are frame-snapped to nearest video frame boundary
  3. Each word highlight is GAPLESS — extends to the next word's start
     so there is never a flash of empty screen between words
  4. Chunk transitions (every 4 words) are also gapless
  5. Minimum event duration = 2 frames (prevents invisible flashes)

Visual style (top YouTube channel research):
  - 4 words per chunk displayed simultaneously
  - Active word: pure white, fully opaque
  - Other words: dimmed grey, semi-transparent
  - Position: centered at 75% screen height
  - Font: Arial Bold 72pt with thick black outline
"""

import os
from pathlib import Path
from loguru import logger

try:
    import pysubs2
except ImportError:
    raise ImportError("Run: pip install pysubs2")


class CaptionEngine:
    """
    Generates frame-accurate, gapless .ass karaoke subtitle files.

    Key properties:
    - Frame-snapped: every timestamp aligns to a video frame boundary
    - Gapless: word highlight extends to next word's start (no blank frames)
    - Minimum duration: 2 frames (66ms) prevents invisible flashes
    - 4-word chunks: shows context while highlighting active word
    """

    def __init__(self, resolution: tuple = (1080, 1920), fps: int = 30):
        self.w, self.h   = resolution
        self.fps         = fps
        self.frame_s     = 1.0 / fps          # seconds per frame (0.0333s at 30fps)
        self.frame_ms    = 1000.0 / fps       # ms per frame (33.33ms at 30fps)
        self.safe_y      = int(self.h * 0.75) # Anchor at 75% screen height
        self.words_per_line = 4               # Words displayed simultaneously
        logger.info(
            f"[CaptionEngine] {self.w}x{self.h} | fps={fps} | "
            f"frame={self.frame_ms:.2f}ms | y={self.safe_y}"
        )

    def _snap(self, seconds: float) -> float:
        """Snap timestamp to nearest frame boundary.

        At 30fps, valid boundaries are 0.000, 0.033, 0.067, 0.100 ...
        Snapping means the caption appears on the EXACT frame where
        the word is spoken — zero perceptible delay.
        """
        return round(seconds * self.fps) / self.fps

    def build_ass_subtitles(
        self,
        timeline: dict,
        output_path: str = "exports/captions.ass"
    ) -> str:
        """
        Builds a complete .ass subtitle file from the master timeline.

        Gapless algorithm:
          For each 4-word chunk:
            word[i].display_end = word[i+1].start   (extend to fill gap)
          Last word in chunk:
            display_end = first_word_of_next_chunk.start   (gapless chunk transition)
          Very last word:
            display_end = word[last].end + 2 frames   (natural completion)

        Frame-snap algorithm:
          snap(t) = round(t * fps) / fps
          Applied to both start and display_end times.

        Args:
            timeline: Master timeline JSON with word_data per segment
            output_path: Output path for the .ass file

        Returns:
            str: Path to saved .ass file
        """
        subs = pysubs2.SSAFile()

        # ─── ASS File Headers ─────────────────────────────────────────────
        subs.info["PlayResX"] = str(self.w)
        subs.info["PlayResY"] = str(self.h)
        subs.info["ScaledBorderAndShadow"] = "yes"

        # ─── Style Definition ─────────────────────────────────────────────
        style = pysubs2.SSAStyle()
        style.fontname      = "Arial"                          # Guaranteed on Windows
        style.fontsize      = 72                               # Large for mobile screens
        style.primarycolor  = pysubs2.Color(255, 255, 255, 0) # White, fully opaque
        style.outlinecolor  = pysubs2.Color(0,   0,   0,   0) # Black outline, fully opaque
        style.backcolor     = pysubs2.Color(0,   0,   0, 180) # Semi-transparent black backing
        style.bold          = True
        style.italic        = False
        style.alignment     = 2                                # Bottom-center (overridden by \pos)
        style.outline       = 4                                # Thick outline — readable on any bg
        style.shadow        = 2                                # Subtle depth shadow
        style.marginv       = int(self.h * 0.25)              # 25% from bottom = 75% from top
        subs.styles["Default"] = style

        # ─── Collect ALL words flat across all segments ────────────────────
        # We need the global flat list to compute gapless cross-chunk transitions
        all_words = []
        for segment in timeline.get("segments", []):
            for w in segment.get("word_data", []):
                if w.get("word", "").strip():
                    all_words.append(w)

        if not all_words:
            logger.warning("[CaptionEngine] No word_data found in timeline")
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            subs.save(output_path, encoding="utf-8")
            return output_path

        # ─── Compute gapless display_end for every word ───────────────────
        # display_end = when THIS word's highlight ends on screen
        # = next word's start time (gapless) OR natural end + tail
        MIN_DURATION_S = 2 * self.frame_s   # Minimum 2 frames (66ms at 30fps)

        display_ends = []
        for i, w in enumerate(all_words):
            if i + 1 < len(all_words):
                # Extend highlight to next word's start (GAPLESS)
                next_start = all_words[i + 1]["start"]
                # Take the later of: natural end OR next word start
                d_end = max(w["end"], next_start)
            else:
                # Last word: hold for 2 extra frames after natural end
                d_end = w["end"] + (2 * self.frame_s)

            # Ensure minimum display duration
            nat_start = w["start"]
            if d_end - nat_start < MIN_DURATION_S:
                d_end = nat_start + MIN_DURATION_S

            display_ends.append(d_end)

        # ─── Generate ASS Events (4-word chunks) ──────────────────────────
        total_events = 0
        N = len(all_words)
        WPL = self.words_per_line

        pos_tag = f"{{\\pos({self.w // 2},{self.safe_y})}}"

        for chunk_start in range(0, N, WPL):
            chunk = all_words[chunk_start: chunk_start + WPL]
            chunk_d_ends = display_ends[chunk_start: chunk_start + WPL]

            for active_idx, active_word in enumerate(chunk):
                # Build the display line: active=white, others=grey
                line_text = ""
                for w_idx, word in enumerate(chunk):
                    word_text = word["word"].strip()
                    if not word_text:
                        continue
                    if w_idx == active_idx:
                        # Active word: pure white, fully opaque
                        line_text += f"{{\\c&HFFFFFF&}}{{\\alpha&H00&}}{word_text} "
                    else:
                        # Inactive words in chunk: dimmed grey, 50% transparent
                        line_text += f"{{\\c&HAAAAAA&}}{{\\alpha&H80&}}{word_text} "

                line_text  = line_text.strip()
                full_text  = pos_tag + line_text

                # Frame-snap the START time
                snap_start = self._snap(active_word["start"])

                # Frame-snap the DISPLAY END (gapless)
                snap_end   = self._snap(chunk_d_ends[active_idx])

                # Safety: ensure minimum 2-frame duration
                if snap_end - snap_start < MIN_DURATION_S:
                    snap_end = snap_start + MIN_DURATION_S

                # Safety: ensure end > start
                if snap_end <= snap_start:
                    snap_end = snap_start + self.frame_s

                event = pysubs2.SSAEvent(
                    start=pysubs2.make_time(s=snap_start),
                    end=pysubs2.make_time(s=snap_end),
                    text=full_text,
                )
                subs.append(event)
                total_events += 1

        # ─── Save ──────────────────────────────────────────────────────────
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        subs.save(output_path, encoding="utf-8")

        logger.info(
            f"[CaptionEngine] {total_events} events | "
            f"{N} words | gapless | frame-snapped @ {self.fps}fps -> {output_path}"
        )
        return output_path
