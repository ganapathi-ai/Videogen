"""
THE INNER CITADEL — Script Engine
LLM Priority Chain: Groq (fastest) → OpenRouter (many free models) → Gemini (fallback)

All three APIs have completely FREE tiers — no credit card conflicts:
  • Groq:        14,400 req/day free  | 500+ tok/sec | console.groq.com/keys
  • OpenRouter:  Unlimited free models| `:free` suffix| openrouter.ai/keys
  • Gemini:      1M tokens/day free   | aistudio.google.com/apikey
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
# Pydantic Schema — Forces exact JSON structure from LLM
# ─────────────────────────────────────────────────────────────────

class Beat(BaseModel):
    id: int
    text: str = Field(description="Exactly 5-10 words. One powerful Stoic idea. No filler.")
    emotion: str = Field(description="One of: minimal | deep | emotional | modern | resolute | inspiring | steady | reassuring")
    intent: str = Field(description="Narrative stage: hook | pain | insight | reframe | action | close")
    visual_keywords: List[str] = Field(description="2-3 cinematic search queries for Pexels/Pixabay. E.g. ['roman soldier', 'sunset mountain']")

class Script(BaseModel):
    title: str = Field(description="Cinematic philosophical title")
    topic: str
    duration_target: int = Field(description="Target duration in seconds")
    hook: str = Field(description="Opening hook — max 10 words, creates immediate tension")
    beats: List[Beat]


# ─────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an elite cinematic script writer for "THE INNER CITADEL" — a premium Stoic philosophy YouTube channel targeting 18-35 year olds.

STRICT RULES:
1. Each beat MUST be 5-10 words. Short. Punchy. Powerful. No exceptions.
2. Follow arc: Hook → Pain → Insight → Reframe → Action → Close
3. Use Marcus Aurelius, Epictetus, Seneca — be specific, not generic
4. Language = cinematic spoken word poetry, NOT academic
5. Visual keywords = evocative, cinematic search terms
6. YOU MUST respond ONLY with a valid JSON object. No explanation, no markdown, no preamble.
7. The JSON must exactly match the provided schema."""

def _user_prompt(topic: str, duration_target: int, num_beats: int) -> str:
    return f"""Generate a {duration_target}-second Stoic philosophy video script about: "{topic}"

Target exactly {num_beats} beats.
Each beat = 5-10 words MAXIMUM.
Make it feel urgent, cinematic, personal to the viewer.
Reference specific Stoics and their ideas.

Return ONLY this JSON structure:
{{
  "title": "string",
  "topic": "{topic}",
  "duration_target": {duration_target},
  "hook": "string (max 10 words)",
  "beats": [
    {{
      "id": 1,
      "text": "5-10 word Stoic statement",
      "emotion": "one of: minimal|deep|emotional|modern|resolute|inspiring|steady|reassuring",
      "intent": "one of: hook|pain|insight|reframe|action|close",
      "visual_keywords": ["search term 1", "search term 2"]
    }}
  ]
}}"""


# ─────────────────────────────────────────────────────────────────
# LLM Clients
# ─────────────────────────────────────────────────────────────────

class GroqClient:
    """Groq API — Fastest inference. 14,400 free requests/day."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.base_url = "https://api.groq.com/openai/v1"

    def available(self) -> bool:
        return bool(self.api_key and self.api_key != "YOUR_GROQ_KEY_HERE")

    def generate(self, system: str, user: str) -> str:
        import httpx
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "temperature": 0.75,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},   # Forces JSON output
        }
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


class OpenRouterClient:
    """OpenRouter API — Many free models. Unlimited with :free suffix."""

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.model   = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
        self.base_url = "https://openrouter.ai/api/v1"

    def available(self) -> bool:
        return bool(self.api_key and self.api_key != "YOUR_OPENROUTER_KEY_HERE")

    def generate(self, system: str, user: str) -> str:
        import httpx
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://inner-citadel.app",
            "X-Title": "Inner Citadel",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "temperature": 0.75,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
        }
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class GeminiClient:
    """Google Gemini API — 1M tokens/day free. Last resort fallback."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model   = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    def available(self) -> bool:
        return bool(self.api_key and self.api_key != "YOUR_GEMINI_KEY_HERE")

    def generate(self, system: str, user: str) -> str:
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        m = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system,
        )
        resp = m.generate_content(
            user,
            generation_config=genai.GenerationConfig(
                temperature=0.75,
                response_mime_type="application/json",
            )
        )
        return resp.text


# ─────────────────────────────────────────────────────────────────
# Script Engine — Priority Chain
# ─────────────────────────────────────────────────────────────────

class ScriptEngine:
    """
    Generates Stoic video scripts using LLM priority chain:
    Groq (fastest) → OpenRouter (many free models) → Gemini (fallback)

    All three are completely free with no credit card required.
    """

    def __init__(self):
        self.groq       = GroqClient()
        self.openrouter = OpenRouterClient()
        self.gemini     = GeminiClient()

        # Log which APIs are available
        available = []
        if self.groq.available():       available.append(f"Groq ({self.groq.model})")
        if self.openrouter.available(): available.append(f"OpenRouter ({self.openrouter.model})")
        if self.gemini.available():     available.append(f"Gemini ({self.gemini.model})")

        if not available:
            raise ValueError(
                "❌ No LLM API keys found!\n"
                "Set at least ONE of: GROQ_API_KEY, OPENROUTER_API_KEY, or GEMINI_API_KEY\n"
                "See CREDENTIALS_SETUP.md for instructions."
            )
        logger.info(f"[ScriptEngine] Available LLMs: {', '.join(available)}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_script(self, topic: str, length: str = "short") -> dict:
        """
        Generates a structured Stoic video script.

        Args:
            topic: e.g. "Overcoming Fear", "Memento Mori"
            length: "short" (~35s, 7 beats) | "medium" (~60s, 12 beats)

        Returns:
            dict: Validated script with title, beats, visual_keywords
        """
        duration_target = 35 if length == "short" else 60
        num_beats       = 7  if length == "short" else 12

        system = SYSTEM_PROMPT
        user   = _user_prompt(topic, duration_target, num_beats)

        raw_json = self._call_with_fallback(system, user)
        return self._parse_and_validate(raw_json, topic, duration_target)

    def _call_with_fallback(self, system: str, user: str) -> str:
        """Try each LLM in priority order. Raises only if ALL fail."""
        errors = []

        # 1. Groq — fastest, try first
        if self.groq.available():
            try:
                result = self.groq.generate(system, user)
                logger.info("[ScriptEngine] ✅ Used: Groq")
                return result
            except Exception as e:
                logger.warning(f"[ScriptEngine] Groq failed: {e}")
                errors.append(f"Groq: {e}")

        # 2. OpenRouter — many free models
        if self.openrouter.available():
            try:
                result = self.openrouter.generate(system, user)
                logger.info("[ScriptEngine] ✅ Used: OpenRouter")
                return result
            except Exception as e:
                logger.warning(f"[ScriptEngine] OpenRouter failed: {e}")
                errors.append(f"OpenRouter: {e}")

        # 3. Gemini — last resort
        if self.gemini.available():
            try:
                result = self.gemini.generate(system, user)
                logger.info("[ScriptEngine] ✅ Used: Gemini")
                return result
            except Exception as e:
                logger.warning(f"[ScriptEngine] Gemini failed: {e}")
                errors.append(f"Gemini: {e}")

        raise RuntimeError(f"All LLMs failed:\n" + "\n".join(errors))

    def _parse_and_validate(self, raw_json: str, topic: str, duration_target: int) -> dict:
        """Parses LLM JSON response and validates with Pydantic."""
        # Strip markdown fences if present
        raw_json = raw_json.strip()
        if raw_json.startswith("```"):
            raw_json = re.sub(r"```(?:json)?\n?", "", raw_json).strip("`").strip()

        try:
            script = Script.model_validate_json(raw_json)
        except Exception as e:
            logger.warning(f"[ScriptEngine] Direct parse failed: {e}")
            # Try extracting JSON object
            match = re.search(r'\{.*\}', raw_json, re.DOTALL)
            if match:
                try:
                    script = Script.model_validate_json(match.group())
                except Exception as e2:
                    raise ValueError(f"Could not parse JSON: {e2}\nRaw: {raw_json[:300]}")
            else:
                raise ValueError(f"No JSON found in response: {raw_json[:200]}")

        result = script.model_dump()
        logger.info(f"[ScriptEngine] ✅ Script: '{result['title']}' — {len(result['beats'])} beats")
        return result


# ─────────────────────────────────────────────────────────────────
# Pre-seeded Stoic Topics (30 included)
# ─────────────────────────────────────────────────────────────────

STOIC_TOPICS = [
    "Overcoming Fear",
    "The Obstacle is the Way",
    "Memento Mori — Remember You Will Die",
    "Amor Fati — Love Your Fate",
    "Discipline is Freedom",
    "The Inner Citadel",
    "Stoic Resilience in Hard Times",
    "Controlling What You Can Control",
    "The Dichotomy of Control",
    "Ego is the Enemy",
    "Morning Meditation of Marcus Aurelius",
    "Seneca on the Shortness of Time",
    "Epictetus: You Are Your Choices",
    "The View from Above",
    "Negative Visualization",
    "Voluntary Hardship",
    "The Stoic Daily Practice",
    "How to Handle Criticism Stoically",
    "Anger — The Stoic Perspective",
    "Finding Tranquility in Chaos",
    "Living According to Nature",
    "The Art of Not Reacting",
    "How to Deal with Failure",
    "The Power of Stoic Journaling",
    "Virtue is the Only True Good",
    "How Stoics Face Death",
    "Doing Less, Better",
    "The Philosophy of Enough",
    "Letting Go of What Others Think",
    "The Present Moment is All You Have",
]


def get_random_topic() -> str:
    import random
    return random.choice(STOIC_TOPICS)
