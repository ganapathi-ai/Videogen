# 🚀 Deploy to Render.com (Free) — Step-by-Step Guide

> Render.com hosts the **FastAPI API layer** for free.
> Your **local PC** runs the Celery ML worker (WhisperX, Kokoro, MoviePy).

---

## Why This Split?

| Component | Where | Why |
|---|---|---|
| FastAPI API | Render.com (free) | Only needs 512MB — handles HTTP + SSE |
| Celery Worker | Your PC | Needs 2-4GB RAM for ML models |
| Next.js UI | Vercel (free) | Static + serverless frontend |
| Redis Queue | Upstash (free) | Cloud Redis, connects both |

---

## Step 1: Push Code to GitHub

```powershell
cd c:\projects\YOUTUBE_WEBAPP
git init
git add .
git commit -m "Initial commit: Inner Citadel pipeline"

# Create repo on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/inner-citadel.git
git push -u origin main
```

---

## Step 2: Deploy FastAPI to Render.com

1. Go to: **https://render.com/** → Sign up free (GitHub login)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo: `inner-citadel`
4. Configure:
   - **Name**: `inner-citadel-api`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install fastapi uvicorn[standard] celery redis python-dotenv loguru httpx pysubs2 pydantic tenacity google-generativeai`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
5. Click **"Advanced"** → **"Add Environment Variable"** for each:
   ```
   GROQ_API_KEY          = your-groq-key
   OPENROUTER_API_KEY    = your-openrouter-key
   GEMINI_API_KEY        = your-gemini-key
   PEXELS_API_KEY        = your-pexels-key
   PIXABAY_API_KEY       = your-pixabay-key
   CELERY_BROKER_URL     = rediss://default:PASSWORD@host.upstash.io:6379
   CELERY_RESULT_BACKEND = db+sqlite:///results.db
   STORAGE_TYPE          = local
   EXPORTS_DIR           = ./exports
   GROQ_MODEL            = llama-3.1-8b-instant
   OPENROUTER_MODEL      = meta-llama/llama-3.1-8b-instruct:free
   ```
6. Click **"Create Web Service"**
7. Wait 2-3 minutes for first deploy
8. Your API URL will be: `https://inner-citadel-api.onrender.com`

> ⚠️ **Render Free Tier Warning**: Service sleeps after 15 min inactivity.
> First request after sleep takes ~30 seconds (cold start).
> This is fine — the ML worker runs locally regardless.

---

## Step 3: Update Your Local .env

```env
# Point to Render for the API
BACKEND_URL=https://inner-citadel-api.onrender.com
```

---

## Step 4: Start Local Celery Worker

Your PC still runs the heavy ML work:
```powershell
cd c:\projects\YOUTUBE_WEBAPP\backend
celery -A tasks worker --loglevel=info
```

The worker connects to Upstash Redis and processes jobs dispatched by Render.

---

## Step 5: Deploy Frontend to Vercel

1. Go to: **https://vercel.com/new** → Import `inner-citadel` repo
2. Set **Root Directory**: `frontend`
3. Add environment variable:
   - `NEXT_PUBLIC_BACKEND_URL` = `https://inner-citadel-api.onrender.com`
4. Click **Deploy**
5. Your frontend URL: `https://inner-citadel.vercel.app`

---

## Final Architecture

```
User → vercel.app (Next.js)
         ↓ POST /api/generate
       onrender.com (FastAPI — 512MB, free)
         ↓ Celery task dispatch
       upstash.io (Redis queue — free)
         ↓ Job picked up
       YOUR PC (Celery Worker — full power)
         ↓ 9-step pipeline
       exports/ (local storage)
         ↓ Result URL
       onrender.com → vercel.app → User downloads video
```

---

## Cost Breakdown

| Service | Free Limit | Our Usage | Cost |
|---|---|---|---|
| Vercel | Unlimited | Frontend | $0 |
| Render | 750 hrs/month | API layer | $0 |
| Upstash Redis | 10,000 cmd/day | ~50/video | $0 |
| Groq | 14,400 req/day | 1/video | $0 |
| OpenRouter | Unlimited (free models) | Fallback | $0 |
| Pexels | Unlimited | Video clips | $0 |
| Pixabay | Unlimited | Video clips | $0 |
| **TOTAL** | | | **$0** |
