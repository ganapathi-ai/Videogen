"""
THE INNER CITADEL — Master Timeline Engine
Assembles the single JSON source of truth that drives ALL downstream components.

Rules:
- audio_start/end: from WhisperX word timestamps (AUTHORITATIVE)
- visual_start/end: seamless (visual_start = prev segment's visual_end)
- caption_start/end: = audio_start/end (synced to speech)
- word_data: per-word timestamps for karaoke subtitles
"""

from loguru import logger


class TimelineEngine:
    """
    Assembles the master timeline JSON from script beats and word timestamps.
    This is the single document that every downstream engine reads.
    """

    def build(self, script_data: dict, word_timeline: list) -> dict:
        """
        Builds master timeline by zipping script beats with aligned word timestamps.

        Args:
            script_data: Output from ScriptEngine (beats, title, etc.)
            word_timeline: Output from AlignmentEngine (word-level timestamps)

        Returns:
            dict: Full master timeline JSON
        """
        beats = script_data.get("beats", [])
        if not beats:
            raise ValueError("No beats in script_data")
        if not word_timeline:
            raise ValueError("Empty word_timeline from alignment")

        # Build a flat word list from beats for matching
        beat_word_groups = []
        for beat in beats:
            words = beat["text"].split()
            beat_word_groups.append(words)

        # Assign aligned words to beats greedily
        segments = []
        word_cursor = 0
        visual_cursor = 0.0

        for i, beat in enumerate(beats):
            beat_words = beat["text"].split()
            n_words = len(beat_words)

            # Slice the next n_words from aligned word_timeline
            segment_words = word_timeline[word_cursor: word_cursor + n_words]
            word_cursor += n_words

            if not segment_words:
                logger.warning(f"[TimelineEngine] Beat {i+1} has no aligned words — skipping")
                continue

            # Timing from WhisperX (authoritative)
            audio_start = segment_words[0]["start"]
            audio_end = segment_words[-1]["end"]

            # Visual timing: seamless, starts where previous ended
            visual_start = visual_cursor
            visual_end = audio_end
            visual_cursor = audio_end

            segment = {
                "id": beat["id"],
                "text": beat["text"],
                "emotion": beat.get("emotion", "deep"),
                "intent": beat.get("intent", "insight"),
                "visual_keywords": beat.get("visual_keywords", [beat["text"]]),

                # Authoritative timing from WhisperX
                "audio_start": round(audio_start, 4),
                "audio_end": round(audio_end, 4),

                # Seamless visual timing
                "visual_start": round(visual_start, 4),
                "visual_end": round(visual_end, 4),

                # Caption timing matches audio
                "caption_start": round(audio_start, 4),
                "caption_end": round(audio_end, 4),

                # Per-word data for karaoke subtitles
                "word_data": [
                    {
                        "word": w["word"],
                        "start": round(w["start"], 4),
                        "end": round(w["end"], 4),
                    }
                    for w in segment_words
                ],
            }
            segments.append(segment)

        total_duration = segments[-1]["audio_end"] if segments else 0

        timeline = {
            "title": script_data.get("title", script_data.get("topic", "Untitled")),
            "topic": script_data.get("topic", ""),
            "duration": round(total_duration, 4),
            "segments": segments,
        }

        logger.info(
            f"[TimelineEngine] ✅ Master timeline: "
            f"{len(segments)} segments, {total_duration:.2f}s total"
        )
        return timeline
