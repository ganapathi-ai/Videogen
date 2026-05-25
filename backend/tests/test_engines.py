"""
THE INNER CITADEL — Backend Tests
Quick smoke tests for each engine module.
Run: pytest tests/ -v
"""

import pytest
import json


# ─────────────────────────────────────────────
# Script Engine Tests
# ─────────────────────────────────────────────

class TestTimelineEngine:
    """Tests for the Master Timeline Engine (no external deps)."""

    def _make_script(self):
        return {
            "title": "Test: Stoic Resilience",
            "topic": "Resilience",
            "duration_target": 35,
            "hook": "What doesn't kill you makes you stronger.",
            "beats": [
                {"id": 1, "text": "Every obstacle is an opportunity.", "emotion": "inspiring", "intent": "hook", "visual_keywords": ["sunrise", "mountain"]},
                {"id": 2, "text": "Your mind is the only citadel.", "emotion": "deep", "intent": "insight", "visual_keywords": ["meditation", "fortress"]},
                {"id": 3, "text": "Discipline conquers every fear.", "emotion": "resolute", "intent": "action", "visual_keywords": ["warrior", "discipline"]},
            ]
        }

    def _make_word_timeline(self):
        return [
            {"word": "Every", "start": 0.10, "end": 0.45},
            {"word": "obstacle", "start": 0.47, "end": 0.90},
            {"word": "is", "start": 0.92, "end": 1.05},
            {"word": "an", "start": 1.07, "end": 1.20},
            {"word": "opportunity", "start": 1.22, "end": 1.90},
            {"word": "Your", "start": 2.10, "end": 2.40},
            {"word": "mind", "start": 2.42, "end": 2.75},
            {"word": "is", "start": 2.77, "end": 2.90},
            {"word": "the", "start": 2.92, "end": 3.05},
            {"word": "only", "start": 3.07, "end": 3.40},
            {"word": "citadel", "start": 3.42, "end": 4.10},
            {"word": "Discipline", "start": 4.30, "end": 4.90},
            {"word": "conquers", "start": 4.92, "end": 5.50},
            {"word": "every", "start": 5.52, "end": 5.90},
            {"word": "fear", "start": 5.92, "end": 6.40},
        ]

    def test_timeline_builds(self):
        from timeline.timeline_engine import TimelineEngine
        engine = TimelineEngine()
        timeline = engine.build(self._make_script(), self._make_word_timeline())

        assert "segments" in timeline
        assert len(timeline["segments"]) == 3
        assert timeline["duration"] > 0

    def test_audio_is_source_of_truth(self):
        """Verify that audio_start/end come from WhisperX, not estimated."""
        from timeline.timeline_engine import TimelineEngine
        engine = TimelineEngine()
        timeline = engine.build(self._make_script(), self._make_word_timeline())

        seg = timeline["segments"][0]
        # First segment starts at first word timestamp (0.10)
        assert abs(seg["audio_start"] - 0.10) < 0.01

    def test_visual_start_is_seamless(self):
        """Verify visual_start of segment N = visual_end of segment N-1."""
        from timeline.timeline_engine import TimelineEngine
        engine = TimelineEngine()
        timeline = engine.build(self._make_script(), self._make_word_timeline())

        segs = timeline["segments"]
        if len(segs) >= 2:
            assert abs(segs[1]["visual_start"] - segs[0]["visual_end"]) < 0.01

    def test_timeline_json_serializable(self):
        """Timeline must be serializable to JSON."""
        from timeline.timeline_engine import TimelineEngine
        engine = TimelineEngine()
        timeline = engine.build(self._make_script(), self._make_word_timeline())
        json_str = json.dumps(timeline)
        assert len(json_str) > 100


# ─────────────────────────────────────────────
# Caption Engine Tests
# ─────────────────────────────────────────────

class TestCaptionEngine:
    """Tests for the ASS caption engine."""

    def _make_timeline(self):
        return {
            "title": "Test",
            "duration": 6.5,
            "segments": [
                {
                    "id": 1,
                    "text": "Every obstacle is an opportunity",
                    "audio_start": 0.10, "audio_end": 1.90,
                    "word_data": [
                        {"word": "Every", "start": 0.10, "end": 0.45},
                        {"word": "obstacle", "start": 0.47, "end": 0.90},
                        {"word": "is", "start": 0.92, "end": 1.05},
                        {"word": "an", "start": 1.07, "end": 1.90},
                    ]
                }
            ]
        }

    def test_captions_file_created(self, tmp_path):
        from captions.caption_engine import CaptionEngine
        engine = CaptionEngine(resolution=(1080, 1920))
        output = str(tmp_path / "test.ass")
        engine.build_ass_subtitles(self._make_timeline(), output)
        assert (tmp_path / "test.ass").exists()

    def test_captions_has_events(self, tmp_path):
        import pysubs2
        from captions.caption_engine import CaptionEngine
        engine = CaptionEngine(resolution=(1080, 1920))
        output = str(tmp_path / "test.ass")
        engine.build_ass_subtitles(self._make_timeline(), output)
        subs = pysubs2.load(output)
        assert len(subs) > 0
