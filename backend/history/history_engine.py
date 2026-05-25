"""
VOXLORE STUDIO — Content History Engine

ARCHITECTURE: Per-channel subfolder isolation.
Each channel gets its own directory under assets/history/:

  assets/
    history/
      stoic/
        history.jsonl    ← ONLY stoic channel videos
      tech/
        history.jsonl    ← ONLY tech channel videos
      [any_new_channel]/
        history.jsonl    ← Auto-created on first use

ZERO CROSS-CHANNEL CONTAMINATION:
  - HistoryEngine(channel_id="stoic") ONLY reads/writes stoic subfolder
  - Adding a new channel requires zero code changes — just define it in channel_config.py
  - _load() filters by channel field as a second safety check
  - Topic dedup checks ONLY against same-channel past topics
  - Beat dedup checks ONLY against same-channel past beats

Storage format: JSONL (append-only, one JSON object per line)
Dependencies: Built-in Python only
"""

import json
import re
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from difflib import SequenceMatcher
from loguru import logger


# ── Base history directory ────────────────────────────────────────
HISTORY_BASE_DIR = Path(__file__).parent.parent / "assets" / "history"

# ── Known channels (for convenience — NOT required; any channel_id works) ─
HISTORY_FILES = {
    "stoic": HISTORY_BASE_DIR / "stoic" / "history.jsonl",
    "tech":  HISTORY_BASE_DIR / "tech"  / "history.jsonl",
}

TOPIC_SIMILARITY_THRESHOLD = 0.72   # Reject if topic matches past at 72%+
BEAT_SIMILARITY_THRESHOLD  = 0.80   # Reject beat if matches past beat at 80%+


def _get_history_file(channel_id: str) -> Path:
    """
    Returns the history file path for any channel_id.
    Creates the subdirectory automatically if it doesn't exist.
    Works for ANY channel — no hardcoding required.
    """
    history_file = HISTORY_BASE_DIR / channel_id / "history.jsonl"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    return history_file


class HistoryEngine:
    """
    Channel-isolated content history tracking.

    Works for ANY number of channels — just pass the channel_id.
    Each channel gets its own subdirectory: assets/history/{channel_id}/history.jsonl

    Call order in pipeline:
      1. check_topic(topic)   → raises if topic too similar to past IN THIS CHANNEL
      2. filter_beats(beats)  → removes beats seen before IN THIS CHANNEL
      3. save(script)         → persists approved script to THIS CHANNEL's subfolder

    Stoic and Tech histories are COMPLETELY SEPARATE — no cross-channel reads.
    If you add 10 more channels, each gets its own isolated subfolder automatically.
    """

    def __init__(self, channel_id: str = "stoic"):
        self.channel_id   = channel_id
        self.history_file = _get_history_file(channel_id)
        self._cache       = None      # Lazy-loaded per instance
        logger.info(
            f"[History:{channel_id}] "
            f"Store: assets/history/{channel_id}/history.jsonl"
        )

    # ─────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────

    def check_topic(self, topic: str) -> None:
        """
        Raises ValueError if this topic is too similar to any past topic
        in THIS CHANNEL's history ONLY. Never reads other channels.
        """
        history = self._load()
        if not history:
            return

        past_topics = [e["topic"] for e in history]
        score, best = self._best_topic_match(topic, past_topics)

        if score >= TOPIC_SIMILARITY_THRESHOLD:
            raise ValueError(
                f"[History:{self.channel_id}] Topic too similar to past content!\n"
                f"  New:       '{topic}'\n"
                f"  Past:      '{best}'\n"
                f"  Score:     {score:.0%} (threshold {TOPIC_SIMILARITY_THRESHOLD:.0%})\n"
                f"  Fix:       Choose a more distinct angle."
            )

        logger.info(
            f"[History:{self.channel_id}] Topic OK — "
            f"closest past: '{best}' ({score:.0%})"
        )

    def filter_beats(self, beats: list) -> list:
        """
        Removes beats too similar to any beat in past videos OF THIS CHANNEL.
        Tech beats compared only to past tech beats.
        Stoic beats compared only to past stoic beats.
        """
        history = self._load()
        if not history:
            return beats

        # Flat list of all past beat texts for this channel only
        past_beats = []
        for entry in history:
            past_beats.extend(entry.get("beats", []))

        filtered = []
        removed  = 0
        for beat in beats:
            text = beat.get("text", "") if isinstance(beat, dict) else beat
            if self._is_duplicate_beat(text, past_beats):
                logger.warning(
                    f"[History:{self.channel_id}] Dup beat removed: '{text[:60]}'"
                )
                removed += 1
            else:
                filtered.append(beat)
                past_beats.append(text)   # Prevent within-batch dups too

        if removed:
            logger.info(
                f"[History:{self.channel_id}] Removed {removed} dup beats. "
                f"Kept: {len(filtered)}"
            )
        return filtered

    def save(self, script: dict, length: str = "short") -> None:
        """
        Saves the generated script to THIS CHANNEL's history subfolder.
        Call AFTER successful video render only.
        """
        beats_text = [
            b["text"] for b in script.get("beats", [])
            if isinstance(b, dict) and b.get("text")
        ]
        entry = {
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "channel":     self.channel_id,   # Stored for safety/audit
            "topic":       script.get("topic", ""),
            "title":       script.get("title", ""),
            "length":      length,
            "beat_count":  len(beats_text),
            "beats":       beats_text,
            "beat_hashes": [self._hash(t) for t in beats_text],
        }

        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        self._cache = None   # Invalidate cache

        logger.info(
            f"[History:{self.channel_id}] Saved: '{entry['title']}' "
            f"({len(beats_text)} beats) → "
            f"assets/history/{self.channel_id}/history.jsonl"
        )

    def get_all_topics(self) -> list:
        """Returns all past topics for THIS CHANNEL only."""
        return [e["topic"] for e in self._load()]

    def get_stats(self) -> dict:
        """Returns stats for THIS CHANNEL's history."""
        history  = self._load()
        all_beats = sum(len(e.get("beats", [])) for e in history)
        return {
            "channel":        self.channel_id,
            "history_path":   f"assets/history/{self.channel_id}/history.jsonl",
            "total_videos":   len(history),
            "total_beats":    all_beats,
            "unique_topics":  len(set(e["topic"] for e in history)),
        }

    # ─────────────────────────────────────────────────────────────
    # Internal — all private to this channel
    # ─────────────────────────────────────────────────────────────

    def _load(self) -> list:
        """Loads THIS CHANNEL's history. Cached per-instance. Never reads other channels."""
        if self._cache is not None:
            return self._cache

        if not self.history_file.exists():
            self._cache = []
            return self._cache

        entries = []
        with open(self.history_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Safety filter: only load entries that belong to this channel
                    # (prevents any accidental cross-write contamination)
                    entry_ch = entry.get("channel", self.channel_id)
                    if entry_ch == self.channel_id:
                        entries.append(entry)
                    else:
                        logger.warning(
                            f"[History:{self.channel_id}] Skipped foreign entry "
                            f"(channel='{entry_ch}') — isolation enforced"
                        )
                except json.JSONDecodeError:
                    pass

        self._cache = entries
        logger.info(
            f"[History:{self.channel_id}] Loaded {len(entries)} videos"
        )
        return entries

    def _best_topic_match(self, topic: str, past_topics: list) -> tuple:
        topic_norm = self._normalize(topic)
        best_score = 0.0
        best_match = ""
        for past in past_topics:
            past_norm = self._normalize(past)
            sm  = SequenceMatcher(None, topic_norm, past_norm).ratio()
            jac = self._jaccard(topic_norm, past_norm)
            score = max(sm, jac)
            if score > best_score:
                best_score = score
                best_match = past
        return best_score, best_match

    def _is_duplicate_beat(self, text: str, past_beats: list) -> bool:
        text_norm = self._normalize(text)
        for past in past_beats:
            if SequenceMatcher(None, text_norm, self._normalize(past)).ratio() >= BEAT_SIMILARITY_THRESHOLD:
                return True
        return False

    def _normalize(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _jaccard(self, a: str, b: str) -> float:
        wa, wb = set(a.split()), set(b.split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)

    def _hash(self, text: str) -> str:
        return hashlib.md5(text.lower().strip().encode()).hexdigest()[:8]


# ── Convenience: get stats for all known channels ────────────────
def get_all_history_stats() -> dict:
    """
    Returns stats for every channel in HISTORY_BASE_DIR.
    Discovers channels by scanning subfolders — works for ANY number of channels.
    """
    result = {}
    if HISTORY_BASE_DIR.exists():
        for ch_dir in sorted(HISTORY_BASE_DIR.iterdir()):
            if ch_dir.is_dir():
                h = HistoryEngine(channel_id=ch_dir.name)
                result[ch_dir.name] = h.get_stats()
    return result
