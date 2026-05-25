# 🔐 THE INNER CITADEL — Complete Setup Guide
> **Intel CPU Mode | 30GB RAM | Vercel + Ngrok | Zero Cost**
> All free, no credit card needed for anything.

---

## What You Need (6 Free APIs + 1 Tunnel)

| # | What | Service | Time | Card? |
|---|---|---|---|---|
| 1 | `GROQ_API_KEY` | Groq (Primary LLM) | 2 min | ❌ No |
| 2 | `OPENROUTER_API_KEY` | OpenRouter (Fallback LLM) | 2 min | ❌ No |
| 3 | `PEXELS_API_KEY` | Pexels (Video Clips) | 3 min | ❌ No |
| 4 | `PIXABAY_API_KEY` | Pixabay (Video Clips) | 2 min | ❌ No |
| 5 | `GEMINI_API_KEY` | Gemini (Last-Resort LLM) | 2 min | ❌ No |
| 6 | `NGROK_AUTHTOKEN` | Ngrok (Vercel Tunnel) | 2 min | ❌ No |

> **Bare minimum to test:** GROQ_API_KEY + PEXELS_API_KEY. Everything else is optional.

---

## Step 1 — GROQ API KEY ⚡ (Do This First — Fastest LLM)

1. Go to → **https://console.groq.com/keys**
2. Click **"Sign Up"** → Google or GitHub
3. On the Keys page → **"Create API Key"**
4. Name it: `inner-citadel` → **"Submit"**
5. Copy the key (looks like `gsk_XXXXXXXXXXXXXXXXXXXX`)

```
Paste into .env:
GROQ_API_KEY=gsk_XXXXXXXXXXXXXXXXXXXX
```

**Free limit:** 14,400 requests/day. One video = 1 request. You can make 14,400 videos/day free.

---

## Step 2 — OPENROUTER API KEY 🔄 (Backup LLM)

1. Go to → **https://openrouter.ai/**
2. **"Sign In"** → Google login
3. Profile icon → **"Keys"** → **"Create Key"**
4. Name: `inner-citadel` → **"Create"**
5. Copy the key (looks like `sk-or-v1-XXXXXXXX`)

```
Paste into .env:
OPENROUTER_API_KEY=sk-or-v1-XXXXXXXX
```

**Free models available:** `meta-llama/llama-3.1-8b-instruct:free`, `mistralai/mistral-7b-instruct:free`

---

## Step 3 — PEXELS API KEY 🎬 (Stock Videos — Primary)

1. Go to → **https://www.pexels.com/api/**
2. **"Get Started"** (top right)
3. Create account → verify email
4. Back at api page → fill form:
   - App Name: `Inner Citadel`
   - URL: `http://localhost:3000`
   - Use: `Personal / Non-commercial`
5. **"Request Access"** → key appears instantly

```
Paste into .env:
PEXELS_API_KEY=YOUR_KEY_HERE
```

---

## Step 4 — PIXABAY API KEY 🎞️ (Stock Videos — Fallback)

1. Go to → **https://pixabay.com/accounts/register/**
2. Register → verify email
3. Go to → **https://pixabay.com/api/docs/**
4. Your key is shown at the top of the page

```
Paste into .env:
PIXABAY_API_KEY=12345678-abcdefghij
```

---

## Step 5 — GEMINI API KEY 🤖 (Optional — Last Resort LLM)

1. Go to → **https://aistudio.google.com/apikey**
2. Sign in with Google
3. **"Create API key"** → **"Create API key in new project"**

```
Paste into .env:
GEMINI_API_KEY=AIzaSyXXXXXXXXX
```

---

## Step 6 — NGROK AUTH TOKEN 🌐 (Connects Your PC to Vercel)

> This is how Vercel (cloud) talks to your backend (your PC).
> Ngrok creates a secure tunnel: `https://random.ngrok-free.app → localhost:8000`

1. Go to → **https://ngrok.com/**
2. Click **"Sign Up"** → GitHub login (1 click, instant)
3. After login → **https://dashboard.ngrok.com/get-started/your-authtoken**
4. Your token is shown there — click **"Copy"**
5. Looks like: `2abc123_XXXXXXXXXXXXXXXXXXXXXXXXXXX`

```
Paste into .env:
NGROK_AUTHTOKEN=2abc123_XXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Free tier:** 1 tunnel, stable URL per session (changes on restart unless you have paid plan).
**Important:** With the auth token, your URL is stable within a session (hours).

---

## Your Final .env File

Create at: `c:\projects\YOUTUBE_WEBAPP\.env`

```env
# LLM APIs
GROQ_API_KEY=gsk_PASTE_HERE
OPENROUTER_API_KEY=sk-or-v1-PASTE_HERE
GEMINI_API_KEY=AIzaSy_PASTE_HERE

# Stock Video
PEXELS_API_KEY=PASTE_HERE
PIXABAY_API_KEY=PASTE_HERE

# Ngrok tunnel (connects Vercel to your PC)
NGROK_AUTHTOKEN=PASTE_HERE

# Auto-filled by ngrok_tunnel.py — leave as localhost for now
BACKEND_URL=http://localhost:8000

# Storage
STORAGE_TYPE=local
EXPORTS_DIR=./exports

# LLM Models
GROQ_MODEL=llama-3.1-8b-instant
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
GEMINI_MODEL=gemini-1.5-flash

# Settings
DEFAULT_ASPECT_RATIO=9:16
DEFAULT_FPS=60
APP_ENV=development
```

---

## Install & Launch (3 Steps)

### Step A — Install FFmpeg (Required for video rendering)
```powershell
winget install ffmpeg
# Restart terminal after installing
```

### Step B — Install Python dependencies
```powershell
cd c:\projects\YOUTUBE_WEBAPP\backend
pip install -r requirements.txt
# Takes 5-15 minutes (downloads AI models)
```

### Step C — Double-click to start everything
```
c:\projects\YOUTUBE_WEBAPP\start_dev.bat
```
Opens 3 windows automatically:
- **Window 1:** FastAPI backend (localhost:8000)
- **Window 2:** Ngrok tunnel (shows your public URL)
- **Window 3:** Next.js frontend (localhost:3000)

→ Open **http://localhost:3000** and generate your first video!

---

## Deploy Frontend to Vercel (Free, 5 minutes)

### Step 1: Push to GitHub
```powershell
cd c:\projects\YOUTUBE_WEBAPP
git init
git add .
git commit -m "Initial commit"
# Create repo on github.com first, then:
git remote add origin https://github.com/YOU/inner-citadel.git
git push -u origin main
```

### Step 2: Deploy to Vercel
1. Go to → **https://vercel.com/new**
2. Click **"Add New Project"** → Import your GitHub repo
3. Settings:
   - **Root Directory**: `frontend`
   - **Framework**: Next.js (auto-detected)
4. **Environment Variables** → Add:
   ```
   Name:  NEXT_PUBLIC_BACKEND_URL
   Value: (paste your Ngrok URL from the Ngrok terminal window)
          e.g. https://abc123.ngrok-free.app
   ```
5. Click **"Deploy"** → Done in ~2 minutes
6. Your app URL: `https://inner-citadel-xxx.vercel.app`

### Step 3: Every time you start your PC
1. Double-click `start_dev.bat`
2. Copy the Ngrok URL from the Ngrok terminal
3. Update `NEXT_PUBLIC_BACKEND_URL` in Vercel dashboard if it changed

> 💡 **Tip:** Get Ngrok's static domain (free): https://dashboard.ngrok.com/cloud-edge/domains
> This gives you a permanent URL that never changes!

---

## System Requirements

| Component | Your PC | Required |
|---|---|---|
| RAM | 30 GB | ≥ 4 GB |
| GPU | Intel (integrated) | None needed ✅ |
| CPU | Intel (any) | Any ✅ |
| Storage | — | ≥ 5 GB free |
| Internet | — | For API calls |
| Python | Install if missing | ≥ 3.10 |
| Node.js | Install if missing | ≥ 18 |

**Your 30GB RAM breakdown during video generation:**
- WhisperX (whisper-base): ~150 MB
- Kokoro-82M TTS: ~300 MB
- SentenceTransformers: ~100 MB
- MoviePy + FFmpeg: ~500 MB
- **Total: ~1.1 GB** (out of your 30 GB) ✅ Excellent

---

## FAQ

**Q: Do I need a GPU?**
> Absolutely not. Your Intel CPU + 30GB RAM is perfect for this pipeline.

**Q: What is Groq vs Grok?**
> **Groq** (groq.com) = Fast AI inference engine. We use this. ✅
> **Grok** (by xAI/Elon Musk) = Different AI assistant. We do NOT use this. ❌

**Q: How long does one video take?**
> On your Intel CPU: ~3-8 minutes per video (mostly WhisperX + FFmpeg rendering)

**Q: Will it work without WhisperX?**
> Yes! The alignment engine has a fallback that calculates word timing proportionally.
> Just don't install WhisperX and it auto-uses the faster fallback.

**Q: Ngrok URL changes every restart. Problem?**
> For local dev: No — just update `frontend/.env.local`
> For Vercel: Get Ngrok's free static domain from dashboard.ngrok.com/cloud-edge/domains
