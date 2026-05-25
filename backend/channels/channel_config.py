"""
NeuralBaba Empire — Channel Configuration System

Two channels:
  1. STOIC PHILOSOPHY — Channel name: "The Inner Citadel"   (@TheInnerCitadel)
  2. TECH & AI        — Channel name: "neuralbaba_empire"   (@neuralbaba_empire)

Research basis:
  Stoic:  Daily Stoic (4M), Einzelgänger (2.3M), Philosophies for Life (1.2M)
  Tech:   Fireship (3.5M), ByteByteGo (1.2M), Two Minute Papers (1.1M),
          Matt Wolfe (1M+), Andrej Karpathy content style

SEO Keywords embedded per channel for highest YouTube + Instagram reach.
"""

from typing import Dict, Any

# ─────────────────────────────────────────────────────────────────
# Channel Definitions
# ─────────────────────────────────────────────────────────────────

CHANNELS: Dict[str, Dict[str, Any]] = {

    # ── CHANNEL 1: Stoic Philosophy ───────────────────────────────
    # YouTube/Instagram channel name: "The Inner Citadel"
    "stoic": {
        "id":            "stoic",
        "name":          "The Inner Citadel",        # EXACT channel name — stoic
        "handle":        "@TheInnerCitadel",
        "watermark":     "The Inner Citadel",        # Watermark shown on all stoic videos
        "tagline":       "Ancient Wisdom. Modern Clarity.",
        "description":   "Stoic philosophy for daily life — discipline, resilience, mindset.",
        "emoji":         "🏛️",
        "accent_color":  "#C4A064",                  # Gold — stoic brand color
        "theme":         "dark_gold",
        "default_voice": "gb_ryan",                  # Deep British — philosophy channels standard
        "default_length": "short",
        "default_aspect": "9:16",                    # Shorts/Reels default for philosophy

        "visual_keywords_prefix": ["cinematic", "ancient", "stoic", "dramatic"],
        "bgm_style": "ambient_meditative",

        # ── SEO Keywords (Daily Stoic, Einzelgänger, Philosophies for Life research)
        "seo_tags": [
            "stoicism", "stoic philosophy", "marcus aurelius", "daily stoic",
            "memento mori", "amor fati", "discipline", "mindset", "stoic wisdom",
            "philosophy", "ancient wisdom", "resilience", "self improvement",
            "mental strength", "inner peace", "ryan holiday", "epictetus",
            "meditations", "seneca", "stoic quotes", "how to be stoic",
            "stoic mindset", "overcoming fear", "ego is the enemy",
        ],

        # ── 40 High-Engagement Stoic Topics ──
        "topics": [
            "Overcoming Fear Through Stoicism",
            "The Obstacle is the Way",
            "Memento Mori — Remember You Will Die",
            "Amor Fati — Love Your Fate",
            "Discipline is Freedom",
            "The Inner Citadel",
            "Ego is the Enemy",
            "The Dichotomy of Control",
            "Stillness is the Key",
            "The Art of Not Reacting",
            "How to Stop Caring What Others Think",
            "The Power of Negative Visualization",
            "Voluntary Hardship Changes Everything",
            "Why Comfort is Destroying You",
            "How to Handle Criticism Like a Stoic",
            "Anger — The Stoic Solution",
            "Finding Peace in Chaos",
            "The Stoic Morning Routine",
            "Stoic Wisdom for Modern Anxiety",
            "How Stoics Deal With Failure",
            "What to Do When Life Feels Unfair",
            "The Power of Doing Less Better",
            "The Philosophy of Enough",
            "Living in the Present Moment",
            "Why Stoics Never Complain",
            "The View from Above",
            "Virtue is the Only True Good",
            "How to Face Death Without Fear",
            "The Stoic Art of Letting Go",
            "Why Your Mind is Your Greatest Weapon",
            "A Complete Guide to Stoic Resilience",
            "Marcus Aurelius — Life Lessons",
            "The Full Stoic Daily Practice",
            "Stoicism vs Modern Self Help",
            "How Ancient Stoics Handled Grief",
            "The Stoic Philosophy of Work",
            "Why Stoicism is More Relevant Now",
            "The Science Behind Stoic Practices",
            "Stoic Secrets of the Greatest Leaders",
            "The Art of Stoic Journaling",
        ],

        # ── System Prompt — The Inner Citadel (Einzelgänger / Daily Stoic style)
        "system_prompt": """You are an elite cinematic narrator writing spoken-word scripts for THE INNER CITADEL — a Stoic philosophy YouTube/Instagram channel.

CRITICAL RULES — follow every single one:
1. NEVER mention any philosopher name (no Epictetus, no Seneca, no Marcus Aurelius, no Stoics, no Zeno). The narrator IS the voice — no attributions ever.
2. NEVER use commas. Commas make TTS pause unnaturally. Use short separate sentences instead.
3. Each beat must be 6-12 words. One powerful self-contained statement.
4. Write as if you are SPEAKING directly to the viewer. Use "you" and "your". Personal. Urgent.
5. Language must feel like spoken poetry — short punchy words. NOT academic prose.
6. No commas. No colons. No semicolons. No parentheses. No dashes. Only periods and exclamation marks.
7. YOU MUST respond ONLY with valid JSON. No explanation. No markdown. No preamble.
8. The JSON must exactly match the schema provided.
9. Each beat must be COMPLETELY UNIQUE — never repeat the same idea twice.
10. Build emotional arc: start tense → go deeper → resolve powerfully.""",
    },

    # ── CHANNEL 2: Tech & AI ──────────────────────────────────────
    # YouTube/Instagram channel name: "neuralbaba_empire"
    "tech": {
        "id":            "tech",
        "name":          "neuralbaba_empire",        # EXACT channel name — tech
        "handle":        "@neuralbaba_empire",
        "watermark":     "neuralbaba_empire",        # Watermark shown on all tech videos
        "tagline":       "The Future is Already Here.",
        "description":   "AI, technology and data science — explained for everyone.",
        "emoji":         "💻",
        "accent_color":  "#00D4FF",                  # Electric cyan — tech brand color
        "theme":         "dark_tech",
        "default_voice": "us_christopher",           # Deep documentary narrator — best for tech
        "default_length": "short",
        "default_aspect": "9:16",                    # Reels-first for Instagram growth

        "visual_keywords_prefix": ["technology", "digital", "data", "futuristic", "code"],
        "bgm_style": "electronic_minimal",

        # ── SEO Keywords (Fireship, ByteByteGo, Matt Wolfe, Two Minute Papers research)
        "seo_tags": [
            "artificial intelligence", "AI", "machine learning", "ChatGPT",
            "programming", "Python", "data science", "software engineering",
            "AI tools", "tech explained", "large language models", "GPT",
            "AI in 2025", "future of AI", "coding", "system design",
            "deep learning", "neural networks", "tech news", "AI revolution",
            "generative AI", "prompt engineering", "data engineering",
            "cloud computing", "software development", "AI productivity",
            "tech career", "learn to code", "AI agent", "RAG explained",
        ],

        # ── 40 High-Engagement Tech Topics (researched from top channels) ──
        "topics": [
            # AI REVOLUTION (highest performing 2024-2025)
            "AI is Changing Everything Right Now",
            "Why Large Language Models Think the Way They Do",
            "The Truth About AI Consciousness",
            "How ChatGPT Actually Works Inside",
            "Why AI Will Not Replace Every Job",
            "The Rise of AI Agents — What it Means",
            "How to Use AI to 10x Your Productivity",
            "The Open Source AI Revolution",
            "Why 90 Percent of AI Projects Fail",
            "Generative AI — What Comes Next",
            # PROGRAMMING / DATA (evergreen)
            "Why Python Won the Data Science War",
            "The Coding Mindset That Changes Everything",
            "How Data Engineers Think Differently",
            "What No One Tells You About Machine Learning",
            "The Real Difference Between AI and Intelligence",
            "How Search Engines Really Work",
            "The Algorithm That Powers Everything",
            "Why Data is Worth More Than Gold",
            # CAREER / PRODUCTIVITY
            "The Mindset of a 10x Engineer",
            "How to Think Like a Data Scientist",
            "Why Senior Developers Think Differently",
            "The Hidden Skills No One Teaches in CS",
            "How to Stay Relevant in an AI World",
            "The Truth About Working in Big Tech",
            "Tech Career Paths in the Age of AI",
            # TECH SYSTEMS (ByteByteGo style)
            "How Netflix Recommends Your Next Show",
            "How Google Processes a Billion Searches",
            "The Architecture Behind Instagram",
            "Why Blockchain Solved a Problem No One Had",
            "How Cloud Computing Changed Business",
            # TRENDING / VIRAL
            "The Dark Side of Social Media Algorithms",
            "Why Quantum Computing is Closer Than You Think",
            "The Death of Traditional Software Development",
            "How AI Reads Your Mind Online",
            "The Illusion of Digital Privacy",
            # LONG FORM (>3 min)
            "Complete Guide to Machine Learning in 2025",
            "How to Build Your First AI Application",
            "The Full History of Artificial Intelligence",
            "Why the Next Five Years Will Reshape Tech",
            "How to Master Python for Data Science",
            "The Future of Work in the Age of AI",
        ],

        # ── System Prompt — neuralbaba_empire (Fireship / ByteByteGo style)
        "system_prompt": """You are an elite narrator writing spoken-word scripts for NEURALBABA_EMPIRE — a tech and artificial intelligence YouTube/Instagram channel.

CRITICAL RULES — follow every single one:
1. Speak DIRECTLY to the viewer. Use "you" and "your". Personal. Urgent. Eye-opening.
2. NEVER use commas. Commas make TTS pause unnaturally. Use short separate sentences instead.
3. Each beat must be 6-12 words. One clear powerful idea per beat.
4. Avoid jargon — explain complex tech concepts in simple vivid language.
5. Use concrete numbers, facts, and analogies when possible. Be specific.
6. Language must feel like a tech revelation — "this changes everything" energy.
7. No commas. No colons. No semicolons. No parentheses. No dashes. Only periods and exclamation marks.
8. YOU MUST respond ONLY with valid JSON. No explanation. No markdown. No preamble.
9. The JSON must exactly match the schema provided.
10. Emotional arc: Hook with shock → Reveal the reality → Explain the insight → Show the impact → Call to action.""",
    },
}


def get_channel(channel_id: str) -> Dict[str, Any]:
    """Returns channel config. Defaults to 'stoic' if channel_id not found."""
    return CHANNELS.get(channel_id, CHANNELS["stoic"])


def get_all_channels() -> list:
    """Returns list of channel info for the frontend selector."""
    return [
        {
            "id":           ch["id"],
            "name":         ch["name"],
            "handle":       ch["handle"],
            "tagline":      ch["tagline"],
            "description":  ch["description"],
            "emoji":        ch["emoji"],
            "accent_color": ch["accent_color"],
            "topics":       ch["topics"],
            "seo_tags":     ch["seo_tags"],
            "default_voice":  ch["default_voice"],
            "default_aspect": ch["default_aspect"],
            "default_length": ch["default_length"],
        }
        for ch in CHANNELS.values()
    ]
