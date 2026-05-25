"""
THE INNER CITADEL — API Key Verifier
Run this BEFORE starting the app to confirm all credentials work.

Usage:
    cd c:\\projects\\YOUTUBE_WEBAPP\\backend
    python verify_keys.py

It will test each API key and print a clear ✅ / ❌ result.
"""

import os
import sys
import json
from dotenv import load_dotenv

# Load .env from project root (one level up from backend/)
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

# ANSI colors for terminal output
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
CYAN   = "\033[96m"

def ok(msg):    print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg):  print(f"  {RED}❌ {msg}{RESET}")
def warn(msg):  print(f"  {YELLOW}⚠️  {msg}{RESET}")
def info(msg):  print(f"  {CYAN}ℹ️  {msg}{RESET}")

def section(title):
    print(f"\n{BOLD}{title}{RESET}")
    print("─" * 50)

passed = 0
failed = 0
warned = 0

# ─────────────────────────────────────────────
section("1. GROQ API KEY (Primary LLM)")
# ─────────────────────────────────────────────
groq_key = os.getenv("GROQ_API_KEY", "")
if not groq_key or groq_key == "YOUR_GROQ_KEY_HERE":
    fail("GROQ_API_KEY not set")
    info("Get free key: https://console.groq.com/keys")
    failed += 1
else:
    try:
        import httpx
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": "Say: OK"}],
                "max_tokens": 5,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            ok(f"Groq API works! Model: llama-3.1-8b-instant")
            passed += 1
        else:
            fail(f"Groq returned HTTP {resp.status_code}: {resp.text[:100]}")
            failed += 1
    except Exception as e:
        fail(f"Groq connection error: {e}")
        failed += 1

# ─────────────────────────────────────────────
section("2. OPENROUTER API KEY (Fallback LLM)")
# ─────────────────────────────────────────────
or_key = os.getenv("OPENROUTER_API_KEY", "")
if not or_key or or_key == "YOUR_OPENROUTER_KEY_HERE":
    warn("OPENROUTER_API_KEY not set (optional — Groq is primary)")
    info("Get free key: https://openrouter.ai/keys")
    warned += 1
else:
    try:
        import httpx
        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {or_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://inner-citadel.app",
            },
            json={
                "model": "meta-llama/llama-3.1-8b-instruct:free",
                "messages": [{"role": "user", "content": "Say: OK"}],
                "max_tokens": 5,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            ok("OpenRouter API works! Free model: llama-3.1-8b-instruct:free")
            passed += 1
        else:
            fail(f"OpenRouter returned HTTP {resp.status_code}: {resp.text[:100]}")
            failed += 1
    except Exception as e:
        fail(f"OpenRouter error: {e}")
        failed += 1

# ─────────────────────────────────────────────
section("3. GEMINI API KEY (Last-Resort LLM)")
# ─────────────────────────────────────────────
gemini_key = os.getenv("GEMINI_API_KEY", "")
if not gemini_key or gemini_key == "YOUR_GEMINI_KEY_HERE":
    warn("GEMINI_API_KEY not set (optional if Groq/OpenRouter work)")
    info("Get free key: https://aistudio.google.com/apikey")
    warned += 1
else:
    try:
        import httpx
        resp = httpx.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}",
            timeout=10,
        )
        if resp.status_code == 200:
            ok("Gemini API key is valid!")
            passed += 1
        else:
            fail(f"Gemini returned HTTP {resp.status_code}: {resp.text[:100]}")
            failed += 1
    except Exception as e:
        fail(f"Gemini error: {e}")
        failed += 1

# ─────────────────────────────────────────────
section("4. PEXELS API KEY (Stock Video — Primary)")
# ─────────────────────────────────────────────
pexels_key = os.getenv("PEXELS_API_KEY", "")
if not pexels_key or pexels_key == "YOUR_PEXELS_KEY_HERE":
    fail("PEXELS_API_KEY not set")
    info("Get free key: https://www.pexels.com/api/")
    failed += 1
else:
    try:
        import httpx
        resp = httpx.get(
            "https://api.pexels.com/videos/search?query=nature&per_page=1",
            headers={"Authorization": pexels_key},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            total = data.get("total_results", 0)
            ok(f"Pexels API works! ({total:,} videos available for 'nature')")
            passed += 1
        else:
            fail(f"Pexels returned HTTP {resp.status_code}")
            failed += 1
    except Exception as e:
        fail(f"Pexels error: {e}")
        failed += 1

# ─────────────────────────────────────────────
section("5. PIXABAY API KEY (Stock Video — Fallback)")
# ─────────────────────────────────────────────
pixabay_key = os.getenv("PIXABAY_API_KEY", "")
if not pixabay_key or pixabay_key == "YOUR_PIXABAY_KEY_HERE":
    warn("PIXABAY_API_KEY not set (optional — Pexels is primary)")
    info("Get free key: https://pixabay.com/api/docs/")
    warned += 1
else:
    try:
        import httpx
        resp = httpx.get(
            f"https://pixabay.com/api/videos/?key={pixabay_key}&q=nature&per_page=3",
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            total = data.get("totalHits", 0)
            ok(f"Pixabay API works! ({total:,} videos for 'nature')")
            passed += 1
        else:
            fail(f"Pixabay returned HTTP {resp.status_code}: {resp.text[:100]}")
            failed += 1
    except Exception as e:
        fail(f"Pixabay error: {e}")
        failed += 1

# ─────────────────────────────────────────────
section("6. REDIS CONNECTION (Celery Queue)")
# ─────────────────────────────────────────────
redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
info(f"URL: {redis_url[:50]}...")
try:
    import redis as redis_lib
    # Parse URL and connect
    if redis_url.startswith("rediss://"):
        r = redis_lib.from_url(redis_url, ssl_cert_reqs=None)
    else:
        r = redis_lib.from_url(redis_url)
    r.ping()
    ok("Redis connection successful! Queue is ready.")
    passed += 1
except ImportError:
    warn("redis package not installed yet. Run: pip install redis")
    warned += 1
except Exception as e:
    fail(f"Redis connection failed: {e}")
    if "localhost" in redis_url:
        info("Local Redis not running. Start with: docker run -d -p 6379:6379 redis:alpine")
        info("OR use Upstash Redis (free cloud): https://upstash.com")
    else:
        info("Check your Upstash Redis URL in .env")
    failed += 1

# ─────────────────────────────────────────────
section("7. SYSTEM DEPENDENCIES")
# ─────────────────────────────────────────────

# FFmpeg
try:
    import subprocess
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
    if result.returncode == 0:
        version = result.stdout.decode()[:40].strip()
        ok(f"FFmpeg installed: {version}")
        passed += 1
    else:
        fail("FFmpeg not found in PATH")
        info("Install: winget install ffmpeg  OR  https://ffmpeg.org/download.html")
        failed += 1
except FileNotFoundError:
    fail("FFmpeg not found")
    info("Install: winget install ffmpeg  OR  https://ffmpeg.org/download.html")
    failed += 1
except Exception as e:
    warn(f"FFmpeg check error: {e}")
    warned += 1

# Python packages
for pkg, import_name, pip_name in [
    ("FastAPI",        "fastapi",     "fastapi"),
    ("Celery",         "celery",      "celery"),
    ("MoviePy",        "moviepy",     "moviepy"),
    ("pysubs2",        "pysubs2",     "pysubs2"),
    ("SentenceTransf", "sentence_transformers", "sentence-transformers"),
    ("FAISS",          "faiss",       "faiss-cpu"),
    ("httpx",          "httpx",       "httpx"),
]:
    try:
        __import__(import_name)
        ok(f"{pkg} installed")
        passed += 1
    except ImportError:
        fail(f"{pkg} not installed — run: pip install {pip_name}")
        failed += 1

# Kokoro TTS (optional — downloads on first use)
try:
    import kokoro
    ok("Kokoro TTS installed")
    passed += 1
except ImportError:
    warn("Kokoro TTS not installed. Install: pip install kokoro")
    info("It will auto-download the model (~300MB) on first video generation")
    warned += 1

# WhisperX
try:
    import whisperx
    ok("WhisperX installed")
    passed += 1
except ImportError:
    warn("WhisperX not installed. Install: pip install whisperx")
    info("Required for word-level audio alignment")
    warned += 1

# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
print(f"\n{'═'*50}")
print(f"{BOLD}VERIFICATION SUMMARY{RESET}")
print(f"{'═'*50}")
print(f"  {GREEN}✅ Passed:  {passed}{RESET}")
print(f"  {YELLOW}⚠️  Warnings: {warned}{RESET}")
print(f"  {RED}❌ Failed:  {failed}{RESET}")
print(f"{'═'*50}\n")

if failed == 0:
    print(f"{GREEN}{BOLD}🚀 ALL CRITICAL CHECKS PASSED! You're ready to generate videos.{RESET}")
    print(f"   Run: start_dev.bat  (or start services manually)")
elif failed <= 2:
    print(f"{YELLOW}{BOLD}⚠️  Almost ready — fix the {failed} failed item(s) above.{RESET}")
    print(f"   See CREDENTIALS_SETUP.md for step-by-step instructions.")
else:
    print(f"{RED}{BOLD}❌ Multiple items need attention. See CREDENTIALS_SETUP.md{RESET}")
    print(f"   At minimum you need: GROQ_API_KEY + PEXELS_API_KEY + Redis")

print()
sys.exit(0 if failed == 0 else 1)
