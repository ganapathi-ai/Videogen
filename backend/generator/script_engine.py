"""
THE INNER CITADEL — Script Engine
LLM Priority Chain: Groq (fastest) → OpenRouter (many free models) → Gemini (fallback)

All three APIs have completely FREE tiers — no credit card conflicts:
  • Groq:        14,400 req/day free  | 500+ tok/sec | console.groq.com/keys
  • OpenRouter:  Unlimited free models| `:free` suffix| openrouter.ai/keys
  • Gemini:      1M tokens/day free   | aistudio.google.com/apikey

VIDEO LENGTHS supported:
  Shorts/Reels:  short (~35s, 7 beats) | medium (~60s, 12 beats)
  Full YouTube:  long_3 (3 min, 36 beats) | long_5 (5 min, 60 beats)
                 long_7 (7 min, 84 beats) | long_11 (11 min, 130 beats)

Long-form structure (Einzelgänger / Philosophies for Life style):
  HOOK → PROBLEM → PHILOSOPHY → STORY → APPLICATION → CLOSE
"""

import os
import json
import re
from typing import List, Optional
from pydantic import BaseModel, Field
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# ─────────────────────────────────────────────────────────────────
# Length Configuration
# Research basis: Einzelgänger, Philosophies for Life, Daily Stoic
# Beat avg: 9 words @ -15% TTS rate ≈ 5s/beat + 0.6s pause = 5.6s/beat
# ─────────────────────────────────────────────────────────────────

LENGTH_CONFIG = {
    # ── Shorts / Reels ─────────────────────────────────
    "short":   {"target_s": 35,  "beats": 7,   "type": "short",  "label": "~35s Short"},
    "medium":  {"target_s": 60,  "beats": 12,  "type": "short",  "label": "~60s Short"},
    # ── Full YouTube ────────────────────────────────────
    "long_3":  {"target_s": 180, "beats": 34,  "type": "long",   "label": ">3 min YouTube"},
    "long_5":  {"target_s": 300, "beats": 56,  "type": "long",   "label": ">5 min YouTube"},
    "long_7":  {"target_s": 420, "beats": 78,  "type": "long",   "label": ">7 min YouTube"},
    "long_11": {"target_s": 660, "beats": 122, "type": "long",   "label": ">11 min YouTube"},
}

# Groq llama has a context window of 8k tokens
# For long videos we chunk the generation into multiple calls
# Each chunk: max 30 beats
MAX_BEATS_PER_CALL = 28

# Long-form chapter structure (Einzelgänger / Philosophies for Life research)
# Each chapter gets a proportion of the total beats
LONG_FORM_CHAPTERS = [
    {"name": "HOOK",        "intent": "hook",    "proportion": 0.08},  # ~8%
    {"name": "PROBLEM",     "intent": "pain",    "proportion": 0.18},  # ~18%
    {"name": "PHILOSOPHY",  "intent": "insight", "proportion": 0.28},  # ~28%
    {"name": "STORY",       "intent": "reframe", "proportion": 0.22},  # ~22%
    {"name": "APPLICATION", "intent": "action",  "proportion": 0.16},  # ~16%
    {"name": "CLOSE",       "intent": "close",   "proportion": 0.08},  # ~8%
]


# ─────────────────────────────────────────────────────────────────
# Pydantic Schema
# ─────────────────────────────────────────────────────────────────

class Beat(BaseModel):
    id: int
    text: str = Field(description="Exactly 6-12 words. One powerful idea. No filler. No commas.")
    emotion: str = Field(description="One of: minimal|deep|emotional|modern|resolute|inspiring|steady|reassuring")
    intent: str = Field(description="Narrative stage: hook|pain|insight|reframe|action|close")
    visual_keywords: List[str] = Field(description="2-3 cinematic Pexels search terms. E.g. ['roman soldier', 'sunset mountain']")

class Script(BaseModel):
    title: str = Field(description="Cinematic philosophical title")
    topic: str
    duration_target: int
    hook: str = Field(description="Opening hook — max 10 words. Creates immediate tension.")
    beats: List[Beat]


# ─────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────

# NOTE: This is the legacy fallback prompt only.
# All active channels now use their own system_prompt from channel_config.py.
# _get_system_prompt(channel_id) fetches the right prompt automatically.
# This fallback only activates if channel_config import fails entirely.
LEGACY_SYSTEM_PROMPT = """You are an elite cinematic narrator writing spoken-word video scripts.

CRITICAL RULES — follow every single one:
1. NEVER use proper nouns or named attributions. The narrator IS the voice.
2. NEVER use commas. Commas make TTS pause unnaturally. Use short separate sentences instead.
3. Each beat must be 6-12 words. One powerful self-contained statement.
4. Write as if you are SPEAKING directly to the viewer. Use "you" and "your". Personal. Urgent.
5. Language must feel like spoken poetry — short punchy words. NOT academic prose.
6. No commas. No colons. No semicolons. No parentheses. No dashes. Only periods and exclamation marks.
7. YOU MUST respond ONLY with valid JSON. No explanation. No markdown. No preamble.
8. The JSON must exactly match the schema provided.
9. Each beat must be COMPLETELY UNIQUE — never repeat the same idea twice.
10. Build emotional arc: start tense → go deeper → resolve powerfully."""

# ── Channel-aware system prompt ───────────────────────────────────
def _get_system_prompt(channel_id: str = "stoic") -> str:
    """Returns the channel-specific system prompt from channel_config. Never mixes channels."""
    try:
        from channels.channel_config import get_channel
        return get_channel(channel_id)["system_prompt"]
    except Exception:
        return LEGACY_SYSTEM_PROMPT  # last-resort fallback


def _short_form_prompt(topic: str, duration_target: int, num_beats: int,
                        used_beats: list = None) -> str:
    used_section = ""
    if used_beats:
        sample = used_beats[:5]
        used_section = f"\n\nAVOID THESE EXACT PHRASINGS (already used in past videos):\n"
        used_section += "\n".join(f'  - "{b}"' for b in sample)

    return f"""Generate a {duration_target}-second spoken-word video script about: "{topic}"

Target exactly {num_beats} beats. This is a SHORT-FORM video (Shorts/Reels).
Arc: Hook (1 beat) → Context (2 beats) → Insight (2 beats) → Action (1 beat) → Close (1 beat)

Each beat = 6-12 words MAXIMUM. One idea. No names. No commas. Only periods.

GOOD beats (short, direct, spoken-word style):
  "Your mind is not your identity."
  "Every thought you resist will consume you."
  "The pain you feel is not permanent."
  "You have always had the power to choose."
  "Begin now. Act. Do not hesitate."

BAD (avoid):
  "You are not your thoughts, [Name]" — NO names
  "Let go, breathe, and find peace" — NO commas
  Repeating the same idea twice — NO repetition
{used_section}
Return ONLY this JSON:
{{
  "title": "string",
  "topic": "{topic}",
  "duration_target": {duration_target},
  "hook": "string (max 10 words. grabs attention instantly. no commas.)",
  "beats": [
    {{
      "id": 1,
      "text": "6-12 word statement. No commas. No names.",
      "emotion": "one of: minimal|deep|emotional|modern|resolute|inspiring|steady|reassuring",
      "intent": "one of: hook|pain|insight|reframe|action|close",
      "visual_keywords": ["search term 1", "search term 2"]
    }}
  ]
}}"""


def _long_form_prompt(topic: str, duration_target: int, num_beats: int,
                       chapter_name: str, chapter_intent: str,
                       chapter_beats: int, start_id: int,
                       used_beats: list = None) -> str:
    duration_min = duration_target // 60

    used_section = ""
    if used_beats:
        sample = used_beats[:8]
        used_section = f"\n\nAVOID THESE PHRASINGS (used in past videos or earlier chapters):\n"
        used_section += "\n".join(f'  - "{b}"' for b in sample)

    return f"""Generate beats for chapter "{chapter_name}" of a >{duration_min}-minute YouTube video about: "{topic}"

This chapter covers: {chapter_intent.upper()} — generate exactly {chapter_beats} beats for this chapter.
Start beat IDs from {start_id}.

Chapter purpose:
  HOOK:        Shock the viewer. Make them feel they MUST watch.
  PROBLEM:     Describe the pain/struggle the viewer lives with. Be specific.
  PHILOSOPHY:  The core insight. Slow down. Go deep. Build real understanding.
  STORY:       An illustrative scenario (no real names). Make it vivid.
  APPLICATION: Practical. "Here is what you do." Concrete daily actions.
  CLOSE:       Unforgettable ending. Leave them changed.

LONG-FORM style (deeper than Shorts):
  - More nuanced. Allow 2-3 beats to develop one idea.
  - Use varied rhythms: short punchy beats AND longer (10-12 word) thoughtful beats.
  - Build momentum. Each beat should flow naturally from the previous.
  - NO commas. NO proper names. Only periods. Direct address to viewer.
  - Every beat must speak universally — no attributions, no citations.
{used_section}
Return ONLY this JSON:
{{
  "title": "string",
  "topic": "{topic}",
  "duration_target": {duration_target},
  "hook": "string (max 10 words)",
  "beats": [
    {{
      "id": {start_id},
      "text": "6-12 word statement. No commas. No names.",
      "emotion": "one of: minimal|deep|emotional|modern|resolute|inspiring|steady|reassuring",
      "intent": "{chapter_intent}",
      "visual_keywords": ["cinematic search term 1", "cinematic search term 2"]
    }}
  ]
}}"""


# ─────────────────────────────────────────────────────────────────
# LLM Clients
# ─────────────────────────────────────────────────────────────────

class GroqClient:
    """Groq API — Fastest inference. 14,400 free requests/day."""

    def __init__(self):
        self.api_key  = os.getenv("GROQ_API_KEY", "")
        self.model    = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.base_url = "https://api.groq.com/openai/v1"

    def available(self) -> bool:
        return bool(self.api_key and self.api_key != "YOUR_GROQ_KEY_HERE")

    def generate(self, system: str, user: str, max_tokens: int = 4096) -> str:
        import httpx
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model":   self.model,
                "messages":[{"role":"system","content":system},{"role":"user","content":user}],
                "temperature":     0.78,
                "max_tokens":      max_tokens,
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


class OpenRouterClient:
    """OpenRouter API — Many free models. Unlimited with :free suffix."""

    def __init__(self):
        self.api_key  = os.getenv("OPENROUTER_API_KEY", "")
        self.model    = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash:free")
        self.base_url = "https://openrouter.ai/api/v1"

    def available(self) -> bool:
        return bool(self.api_key and self.api_key != "YOUR_OPENROUTER_KEY_HERE")

    def generate(self, system: str, user: str, max_tokens: int = 4096) -> str:
        import httpx
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  "https://voxlore.studio",
                "X-Title":       "Voxlore Studio",
            },
            json={
                "model":   self.model,
                "messages":[{"role":"system","content":system},{"role":"user","content":user}],
                "temperature":     0.78,
                "max_tokens":      max_tokens,
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


class GeminiClient:
    """Google Gemini API — free tier, 1500 req/day. Used as fallback."""

    # gemini-1.5-flash is deprecated (404 since early 2026)
    # gemini-2.0-flash is the current free fast model
    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model   = os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL)

    def available(self) -> bool:
        return bool(self.api_key and self.api_key != "YOUR_GEMINI_KEY_HERE")

    def generate(self, system: str, user: str, max_tokens: int = 4096) -> str:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.78,
                response_mime_type="application/json",
            ),
        )
        return response.text


# ─────────────────────────────────────────────────────────────────
# Script Engine — Priority Chain + Long-Form Support
# ─────────────────────────────────────────────────────────────────

class ScriptEngine:
    """
    VOXLORE STUDIO — Universal video script generator.
    Supports ALL channels: stoic, tech, and any future channels.
    Channel content is driven entirely by channel_config.py system prompts.
    Supports short-form (Shorts/Reels) and long-form (Full YouTube).
    History-aware: passes recent beats to LLM to avoid repetition.
    """

    def __init__(self):
        self.groq       = GroqClient()
        self.openrouter = OpenRouterClient()
        self.gemini     = GeminiClient()

        available = []
        if self.groq.available():       available.append(f"Groq ({self.groq.model})")
        if self.openrouter.available(): available.append(f"OpenRouter ({self.openrouter.model})")
        if self.gemini.available():     available.append(f"Gemini ({self.gemini.model})")

        if not available:
            raise ValueError(
                "No LLM API keys found!\n"
                "Set at least ONE of: GROQ_API_KEY, OPENROUTER_API_KEY, GEMINI_API_KEY"
            )
        logger.info(f"[ScriptEngine] Available LLMs: {', '.join(available)}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=60))
    def generate_script(self, topic: str, length: str = "short",
                         used_beats: list = None, channel_id: str = "stoic") -> dict:
        """
        Generates a video script for the specified channel.

        Args:
            topic:      e.g. "Overcoming Fear" or "How AI Agents Work"
            length:     "short" | "medium" | "long_3" | "long_5" | "long_7" | "long_11"
            used_beats: Beat texts from history (to avoid repetition)
            channel_id: "stoic" | "tech"

        Returns:
            dict: Validated script with title, beats, visual_keywords
        """
        cfg = LENGTH_CONFIG.get(length, LENGTH_CONFIG["short"])
        video_type   = cfg["type"]
        duration_s   = cfg["target_s"]
        total_beats  = cfg["beats"]

        # Load channel system prompt
        system_prompt = _get_system_prompt(channel_id)

        logger.info(
            f"[ScriptEngine] channel={channel_id} | '{topic}' | {cfg['label']} "
            f"| {total_beats} beats | {duration_s}s target"
        )

        if video_type == "short":
            return self._generate_short(topic, duration_s, total_beats, used_beats,
                                        system_prompt=system_prompt)
        else:
            return self._generate_long(topic, duration_s, total_beats, length, used_beats,
                                       system_prompt=system_prompt)

    # ─────────────────────────────────────────────
    # Short-Form (Shorts / Reels)
    # ─────────────────────────────────────────────

    def _generate_short(self, topic: str, duration_s: int,
                          num_beats: int, used_beats: list,
                          system_prompt: str = None) -> dict:
        """Single LLM call for short-form content. System prompt is channel-specific."""
        prompt = _short_form_prompt(topic, duration_s, num_beats, used_beats)
        sys_p  = system_prompt or LEGACY_SYSTEM_PROMPT
        raw    = self._call_with_fallback(sys_p, prompt, max_tokens=2048)
        return self._parse_and_validate(raw, topic, duration_s)

    # ─────────────────────────────────────────────
    # Long-Form (Full YouTube)
    # ─────────────────────────────────────────────

    def _generate_long(self, topic: str, duration_s: int,
                         total_beats: int, length: str,
                         used_beats: list, system_prompt: str = None) -> dict:
        """
        Multi-call generation for long-form videos.

        Strategy: Generate each chapter in a separate LLM call.
        This keeps each call within token limits and produces
        better chapter-specific content.
        """
        all_beats   = []
        beat_id     = 1
        title       = None
        hook        = None
        this_chapter_beats = []  # Running list of beats in this video

        for chapter in LONG_FORM_CHAPTERS:
            # Calculate beats for this chapter
            chapter_beats = max(3, round(total_beats * chapter["proportion"]))
            # Adjust last chapter to hit exact total
            if chapter == LONG_FORM_CHAPTERS[-1]:
                chapter_beats = max(3, total_beats - len(all_beats))

            # Combine history beats + beats already in this video
            avoid_beats = list(used_beats or []) + [b["text"] for b in this_chapter_beats]

            logger.info(
                f"[ScriptEngine] Chapter '{chapter['name']}': "
                f"{chapter_beats} beats (IDs {beat_id}-{beat_id+chapter_beats-1})"
            )

            prompt = _long_form_prompt(
                topic=topic,
                duration_target=duration_s,
                num_beats=total_beats,
                chapter_name=chapter["name"],
                chapter_intent=chapter["intent"],
                chapter_beats=chapter_beats,
                start_id=beat_id,
                used_beats=avoid_beats[:10],  # Cap to avoid giant prompts
            )

            raw = self._call_with_fallback(
                system_prompt or LEGACY_SYSTEM_PROMPT, prompt,
                max_tokens=min(4096, chapter_beats * 120),
            )
            chapter_data = self._parse_and_validate(raw, topic, duration_s)

            # Take title + hook from first chapter only
            if title is None:
                title = chapter_data.get("title", f"The {topic}")
                hook  = chapter_data.get("hook", "")

            chapter_beat_list = chapter_data.get("beats", [])

            # Re-assign IDs sequentially and fix intent to match chapter
            for i, b in enumerate(chapter_beat_list):
                b["id"]     = beat_id
                b["intent"] = chapter["intent"]
                beat_id += 1

            all_beats.extend(chapter_beat_list)
            this_chapter_beats.extend(chapter_beat_list)
            logger.info(f"[ScriptEngine] Chapter '{chapter['name']}' done: {len(chapter_beat_list)} beats")

            # Rate-limit guard: sleep between chapter calls to avoid 429s
            # Long videos have 6 chapters — without sleep, rapid-fire calls hit Groq/OpenRouter limits
            if chapter != LONG_FORM_CHAPTERS[-1]:  # No sleep after last chapter
                import time
                time.sleep(3)

        result = {
            "title":           title,
            "topic":           topic,
            "duration_target": duration_s,
            "hook":            hook,
            "beats":           all_beats,
        }
        logger.info(
            f"[ScriptEngine] Long-form complete: '{title}' "
            f"— {len(all_beats)} beats total"
        )
        return result

    # ─────────────────────────────────────────────
    # LLM Fallback Chain
    # ─────────────────────────────────────────────

    def _call_with_fallback(self, system: str, user: str, max_tokens: int = 2048) -> str:
        """Try each LLM in priority order. Backs off on 429 rate limits."""
        import time
        errors = []

        if self.groq.available():
            try:
                r = self.groq.generate(system, user, max_tokens)
                logger.info("[ScriptEngine] Used: Groq")
                return r
            except Exception as e:
                err_str = str(e)
                logger.warning(f"[ScriptEngine] Groq failed: {err_str[:120]}")
                errors.append(f"Groq: {e}")
                if "429" in err_str:
                    logger.info("[ScriptEngine] Groq 429 — waiting 8s before next LLM")
                    time.sleep(8)

        if self.openrouter.available():
            try:
                r = self.openrouter.generate(system, user, max_tokens)
                logger.info("[ScriptEngine] Used: OpenRouter")
                return r
            except Exception as e:
                err_str = str(e)
                logger.warning(f"[ScriptEngine] OpenRouter failed: {err_str[:120]}")
                errors.append(f"OpenRouter: {e}")
                if "429" in err_str:
                    logger.info("[ScriptEngine] OpenRouter 429 — waiting 5s before Gemini")
                    time.sleep(5)

        if self.gemini.available():
            try:
                r = self.gemini.generate(system, user, max_tokens)
                logger.info("[ScriptEngine] Used: Gemini")
                return r
            except Exception as e:
                logger.warning(f"[ScriptEngine] Gemini failed: {str(e)[:120]}")
                errors.append(f"Gemini: {e}")

        raise RuntimeError("All LLMs failed:\n" + "\n".join(errors))

    def _parse_and_validate(self, raw_json: str, topic: str, duration_target: int) -> dict:
        """Parses LLM JSON, validates with Pydantic."""
        raw_json = raw_json.strip()
        if raw_json.startswith("```"):
            raw_json = re.sub(r"```(?:json)?\n?", "", raw_json).strip("`").strip()

        try:
            script = Script.model_validate_json(raw_json)
        except Exception as e:
            logger.warning(f"[ScriptEngine] Direct parse failed: {e}")
            match = re.search(r'\{.*\}', raw_json, re.DOTALL)
            if match:
                try:
                    script = Script.model_validate_json(match.group())
                except Exception as e2:
                    raise ValueError(f"Cannot parse JSON: {e2}\nRaw: {raw_json[:300]}")
            else:
                raise ValueError(f"No JSON in response: {raw_json[:200]}")

        result = script.model_dump()
        logger.info(f"[ScriptEngine] Parsed: '{result['title']}' — {len(result['beats'])} beats")
        return result


# ─────────────────────────────────────────────────────────────────
# Default Topics per channel (used when user doesn't specify a topic)
# These are ONLY used as random seeds — history deduplication filters repeats
# ─────────────────────────────────────────────────────────────────

STOIC_TOPICS = [
    "Overcoming Fear",
    "The Obstacle is the Way",
    "Memento Mori — Remember You Will Die",
    "Amor Fati — Love Your Fate",
    "Discipline is Freedom",
    "The Inner Citadel",
    "Resilience in Hard Times",
    "Controlling What You Can Control",
    "The Dichotomy of Control",
    "Ego is the Enemy",
    "The View from Above",
    "Negative Visualization",
    "Voluntary Hardship",
    "The Daily Practice of Reflection",
    "How to Handle Criticism",
    "Anger — Choosing Your Response",
    "Finding Tranquility in Chaos",
    "Living According to Your Values",
    "The Art of Not Reacting",
    "How to Deal with Failure",
    "The Power of Journaling",
    "Virtue is the Only True Good",
    "Facing Your Own Mortality",
    "Doing Less Better",
    "The Philosophy of Enough",
    "Letting Go of What Others Think",
    "The Present Moment is All You Have",
    "Stillness is the Key",
    "The Power of Indifference",
    "Why Comfort is Your Enemy",
]

TECH_TOPICS = [
    "How Large Language Models Actually Work",
    "How Neural Networks Learn From Data",
    "How ChatGPT Generates Text Word by Word",
    "How Netflix Serves 600 Million Users Without Crashing",
    "How Binary Search Finds Anything in Milliseconds",
    "How Encryption Keeps Your Data Private",
    "How Docker Containers Work Under the Hood",
    "How APIs Connect the Digital World",
    "How Recommendation Algorithms Predict Your Next Watch",
    "How Quantum Computers Use Superposition to Compute",
    "How Git Tracks Every Change You Ever Make",
    "How TCP/IP Actually Moves Data Across the Internet",
    "How Databases Index Billions of Rows in Milliseconds",
    "How Transformers Changed Everything in AI",
    "How Your Phone Predicts Your Next Word",
    "How Gradient Descent Teaches Machines to Learn",
    "How Kubernetes Orchestrates Thousands of Containers",
    "How HTTPS Keeps Every Web Request Secure",
    "How Compilers Turn Code Into Machine Instructions",
    "How Backpropagation Makes Neural Networks Smarter",
]

# Map channel_id → topic list
CHANNEL_TOPICS = {
    "stoic": STOIC_TOPICS,
    "tech":  TECH_TOPICS,
}


def get_random_topic(channel_id: str = "stoic") -> str:
    """Returns a random topic for the given channel. Fully channel-aware."""
    import random
    topics = CHANNEL_TOPICS.get(channel_id, STOIC_TOPICS)
    return random.choice(topics)
