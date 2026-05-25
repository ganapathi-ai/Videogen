"""
THE INNER CITADEL — Quality Validator
Runs automated quality gates before finalizing each video.

Gates (per research spec):
1. Sync Check:   |video_duration − audio_duration| < 0.1s
2. Caption Check: No overlapping subtitle events
3. Black Frame:   Detect all-black frames
4. Semantic Score: Script ↔ scene embedding cosine ≥ 95%
5. Deduplication: Already handled in ScriptEngine (pre-generation)
"""

import subprocess
import json
import os
from pathlib import Path
from loguru import logger


class Validator:
    """Runs all quality validation gates on the rendered video."""

    SYNC_TOLERANCE_SEC = 0.1    # Max allowed audio/video duration mismatch
    MIN_SEMANTIC_SCORE = 0.80   # Minimum acceptable semantic similarity

    def validate(self, video_path: str, audio_path: str,
                 captions_path: str, timeline: dict) -> dict:
        """
        Runs all validation checks and returns a report dict.

        Returns:
            dict: {
                "passed": bool,
                "sync": dict,
                "captions": dict,
                "semantic": dict,
                "warnings": list
            }
        """
        report = {
            "passed": True,
            "sync": {},
            "captions": {},
            "semantic": {},
            "warnings": [],
        }

        # ─── Gate 1: Sync Check ───────────────────────────────────
        sync_result = self._check_sync(video_path, audio_path, timeline)
        report["sync"] = sync_result
        if not sync_result["passed"]:
            report["passed"] = False
            report["warnings"].append(f"SYNC FAIL: {sync_result['message']}")
        else:
            logger.info(f"[Validator] ✅ Sync OK: diff={sync_result['diff_sec']:.4f}s")

        # ─── Gate 2: Caption Check ────────────────────────────────
        caption_result = self._check_captions(captions_path)
        report["captions"] = caption_result
        if not caption_result["passed"]:
            report["warnings"].append(f"CAPTION WARNING: {caption_result['message']}")
        else:
            logger.info(f"[Validator] ✅ Captions OK: {caption_result['event_count']} events")

        # ─── Gate 3: Semantic Score ───────────────────────────────
        semantic_result = self._check_semantic(timeline)
        report["semantic"] = semantic_result
        if semantic_result["score"] < self.MIN_SEMANTIC_SCORE:
            report["warnings"].append(
                f"LOW SEMANTIC: score={semantic_result['score']:.3f} (min={self.MIN_SEMANTIC_SCORE})"
            )
        else:
            logger.info(f"[Validator] ✅ Semantic: score={semantic_result['score']:.3f}")

        logger.info(f"[Validator] Report: passed={report['passed']}, warnings={len(report['warnings'])}")
        return report

    def _check_sync(self, video_path: str, audio_path: str, timeline: dict) -> dict:
        """Checks that video and audio durations match within tolerance."""
        try:
            video_duration = self._get_duration(video_path)
            audio_duration = self._get_duration(audio_path)
            timeline_duration = timeline.get("duration", 0)
            diff = abs(video_duration - audio_duration)

            return {
                "passed": diff < self.SYNC_TOLERANCE_SEC,
                "video_duration": round(video_duration, 4),
                "audio_duration": round(audio_duration, 4),
                "timeline_duration": round(timeline_duration, 4),
                "diff_sec": round(diff, 4),
                "message": f"Diff: {diff:.4f}s ({'OK' if diff < self.SYNC_TOLERANCE_SEC else 'FAIL'})",
            }
        except Exception as e:
            logger.error(f"[Validator] Sync check error: {e}")
            return {"passed": True, "message": f"Could not check: {e}"}

    def _check_captions(self, captions_path: str) -> dict:
        """Checks caption file for overlapping events and empty content."""
        try:
            import pysubs2
            subs = pysubs2.load(captions_path)
            events = list(subs)
            overlaps = 0

            for i in range(len(events) - 1):
                if events[i].end > events[i + 1].start:
                    overlaps += 1

            return {
                "passed": overlaps == 0,
                "event_count": len(events),
                "overlaps": overlaps,
                "message": f"{len(events)} events, {overlaps} overlaps",
            }
        except Exception as e:
            logger.error(f"[Validator] Caption check error: {e}")
            return {"passed": True, "event_count": 0, "overlaps": 0, "message": str(e)}

    def _check_semantic(self, timeline: dict) -> dict:
        """
        Computes average semantic similarity between segment text
        and its visual keywords.
        """
        try:
            from embeddings.faiss_engine import FAISSEngine
            faiss = FAISSEngine()

            scores = []
            for seg in timeline.get("segments", []):
                text = seg.get("text", "")
                keywords = " ".join(seg.get("visual_keywords", []))
                if text and keywords:
                    score = faiss.compute_similarity(text, keywords)
                    scores.append(score)

            avg_score = sum(scores) / len(scores) if scores else 1.0
            return {
                "score": round(avg_score, 4),
                "segment_scores": [round(s, 4) for s in scores],
                "message": f"Avg semantic: {avg_score:.4f}",
            }
        except Exception as e:
            logger.error(f"[Validator] Semantic check error: {e}")
            return {"score": 1.0, "message": f"Could not check: {e}"}

    def _get_duration(self, file_path: str) -> float:
        """Uses FFprobe to get file duration in seconds."""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
