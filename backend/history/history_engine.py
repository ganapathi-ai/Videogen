"""
NeuralBaba Empire — Content History Engine

CRITICAL: Each channel has its OWN separate history file.
  Channel 'stoic' → assets/history_stoic.jsonl
  Channel 'tech'  → assets/history_tech.jsonl

This prevents ANY mixing of content between channels:
  - Stoic topic checks only compare against past stoic topics
  - Tech topic checks only compare against past tech topics
  - Stoic beats never contaminate tech beat deduplication
  - Tech phrases never block stoic generation

Prevents duplicate content within EACH channel:
  1. Topic similarity check  (Jaccard + SequenceMatcher) — before LLM call
  2. Beat deduplication      (SequenceMatcher)           — after LLM call
  3. Append-only JSONL save  — after successful render

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


# ── Per-channel history files ─────────────────────────────────────
ASSETS_DIR = Path(__file__).parent.parent / "assets"

HISTORY_FILES = {
    "stoic": ASSETS_DIR / "history_stoic.jsonl",
    "tech":  ASSETS_DIR / "history_tech.jsonl",
}
# Fallback for unknown channel IDs
DEFAULT_HISTORY_FILE = ASSETS_DIR / "history_stoic.jsonl"

TOPIC_SIMILARITY_THRESHOLD = 0.72   # Reject if topic matches past at 72%+
BEAT_SIMILARITY_THRESHOLD  = 0.80   # Reject beat if matches past beat at 80%+


def _get_history_file(channel_id: str) -> Path:
    """Returns the correct history file for the given channel. Never mixed."""
    return HISTORY_FILES.get(channel_id, DEFAULT_HISTORY_FILE)


class HistoryEngine:
    """
    Channel-isolated history tracking. Ensures zero repetition per channel.
    Stoic history and Tech history are COMPLETELY SEPARATE — no cross-channel
    contamination is possible.

    Call order in pipeline:
      1. check_topic(topic)   → raises if too similar to past topic IN THIS CHANNEL
      2. filter_beats(beats)  → removes beats seen before IN THIS CHANNEL
      3. save(script)         → persists approved script to THIS CHANNEL's history
    """

    def __init__(self, channel_id: str = "stoic"):
        self.channel_id   = channel_id
        self.history_file = _get_history_file(channel_id)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._cache = None      # Lazy-loaded, per-instance
        logger.info(
            f"[History:{channel_id}] Store: {self.history_file.name} "
            f"(isolated from other channels)"
        )

    # ─────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────

    def check_topic(self, topic: str) -> None:
        """
        Raises ValueError if this topic is too similar to any past topic
        IN THIS CHANNEL ONLY. Does not compare against other channels.
        """
        history = self._load()
        if not history:
            return

        past_topics = [e["topic"] for e in history]
        score, best = self._best_topic_match(topic, past_topics)

        if score >= TOPIC_SIMILARITY_THRESHOLD:
            raise ValueError(
                f"[History:{self.channel_id}] Topic too similar to past {self.channel_id} content!\n"
                f"  New:  '{topic}'\n"
                f"  Past: '{best}'\n"
                f"  Similarity: {score:.0%} (threshold: {TOPIC_SIMILARITY_THRESHOLD:.0%})\n"
                f"  Try a more distinct angle on this topic."
            )
        logger.info(
            f"[History:{self.channel_id}] Topic OK — "
            f"closest past match: '{best}' ({score:.0%})"
        )

    def filter_beats(self, beats: list) -> list:
        """
        Removes beats too similar to any beat in past videos OF THIS CHANNEL.
        Returns filtered list (may be smaller).
        Tech beats are only compared to past tech beats.
        Stoic beats are only compared to past stoic beats.
        """
        history = self._load()
        if not history:
            return beats

        # Build flat list of all past beat texts for this channel
        past_beats = []
        for entry in history:
            past_beats.extend(entry.get("beats", []))

        filtered = []
        removed  = 0
        for beat in beats:
            text = beat.get("text", "") if isinstance(beat, dict) else beat
            if self._is_duplicate_beat(text, past_beats):
                logger.warning(
                    f"[History:{self.channel_id}] Duplicate beat removed: '{text[:60]}'"
                )
                removed += 1
            else:
                filtered.append(beat)
                past_beats.append(text)  # Prevent intra-batch duplicates too

        if removed:
            logger.info(
                f"[History:{self.channel_id}] Filtered {removed} duplicate beats. "
                f"Remaining: {len(filtered)}"
            )
        return filtered

    def save(self, script: dict, length: str = "short") -> None:
        """
        Saves the generated script to THIS CHANNEL's history file.
        Call AFTER successful video generation only.
        """
        beats_text = [b["text"] for b in script.get("beats", []) if isinstance(b, dict)]
        entry = {
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "channel":     self.channel_id,      # Always stored — no ambiguity
            "topic":       script.get("topic", ""),
            "title":       script.get("title", ""),
            "length":      length,
            "beat_count":  len(beats_text),
            "beats":       beats_text,
            "beat_hashes": [self._hash(t) for t in beats_text],
        }

        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Invalidate cache so next call reloads from disk
        self._cache = None

        logger.info(
            f"[History:{self.channel_id}] Saved: '{entry['title']}' "
            f"({len(beats_text)} beats) → {self.history_file.name}"
        )

    def get_all_topics(self) -> list:
        """Returns list of all past topics for THIS CHANNEL."""
        return [e["topic"] for e in self._load()]

    def get_stats(self) -> dict:
        """Returns history stats for THIS CHANNEL."""
        history = self._load()
        all_beats = sum(len(e.get("beats", [])) for e in history)
        return {
            "channel":       self.channel_id,
            "total_videos":  len(history),
            "total_beats":   all_beats,
            "unique_topics": len(set(e["topic"] for e in history)),
            "history_file":  str(self.history_file),
        }

    # ─────────────────────────────────────────────────────────────
    # Internal Helpers
    # ─────────────────────────────────────────────────────────────

    def _load(self) -> list:
        """Loads THIS CHANNEL's history from file. Cached per instance."""
        if self._cache is not None:
            return self._cache

        if not self.history_file.exists():
            self._cache = []
            return self._cache

        entries = []
        with open(self.history_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        # Safety: only load entries that belong to this channel
                        # (handles legacy files that may have mixed content)
                        entry_channel = entry.get("channel", self.channel_id)
                        if entry_channel == self.channel_id:
                            entries.append(entry)
                    except json.JSONDecodeError:
                        pass

        self._cache = entries
        logger.info(
            f"[History:{self.channel_id}] Loaded {len(entries)} past videos"
        )
        return entries

    def _best_topic_match(self, topic: str, past_topics: list) -> tuple:
        """Returns (best_score, best_match_topic) across all past topics."""
        topic_norm = self._normalize(topic)
        best_score = 0.0
        best_match = ""

        for past in past_topics:
            past_norm = self._normalize(past)

            # Method 1: SequenceMatcher (handles substrings and rewording)
            sm_score  = SequenceMatcher(None, topic_norm, past_norm).ratio()

            # Method 2: Jaccard word overlap (catches reworded same concept)
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


# ── New: also expose /api/history endpoint data ──────────────────
def get_all_history_stats() -> dict:
    """Returns combined stats for all channels (for admin/UI)."""
    result = {}
    for channel_id in HISTORY_FILES:
        h = HistoryEngine(channel_id)
        result[channel_id] = h.get_stats()
    return result
