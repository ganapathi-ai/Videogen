"""
NeuralBaba Empire — Channel Configuration System

Two channels — COMPLETELY SEPARATE, no mixing:
  1. STOIC PHILOSOPHY  — Channel name: "The Inner Citadel"  (@TheInnerCitadel)
  2. TECH EXPLAINER    — Channel name: "neuralbaba_empire"  (@neuralbaba_empire)

Research basis:
  Stoic:  Daily Stoic (4M), Einzelgänger (2.3M), Philosophies for Life (1.2M)
  Tech:   Fireship (3.8M), ByteByteGo (1.1M), 3Blue1Brown (6.2M),
          Two Minute Papers (1.6M), CodeAesthetic (550K), Computerphile (2.4M)

SEO keywords, topics, voices, system prompts — all channel-specific.
History files are also separate (history_stoic.jsonl / history_tech.jsonl).
"""

from typing import Dict, Any

# ─────────────────────────────────────────────────────────────────
# Channel Definitions
# ─────────────────────────────────────────────────────────────────

CHANNELS: Dict[str, Dict[str, Any]] = {

    # ═══════════════════════════════════════════════════════════════
    # CHANNEL 1: Stoic Philosophy
    # YouTube/Instagram name: "The Inner Citadel"
    # ═══════════════════════════════════════════════════════════════
    "stoic": {
        "id":            "stoic",
        "name":          "The Inner Citadel",        # EXACT channel name
        "handle":        "@TheInnerCitadel",
        "watermark":     "The Inner Citadel",        # Watermark on all stoic videos
        "tagline":       "Ancient Wisdom. Modern Clarity.",
        "description":   "Stoic philosophy for daily life — discipline, resilience, mindset.",
        "emoji":         "🏛️",
        "accent_color":  "#C4A064",                  # Gold — stoic brand color
        "theme":         "dark_gold",
        "default_voice": "gb_ryan",                  # Deep British — philosophy standard
        "default_length": "short",
        "default_aspect": "9:16",                    # Shorts/Reels default

        "visual_keywords_prefix": ["cinematic", "ancient", "stoic", "dramatic", "philosophy"],
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

        # ── System Prompt — The Inner Citadel
        # Research: Einzelgänger, Daily Stoic, Philosophies for Life narration style
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

    # ═══════════════════════════════════════════════════════════════
    # CHANNEL 2: Tech Concept Explainer
    # YouTube/Instagram name: "neuralbaba_empire"
    # ═══════════════════════════════════════════════════════════════
    "tech": {
        "id":            "tech",
        "name":          "neuralbaba_empire",        # EXACT channel name
        "handle":        "@neuralbaba_empire",
        "watermark":     "neuralbaba_empire",        # Watermark on all tech videos
        "tagline":       "How Technology Actually Works.",
        "description":   "Tech concept explainers — AI, systems, and code made simple.",
        "emoji":         "💻",
        "accent_color":  "#00D4FF",                  # Electric cyan — tech brand color
        "theme":         "dark_tech",
        "default_voice": "us_christopher",           # Deep documentary narrator — best for tech
        "default_length": "short",
        "default_aspect": "9:16",                    # Reels-first for Instagram growth

        # Visual keywords for concept explainer footage searches
        "visual_keywords_prefix": [
            "computer", "server", "network", "data center",
            "code", "circuit", "digital", "processor",
        ],
        "bgm_style": "electronic_minimal",

        # ── SEO Keywords
        # Research: Fireship, ByteByteGo, 3Blue1Brown, Two Minute Papers, Computerphile
        # Focus: "how X works" search intent — concept explainer keywords
        "seo_tags": [
            "how AI works", "machine learning explained", "neural networks explained",
            "system design", "how ChatGPT works", "transformer model explained",
            "how algorithms work", "data structures explained", "how the internet works",
            "how databases work", "how Python works", "deep learning explained",
            "how LLMs work", "RAG explained", "how search engines work",
            "distributed systems", "API explained", "how blockchain works",
            "computer science explained", "tech explained simply",
            "artificial intelligence explained", "how Netflix works",
            "how Google works", "software engineering explained",
            "coding concepts", "programming explained", "AI concepts",
            "neuralbaba", "tech concepts", "computer science basics",
        ],

        # ── 50 Concept Explainer Topics (HOW things work)
        # Research: Fireship "100 Seconds" format, ByteByteGo system design,
        # 3Blue1Brown visual math, Two Minute Papers AI research, CodeAesthetic essays
        # KEY PRINCIPLE: Every topic answers "HOW does X work?" — not "why X is important"
        "topics": [
            # HOW AI / ML WORKS (highest search volume — concept explainer)
            "How Large Language Models Actually Work",
            "How Neural Networks Learn From Data",
            "How ChatGPT Generates Text Word by Word",
            "How Transformers Changed Everything in AI",
            "How DALL-E Generates Images From Text",
            "How Reinforcement Learning Teaches AI to Play Games",
            "How AI Agents Make Decisions Autonomously",
            "How RAG Makes AI Smarter Without Retraining",
            "How Diffusion Models Create Images From Noise",
            "How Attention Mechanism Works in Transformers",
            "How Embeddings Turn Words Into Numbers",
            "How AlphaFold Solved Protein Folding",

            # HOW SYSTEMS WORK (ByteByteGo / system design style)
            "How Netflix Serves 600 Million Users Without Crashing",
            "How Google Search Indexes the Entire Internet",
            "How WhatsApp Delivers 100 Billion Messages a Day",
            "How Uber Matches Millions of Riders in Real Time",
            "How DNS Translates a Domain Name to an IP Address",
            "How HTTP and HTTPS Actually Work",
            "How Load Balancers Distribute Traffic Across Servers",
            "How Databases Store and Retrieve Data",
            "How Git Tracks Every Change in Your Code",
            "How Docker Containers Work Under the Hood",
            "How APIs Connect the Digital World",
            "How TCP Ensures Your Data Arrives Intact",

            # HOW ALGORITHMS WORK (3Blue1Brown / visual explainer style)
            "How Binary Search Finds Anything in Milliseconds",
            "How Sorting Algorithms Actually Work",
            "How Dijkstra Finds the Shortest Path",
            "How Hash Tables Work in Constant Time",
            "How Recursion Solves Impossible Problems Simply",
            "How Encryption Keeps Your Data Private",
            "How Compression Shrinks Files Without Losing Data",
            "How Recommendation Algorithms Predict Your Next Watch",
            "How PageRank Made Google the World's Search Engine",
            "How A/B Testing Drives Every Big Tech Decision",

            # HOW CODE / PLATFORMS WORK (Fireship / CodeAesthetic style)
            "How Python Executes Your Code Line by Line",
            "How JavaScript Event Loop Works",
            "How React Renders Only What Changed on Screen",
            "How SQL Queries Execute Inside a Database",
            "How Garbage Collection Frees Memory Automatically",
            "How Cloud Computing Works Behind the Scenes",
            "How Microservices Split One App Into Many",
            "How Kubernetes Orchestrates Thousands of Containers",
            "How WebSockets Enable Real-Time Communication",
            "How OAuth Lets You Log In With Google Safely",

            # CONCEPT EXPLAINERS — EMERGING TECH
            "How Quantum Computers Use Superposition to Compute",
            "How Zero Knowledge Proofs Work",
            "How Blockchain Achieves Consensus Without a Central Authority",
            "How Edge Computing Brings Processing Closer to You",
            "How Autonomous Cars Perceive and Navigate the World",
            "How Brain-Computer Interfaces Read Neural Signals",

            # LONG FORM concept explainers (>3 min deep dives)
            "A Complete Guide to How Machine Learning Works",
            "How the Internet Was Built — From Packets to Pages",
            "The Complete History of Artificial Intelligence",
            "How Modern AI Systems Are Actually Trained",
        ],

        # ── System Prompt — neuralbaba_empire
        # ─────────────────────────────────────────────────────────
        # Research basis (what makes these channels succeed):
        #
        # FIRESHIP (3.8M): Start with a surprising fact. Explain concept in fast dense
        #   layers. Use analogies. "Here is how X works in 100 seconds." No filler.
        #   Example: "A neural network is just a function. But not just any function."
        #
        # BYTEBYTEGO (1.1M): Start with a real-world problem. Show how the system
        #   solves it step by step. Concrete examples: Netflix, Google, Uber.
        #   Example: "Imagine you need to serve 1 million requests per second..."
        #
        # 3BLUE1BROWN (6.2M): Start with intuition. Build up simple → complex → insight.
        #   Every statement earns its place. The perfect analogy. No wasted words.
        #   Example: "Think of it this way. A matrix is just a transformation of space."
        #
        # TWO MINUTE PAPERS (1.6M): Celebrate the discovery. Make viewer feel the
        #   excitement. "What a time to be alive!" Convey genuine wonder.
        #   Example: "This paper can generate a photo-realistic human face from scratch."
        #
        # CODEAESTHETIC (550K): Treat engineering as philosophy. Short punchy sentences.
        #   Poetic clarity about code and systems. "Clean code is communication."
        #
        # WHAT ALL SHARE:
        #   - HOOK: surprising fact, paradox, or question first
        #   - GRADUAL BUILDUP: simple → complex → insight
        #   - ANALOGIES: tech concept = everyday comparison
        #   - CONCRETE NUMBERS: real companies, real scale
        #   - AHA MOMENT: the payoff insight
        #   - SPEAK TO the viewer, not AT them
        "system_prompt": """You are an elite concept explainer narrator writing scripts for NEURALBABA_EMPIRE — a tech concept explainer YouTube/Instagram channel in the style of Fireship + ByteByteGo + 3Blue1Brown.

YOUR MISSION: Explain HOW technology actually works. MECHANISMS. Concepts. Step-by-step understanding. NOT motivation. NOT career advice. NOT proclamations.

CONCEPT EXPLAINER STRUCTURE (this arc every time):
  Beats 1-2  : HOOK — Surprising fact, paradox, or question that creates instant curiosity
  Beats 3-4  : SETUP — The real-world problem this technology solves
  Beats 5-7  : MECHANISM — HOW it actually works (simple then complex then insight)
  Beats 8-9  : THE AHA MOMENT — The key insight that makes the viewer say "I get it now"
  Beat 10    : PAYOFF — Why this changes how the viewer sees the world

LANGUAGE PATTERNS from top channels (use these):
  Fireship style:       "Here is how it works. A neural network is just a function."
  ByteByteGo style:     "Imagine you need to handle one million users at once."
  3Blue1Brown style:    "Think of it this way. Every matrix transforms space."
  Two Min Papers style: "This result is genuinely remarkable. The system learned this on its own."
  CodeAesthetic style:  "Clean code is not about style. It is about communication."

ANALOGIES — always use one vivid everyday comparison:
  Hash tables  : like a library's card catalog — find any book in one step
  TCP protocol : like certified mail — must be acknowledged before continuing
  Attention    : like a spotlight that knows exactly where to look
  Load balancer: like a traffic officer directing cars to the emptiest lane
  Embeddings   : like coordinates on a map where similar concepts live close together

CRITICAL RULES — every one matters:
1. EXPLAIN THE MECHANISM — say HOW it works not just THAT it works
2. NEVER use commas. Use short separate sentences instead. TTS reads them naturally.
3. Each beat = 6-12 words. ONE idea. ONE mechanism. ONE fact.
4. Use concrete numbers: "Netflix processes 500 billion events per day"
5. Use ONE vivid analogy per concept explanation
6. Build gradually: simple fact → deeper layer → the core insight
7. No colons. No semicolons. No parentheses. No dashes. Only periods and exclamation marks.
8. YOU MUST respond ONLY with valid JSON. No explanation. No markdown. No preamble.
9. The JSON must exactly match the schema provided.
10. Each beat must be COMPLETELY UNIQUE — never repeat the same idea.
11. NEVER use philosopher names. NEVER use motivational clichés. Explain technology.
12. NEVER start with "You need to know this" or "This changes everything" — show it instead.""",
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
