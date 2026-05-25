"""
THE INNER CITADEL — Content History Engine

Prevents duplicate content across ALL generated videos.

Strategy:
  1. Every generated video's beats are saved to history.jsonl
  2. Before generation: topic similarity check (Jaccard + SequenceMatcher)
  3. Before saving: exact + near-duplicate beat filtering
  4. Title deduplication

Storage: backend/assets/history.jsonl
Format:  One JSON object per line (append-only, never modified)

Built-in Python only — no extra dependencies.
"""

import json
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from difflib import SequenceMatcher
from loguru import logger


HISTORY_FILE = Path(__file__).parent.parent / "assets" / "history.jsonl"
TOPIC_SIMILARITY_THRESHOLD = 0.72   # Reject if topic matches past at 72%+
BEAT_SIMILARITY_THRESHOLD  = 0.80   # Reject beat if matches past beat at 80%+


class HistoryEngine:
    """
    Tracks all generated content. Ensures zero repetition across videos.

    Call order in pipeline:
      1. check_topic(topic)   → raises if too similar to past topic
      2. filter_beats(beats)  → removes beats seen before
      3. save(script)         → persists approved script to history
    """

    def __init__(self):
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._cache = None      # Lazy-loaded
        logger.info(f"[History] Store: {HISTORY_FILE}")

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────

    def check_topic(self, topic: str) -> None:
        """
        Raises ValueError if this topic is too similar to any past topic.
        Call BEFORE LLM generation to save tokens.
        """
        history = self._load()
        if not history:
            return

        past_topics = [e["topic"] for e in history]
        score, best = self._best_topic_match(topic, past_topics)

        if score >= TOPIC_SIMILARITY_THRESHOLD:
            raise ValueError(
                f"[History] Topic too similar to past content!\n"
                f"  New:  '{topic}'\n"
                f"  Past: '{best}'\n"
                f"  Similarity: {score:.0%} (threshold: {TOPIC_SIMILARITY_THRESHOLD:.0%})\n"
                f"  Try a more distinct angle on this topic."
            )
        logger.info(f"[History] Topic OK — closest past match: '{best}' ({score:.0%})")

    def filter_beats(self, beats: list) -> list:
        """
        Removes beats that are too similar to any beat in past videos.
        Returns filtered list (may be smaller).
        """
        history = self._load()
        if not history:
            return beats

        # Build flat set of all past beat texts
        past_beats = []
        for entry in history:
            past_beats.extend(entry.get("beats", []))

        filtered = []
        removed  = 0
        for beat in beats:
            text = beat.get("text", "") if isinstance(beat, dict) else beat
            if self._is_duplicate_beat(text, past_beats):
                logger.warning(f"[History] Duplicate beat removed: '{text[:50]}'")
                removed += 1
            else:
                filtered.append(beat)
                past_beats.append(text)  # Prevent duplicates within this batch too

        if removed:
            logger.info(f"[History] Filtered {removed} duplicate beats. Remaining: {len(filtered)}")
        return filtered

    def save(self, script: dict, length: str = "short") -> None:
        """
        Saves the generated script to history.
        Call AFTER successful video generation.
        """
        beats_text = [b["text"] for b in script.get("beats", [])]
        entry = {
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "topic":       script.get("topic", ""),
            "title":       script.get("title", ""),
            "length":      length,
            "beat_count":  len(beats_text),
            "beats":       beats_text,
            "beat_hashes": [self._hash(t) for t in beats_text],
        }

        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Invalidate cache
        self._cache = None

        logger.info(
            f"[History] Saved: '{entry['title']}' "
            f"({len(beats_text)} beats) → {HISTORY_FILE.name}"
        )

    def get_all_topics(self) -> list:
        """Returns list of all past topics (for UI display)."""
        return [e["topic"] for e in self._load()]

    def get_stats(self) -> dict:
        """Returns history stats."""
        history = self._load()
        all_beats = sum(len(e.get("beats", [])) for e in history)
        return {
            "total_videos":    len(history),
            "total_beats":     all_beats,
            "unique_topics":   len(set(e["topic"] for e in history)),
            "history_file":    str(HISTORY_FILE),
        }

    # ─────────────────────────────────────────────
    # Internal
    # ─────────────────────────────────────────────

    def _load(self) -> list:
        """Loads history from file. Cached per instance."""
        if self._cache is not None:
            return self._cache

        if not HISTORY_FILE.exists():
            self._cache = []
            return self._cache

        entries = []
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        self._cache = entries
        logger.info(f"[History] Loaded {len(entries)} past videos from history")
        return entries

    def _best_topic_match(self, topic: str, past_topics: list) -> tuple:
        """Returns (best_score, best_match_topic) across all past topics."""
        topic_norm = self._normalize(topic)
        best_score = 0.0
        best_match = ""

        for past in past_topics:
            past_norm = self._normalize(past)

            # Method 1: SequenceMatcher (handles substrings, rewording)
            sm_score = SequenceMatcher(None, topic_norm, past_norm).ratio()

            # Method 2: Jaccard word overlap
            jac_score = self._jaccard(topic_norm, past_norm)

            score = max(sm_score, jac_score)
            if score > best_score:
                best_score = score
                best_match = past

        return best_score, best_match

    def _is_duplicate_beat(self, text: str, past_beats: list) -> bool:
        """Returns True if beat is too similar to any past beat."""
        text_norm = self._normalize(text)
        for past in past_beats:
            past_norm = self._normalize(past)
            score = SequenceMatcher(None, text_norm, past_norm).ratio()
            if score >= BEAT_SIMILARITY_THRESHOLD:
                return True
        return False

    def _normalize(self, text: str) -> str:
        """Lowercase, remove punctuation, collapse spaces."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _jaccard(self, a: str, b: str) -> float:
        """Jaccard similarity on word sets."""
        wa, wb = set(a.split()), set(b.split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)

    def _hash(self, text: str) -> str:
        """MD5 hash for fast exact-match lookup."""
        return hashlib.md5(text.lower().strip().encode()).hexdigest()[:8]
