"""
THE INNER CITADEL — Caption Engine
Generates word-level karaoke ASS subtitles using pysubs2.

Format: Advanced SubStation Alpha (.ass)
Effect: Active word = pure white, inactive words in line = dimmed grey
Position: Anchored at 75% screen height for vertical video
Font: Montserrat Bold 72pt
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
    Generates .ass karaoke subtitle files with word-level highlighting.
    
    Visual effect per research spec:
    - 4 words shown at a time on screen
    - Currently spoken word: white (#FFFFFF, fully opaque)
    - Other words in chunk: dimmed grey (#AAAAAA, 50% alpha)
    - Position: center, 75% down screen height
    """

    def __init__(self, resolution: tuple = (1080, 1920)):
        self.w, self.h = resolution
        # Anchor at 75% screen height (research mandate)
        self.safe_y = int(self.h * 0.75)
        self.words_per_line = 4    # Words displayed simultaneously
        logger.info(f"[CaptionEngine] Resolution: {self.w}x{self.h}, Y-anchor: {self.safe_y}")

    def build_ass_subtitles(self, timeline: dict, output_path: str = "exports/captions.ass") -> str:
        """
        Builds a complete .ass subtitle file from the master timeline.

        Args:
            timeline: Master timeline JSON with word_data per segment
            output_path: Output path for the .ass file

        Returns:
            str: Path to saved .ass file
        """
        subs = pysubs2.SSAFile()

        # ─── ASS File Headers ─────────────────────────────────────
        subs.info["PlayResX"] = str(self.w)
        subs.info["PlayResY"] = str(self.h)
        subs.info["ScaledBorderAndShadow"] = "yes"

        # ─── Style Definition ─────────────────────────────────────
        style = pysubs2.SSAStyle()
        style.fontname = "Montserrat"
        style.fontsize = 72
        style.primarycolor = pysubs2.Color(255, 255, 255, 0)    # White, fully opaque
        style.outlinecolor = pysubs2.Color(0, 0, 0, 200)        # Black outline
        style.backcolor = pysubs2.Color(0, 0, 0, 128)           # Semi-transparent bg
        style.bold = True
        style.alignment = 2      # Bottom-center (we override pos in each event)
        style.outline = 3
        style.shadow = 5
        style.marginv = int(self.h * 0.25)   # 25% from bottom = 75% from top

        subs.styles["Default"] = style

        # ─── Generate Events ──────────────────────────────────────
        total_events = 0
        segments = timeline.get("segments", [])

        for segment in segments:
            words = segment.get("word_data", [])
            if not words:
                continue

            # Split words into chunks of N (displayed together)
            for chunk_start in range(0, len(words), self.words_per_line):
                chunk = words[chunk_start: chunk_start + self.words_per_line]

                # For each word in this chunk, create a subtitle event
                # where that word is highlighted (active) and others dimmed
                for active_idx, active_word in enumerate(chunk):
                    line_text = ""
                    for w_idx, word in enumerate(chunk):
                        word_text = word["word"].strip()
                        if w_idx == active_idx:
                            # Active word: pure white, fully opaque
                            line_text += f"{{\\c&HFFFFFF&}}{{\\alpha&H00&}}{word_text} "
                        else:
                            # Inactive word: grey, 50% transparent
                            line_text += f"{{\\c&HAAAAAA&}}{{\\alpha&H80&}}{word_text} "

                    line_text = line_text.strip()

                    # Position override: centered horizontally at safe_y
                    pos_tag = f"{{\\pos({self.w // 2},{self.safe_y})}}"
                    full_text = pos_tag + line_text

                    event = pysubs2.SSAEvent(
                        start=pysubs2.make_time(s=active_word["start"]),
                        end=pysubs2.make_time(s=active_word["end"]),
                        text=full_text,
                    )
                    subs.append(event)
                    total_events += 1

        # Ensure output directory
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        subs.save(output_path, encoding="utf-8")

        logger.info(f"[CaptionEngine] ✅ {total_events} subtitle events → {output_path}")
        return output_path
