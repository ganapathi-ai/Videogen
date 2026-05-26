"""
VOXLORE STUDIO — FastAPI Backend (CPU-Only, No Celery/Redis)
Multi-channel AI video generation: Stoic philosophy + Tech concept explainer.
Progress tracked in-memory. SSE streams live updates to the frontend.

Channels:
  The Inner Citadel  (stoic)   — philosophy, dark ambient BGM, gold theme
  neuralbaba_empire  (tech)    — concept explainer, electronic BGM, cyan theme

Works perfectly on Intel CPU with 30GB RAM.
"""

import asyncio
import uuid
import os
from typing import Dict, Any
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from loguru import logger
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# ── In-memory job store (no Redis needed) ────────────────────
# { job_id: { "state": str, "step": int, "total": int,
#             "status": str, "result": dict | None, "error": str | None } }
JOBS: Dict[str, Dict[str, Any]] = {}

EXPORTS_DIR = Path(os.getenv("EXPORTS_DIR", "./exports"))
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
app = FastAPI(
    title="Voxlore Studio API",
    description="VOXLORE STUDIO — Multi-channel AI Video Generator (Stoic + Tech)",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated videos directly
app.mount("/exports", StaticFiles(directory=str(EXPORTS_DIR)), name="exports")

# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class GenerateRequest(BaseModel):
    topic: str
    length: str = "short"          # short|medium|long_3|long_5|long_7|long_11
    aspect_ratio: str = "9:16"     # "9:16" | "16:9" | "1:1"
    voice: str = "gb_ryan"         # Voice ID from /api/voices
    fps: int = 30                  # 30fps — smooth on CPU, standard for YouTube
    channel: str = "stoic"         # Any channel_id defined in channel_config.py

# ─────────────────────────────────────────────
# Progress Helper
# ─────────────────────────────────────────────

def set_progress(job_id: str, step: int, status: str, total: int = 9):
    JOBS[job_id].update({"state": "running", "step": step,
                          "total": total, "status": status})
    logger.info(f"[{job_id[:8]}] Step {step}/{total}: {status}")

# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.get("/")
async def root():
    from channels.channel_config import get_all_channels
    channel_names = [ch["id"] for ch in get_all_channels()]
    return {
        "status":   "ok",
        "service":  "VOXLORE STUDIO",
        "version":  "3.0.0",
        "channels": channel_names,
        "mode":     "CPU-only, no Redis/Celery"
    }


@app.get("/api/channels")
async def get_channels():
    """Returns all configured channels for the frontend."""
    from channels.channel_config import get_all_channels
    return {"channels": get_all_channels()}


@app.post("/api/generate")
async def generate_video(req: GenerateRequest, background_tasks: BackgroundTasks):
    """Queues a video generation job. Returns job_id immediately."""
    if not req.topic or len(req.topic.strip()) < 3:
        raise HTTPException(status_code=400, detail="Topic must be at least 3 characters.")

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "state": "queued", "step": 0, "total": 9,
        "status": "Queued — starting pipeline...",
        "result": None, "error": None,
    }

    logger.info(f"[{job_id[:8]}] New job: topic='{req.topic}' length={req.length}")

    # Run pipeline in background (non-blocking)
    background_tasks.add_task(
        run_pipeline, job_id, req.topic.strip(),
        req.length, req.aspect_ratio, req.voice, req.fps,
        req.channel
    )

    return {"job_id": job_id, "status": "queued",
            "stream_url": f"/api/stream-progress/{job_id}"}


@app.get("/api/stream-progress/{job_id}")
async def stream_progress(request: Request, job_id: str):
    """
    SSE endpoint — streams live step-by-step progress to Next.js frontend.
    No Redis/Celery needed — reads from in-memory JOBS dict.
    """
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        import json
        timeout = 0
        max_wait = 900  # 15 minutes max

        while timeout < max_wait:
            if await request.is_disconnected():
                break

            job = JOBS.get(job_id, {})
            state = job.get("state", "queued")

            payload = {
                "state":  state,
                "step":   job.get("step", 0),
                "total":  job.get("total", 9),
                "status": job.get("status", ""),
            }

            if state == "done":
                result = job.get("result", {})
                payload.update(result)
                yield f"data: {json.dumps(payload)}\n\n"
                break
            elif state == "error":
                payload["error"] = job.get("error", "Unknown error")
                yield f"data: {json.dumps(payload)}\n\n"
                break
            else:
                yield f"data: {json.dumps(payload)}\n\n"

            await asyncio.sleep(1)
            timeout += 1

        yield f"data: {{\"state\": \"closed\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Polling fallback (if SSE not supported)."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/result/{job_id}")
async def get_result(job_id: str):
    """Returns final video/captions URLs when done."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["state"] != "done":
        raise HTTPException(status_code=425, detail=f"Not complete. State: {job['state']}")
    return job["result"]


@app.get("/api/voices")
async def list_voices():
    """Returns all available TTS voices for the frontend."""
    from audio.tts_engine import get_voice_list
    return {"voices": get_voice_list()}


@app.get("/api/history")
async def get_history():
    """Returns per-channel history stats. Auto-discovers all channels via subfolder scan."""
    from history.history_engine import get_all_history_stats, HISTORY_FILES
    # Also ensure known channels appear even if empty
    stats = get_all_history_stats()
    for ch_id in HISTORY_FILES:
        if ch_id not in stats:
            from history.history_engine import HistoryEngine
            stats[ch_id] = HistoryEngine(channel_id=ch_id).get_stats()
    return {
        "channels": {ch: {"stats": s, "past_topics": []} for ch, s in stats.items()},
        "note": "Each channel's history is completely isolated in its own subfolder"
    }



@app.get("/api/health")
async def health():
    active = sum(1 for j in JOBS.values() if j["state"] == "running")
    return {"status": "ok", "active_jobs": active,
            "total_jobs": len(JOBS), "mode": "CPU"}


class PostSuggestionsRequest(BaseModel):
    title: str
    topic: str
    channel: str = "stoic"
    duration: float = 60.0          # seconds
    script_excerpt: str = ""        # first ~300 chars of script for context


@app.post("/api/post-suggestions")
async def generate_post_suggestions(req: PostSuggestionsRequest):
    """
    Generate SEO-optimized post copy for every generated video:
      - YouTube title (3 variants, click-optimised)
      - YouTube description (500 chars, SEO keywords, timestamps, CTA)
      - Instagram caption (hashtags, emojis, CTA)
      - Twitter/X thread (3-tweet thread)
      - 30 SEO hashtags (mixed broad + niche)
      - Thumbnail prompt (Midjourney/DALL-E style) — always included
    """
    import google.generativeai as genai

    genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

    is_long    = req.duration >= 120
    video_type = "long-form YouTube video" if is_long else "YouTube Short / Reel"
    channel_label = "Stoic philosophy wisdom" if req.channel == "stoic" else "tech/AI concept explainer"

    prompt = f"""You are a top-tier YouTube SEO strategist and social media copywriter for a {channel_label} channel.

Video details:
  Title: {req.title}
  Topic: {req.topic}
  Type: {video_type} ({req.duration:.0f}s)
  Channel style: {channel_label}
  {"Script excerpt: " + req.script_excerpt[:300] if req.script_excerpt else ""}

Generate ALL of the following as a single valid JSON object (no markdown, no code fences):

{{
  "youtube_titles": ["<title 1, curiosity hook>", "<title 2, benefit-driven>", "<title 3, question-based>"],
  "youtube_description": "<500-char SEO description with keywords, 2 CTAs (Subscribe + Comment), 3 relevant timestamps if long video>",
  "instagram_caption": "<punchy 3-line caption with emojis, hook, value, CTA, 5 hashtags inline>",
  "twitter_thread": ["<tweet 1 - hook, max 280 chars>", "<tweet 2 - insight>", "<tweet 3 - CTA + link>"],
  "hashtags": ["<30 SEO hashtags — mix of broad, niche, channel-specific, no # prefix>"],
  "thumbnail_prompt": "<Midjourney-style prompt for a high-CTR YouTube thumbnail: bold text overlay, dramatic lighting, specific visual elements, style keywords, aspect ratio 16:9>"
}}

Rules:
- YouTube title: max 60 chars, power word at start, number or question if natural
- Description: first 2 lines must hook without "click more", natural keyword density
- Instagram: Reels-style, 3 short punchy lines then hashtags
- Hashtags: 10 broad (1M+ posts) + 10 medium + 10 niche/channel-specific
- Thumbnail: describe the EXACT visual scene, not abstract. Include text overlay words.
- Return ONLY the JSON. No other text."""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        resp  = model.generate_content(prompt)
        raw   = resp.text.strip()
        # Strip markdown fences if model returns them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        import json as _json
        data = _json.loads(raw.strip())
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"[PostSuggestions] Error: {e}")
        # Return graceful fallback
        return {
            "success": False,
            "error": str(e),
            "data": {
                "youtube_titles": [req.title],
                "youtube_description": f"Watch this video about {req.topic}. Like and Subscribe for more!",
                "instagram_caption": f"New video: {req.topic} 🔥\nWatch now!\n#youtube #content",
                "twitter_thread": [f"Just posted: {req.title}", f"Topic: {req.topic}", "Watch now! 🔗"],
                "hashtags": ["youtube", "contentcreator", "viral", req.topic.lower().replace(" ", "")],
                "thumbnail_prompt": f"YouTube thumbnail for '{req.topic}', bold text overlay, dramatic lighting, 16:9"
            }
        }


# ─────────────────────────────────────────────
# Pipeline Runner (runs in background)
# ─────────────────────────────────────────────

async def run_pipeline(job_id: str, topic: str, length: str,
                        aspect_ratio: str, voice: str, fps: int,
                        channel: str = "stoic"):
    """
    Async wrapper — offloads blocking ML work to thread pool
    so the FastAPI event loop stays responsive.
    """
    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        try:
            await loop.run_in_executor(
                pool,
                lambda: _pipeline_sync(job_id, topic, length, aspect_ratio, voice, fps, channel)
            )
        except Exception as e:
            logger.error(f"[{job_id[:8]}] Pipeline error: {e}")
            JOBS[job_id].update({"state": "error", "error": str(e)})


def _pipeline_sync(job_id: str, topic: str, length: str,
                   aspect_ratio: str, voice: str, fps: int,
                   channel: str = "stoic"):
    """Synchronous pipeline — all 9 steps, CPU mode."""
    import json, sys
    sys.path.insert(0, str(Path(__file__).parent))

    # Load channel config for watermark + metadata
    from channels.channel_config import get_channel
    channel_cfg  = get_channel(channel)
    watermark    = channel_cfg.get("watermark", "NeuralBaba Empire")

    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    job_dir = EXPORTS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ── Step 1: History Check + Script ──────────────────
        from generator.script_engine import ScriptEngine, LENGTH_CONFIG
        from history.history_engine import HistoryEngine

        history = HistoryEngine(channel_id=channel)  # Channel-isolated — no mixing!
        cfg = LENGTH_CONFIG.get(length, LENGTH_CONFIG["short"])
        total_steps = 11 if cfg["type"] == "long" else 9
        JOBS[job_id]["total"] = total_steps

        # ── ASPECT RATIO ENFORCEMENT ─────────────────────────────────
        # Long-form YouTube MUST be 16:9 (horizontal) regardless of frontend state
        # Shorts/Reels default to 9:16 (vertical)
        if cfg["type"] == "long":
            aspect_ratio = "16:9"
            logger.info(f"[{job_id[:8]}] Long-form: forcing aspect_ratio=16:9")
        # For short-form, use whatever the user selected (9:16, 16:9, 1:1)

        set_progress(job_id, 1, "📚 Checking history (no repeat content)...", total_steps)
        try:
            history.check_topic(topic)
        except ValueError as e:
            logger.warning(str(e))
            # Not a hard failure — just warn and continue (user chose this topic)
            logger.warning("[History] Proceeding despite similarity — user chose topic explicitly")

        # Collect past beats to guide LLM away from repetition
        past_entries = history._load()
        used_beats = []
        for entry in past_entries[-20:]:   # Last 20 videos only
            used_beats.extend(entry.get("beats", []))
        used_beats = used_beats[-80:]       # Cap to last 80 beats

        set_progress(job_id, 1, f"✍️ Generating script (AI) for {channel_cfg['name']}...", total_steps)
        script = ScriptEngine().generate_script(
            topic=topic, length=length, used_beats=used_beats, channel_id=channel
        )

        # Filter duplicate beats from this script
        script["beats"] = history.filter_beats(script["beats"])
        (job_dir / "script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

        # ── Step 2: TTS ──────────────────────────────────────
        set_progress(job_id, 2, "🎙️ Synthesizing deep voice (edge-tts + bass chain)...", total_steps)
        from audio.tts_engine import TTSEngine
        audio_path = str(job_dir / "audio.wav")
        TTSEngine(voice=voice, channel_id=channel).synthesize(script_data=script, output_path=audio_path)

        # ── Step 3: Alignment ────────────────────────────────
        set_progress(job_id, 3, "🔬 Aligning words (WhisperX CPU)...", total_steps)
        from alignment.align_engine import AlignmentEngine
        word_timeline = AlignmentEngine().generate_word_timestamps(audio_path=audio_path)

        # ── Step 4: Timeline ─────────────────────────────────
        set_progress(job_id, 4, "📐 Building master timeline JSON...", total_steps)
        from timeline.timeline_engine import TimelineEngine
        timeline = TimelineEngine().build(script_data=script, word_timeline=word_timeline)
        (job_dir / "timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")

        # ── Step 5: Media ────────────────────────────────────
        set_progress(job_id, 5, "🎬 Fetching cinematic footage (Pexels/Pixabay)...", total_steps)
        from embeddings.faiss_engine import FAISSEngine
        from media.media_engine import FreeMediaEngine
        faiss = FAISSEngine()
        media_engine = FreeMediaEngine(
            pexels_key=os.getenv("PEXELS_API_KEY", ""),
            pixabay_key=os.getenv("PIXABAY_API_KEY", ""),
            unsplash_key=os.getenv("UNSPLASH_ACCESS_KEY", ""),
            faiss_engine=faiss,
            channel_id=channel,
        )
        clips = []
        for seg in timeline["segments"]:
            dur = seg["audio_end"] - seg["audio_start"]
            path = media_engine.fetch_best_clip(
                script_text=seg["text"],
                queries=seg.get("visual_keywords", [seg["text"]]),
                aspect_ratio=aspect_ratio,
                job_dir=str(job_dir),
                segment_id=seg["id"],
            )
            clips.append({"path": path, "duration": dur, "segment": seg})

        # ── Step 6: Video ────────────────────────────────────
        set_progress(job_id, 6, "🎞️ Compositing video (FFmpeg Ken Burns)...", total_steps)
        from video.video_engine import VideoEngine
        raw_video = str(job_dir / "raw_video.mp4")
        VideoEngine(aspect_ratio=aspect_ratio, fps=fps).compose(
            clips=clips, output_path=raw_video, timeline=timeline
        )

        # ── Step 7: Captions ─────────────────────────────────
        set_progress(job_id, 7, "💬 Generating karaoke subtitles...", total_steps)
        from captions.caption_engine import CaptionEngine
        w, h = {"9:16":(1080,1920),"16:9":(1920,1080),"1:1":(1080,1080)}.get(aspect_ratio,(1080,1920))
        captions_path = str(job_dir / "captions.ass")
        CaptionEngine(resolution=(w, h), fps=fps).build_ass_subtitles(
            timeline=timeline, output_path=captions_path
        )

        # ── Step 8: BGM + Audio Mix ──────────────────────────────
        set_progress(job_id, 8, f"🎵 Fetching {channel_cfg['name']} BGM + professional mix...", total_steps)
        from audio.bgm_engine import BGMEngine
        from audio.audio_mixer import AudioMixer

        # Get dominant emotions from timeline for BGM selection
        emotions = [seg.get("emotion", "deep") for seg in timeline.get("segments", [])]

        # Channel-specific BGM: stoic gets dark ambient, tech gets electronic
        bgm_engine = BGMEngine(
            api_key=os.getenv("FREESOUND_API_KEY", ""),
            channel_id=channel,
        )
        bgm_path   = bgm_engine.get_track(emotions, timeline.get("duration", 30.0))

        mixed_audio = str(job_dir / "audio_mixed.wav")
        AudioMixer().mix(
            voice_path=audio_path,
            bgm_path=bgm_path,
            timeline=timeline,
            output_path=mixed_audio,
        )

        # ── Step 9: Final Render ──────────────────────────────────────
        set_progress(job_id, 9, "🚀 Final FFmpeg render + quality validation...", total_steps)
        final_video = str(job_dir / "final_video.mp4")

        # Use video duration from timeline for precise render length
        video_duration = timeline.get("duration", 0.0)
        _ffmpeg_render(
            raw_video, mixed_audio, captions_path, final_video,
            fps=fps, duration=video_duration, watermark=watermark
        )

        # Thumbnail
        thumb = str(job_dir / "thumbnail.jpg")
        _extract_thumb(final_video, thumb)

        # Validation
        from validator.validator import Validator
        report = Validator().validate(
            video_path=final_video, audio_path=audio_path,
            captions_path=captions_path, timeline=timeline
        )


        # Build script excerpt for post-suggestions (first ~400 chars of beat texts)
        beats = script.get("beats", [])
        script_excerpt = " ".join(b.get("text", "") for b in beats[:5])[:400]

        result = {
            "job_id":         job_id,
            "title":          script.get("title", topic),
            "topic":          topic,
            "channel":        channel,
            "duration":       timeline.get("duration", 0),
            "script_excerpt": script_excerpt,
            "video_url":      f"{backend_url}/exports/{job_id}/final_video.mp4",
            "captions_url":   f"{backend_url}/exports/{job_id}/captions.ass",
            "timeline_url":   f"{backend_url}/exports/{job_id}/timeline.json",
            "thumbnail_url":  f"{backend_url}/exports/{job_id}/thumbnail.jpg",
            "validation":     report,
        }

        # ── Save to history (after success) ──────────────────
        try:
            history.save(script, length=length)   # Saves to channel-specific file
        except Exception as hist_e:
            logger.warning(f"[History] Save failed (non-fatal): {hist_e}")

        JOBS[job_id].update({"state": "done", "step": total_steps,
                              "status": "✅ Complete!", "result": result})
        logger.info(f"[{job_id[:8]}] Done -> {result['video_url']}") 

    except Exception as e:
        logger.error(f"[{job_id[:8]}] ❌ Failed: {e}")
        JOBS[job_id].update({"state": "error", "error": str(e),
                              "status": f"Failed: {e}"})
        raise



def _ffmpeg_render(video: str, audio: str, captions: str, out: str,
                   fps: int = 30, duration: float = 0.0,
                   watermark: str = ""):
    """
    Final FFmpeg render: mux video + mixed audio + captions + watermark.
    """
    import subprocess

    # ── Watermark drawtext filter ──────────────────────────────────────────────
    # CRITICAL: Use hex RGBA notation — 'color@alpha' fails on Windows FFmpeg.
    # white 35% opacity = 0xFFFFFF59  (0x59 = 89 = 35% of 255)
    # black 30% opacity = 0x0000004D  (0x4D = 77 = 30% of 255)
    #
    # IMPORTANT: Do NOT use ih*0.018 expression in fontsize —
    # this fails with 'Undefined constant' when chained after ass= filter (FFmpeg 8.x Windows).
    # Instead compute pixel size from the known video resolution.
    watermark_text = (watermark or "").replace("'", "\\'").replace(":", "\\:")

    # Detect video height from the raw video file to set correct pixel fontsize
    _h = 1920  # default: vertical 9:16
    try:
        import json as _json
        _p = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_streams", "-select_streams", "v",
             "-print_format", "json", video],
            capture_output=True, text=True, timeout=8
        )
        _streams = _json.loads(_p.stdout).get("streams", [])
        if _streams:
            _h = _streams[0].get("height", 1920)
    except Exception:
        pass
    _wm_fontsize = max(18, int(_h * 0.018))  # 1.8% of height, min 18px

    if watermark_text:
        wm_filter = (
            f"drawtext="
            f"text='{watermark_text}':"
            f"fontsize={_wm_fontsize}:"
            f"fontcolor=0xFFFFFF59:"           # white, 35% opacity — HEX RGBA (Windows safe)
            f"x=(w-text_w)/2:"                # horizontally centered
            f"y=h-80:"                         # 80px from bottom
            f"shadowx=1:shadowy=1:"
            f"shadowcolor=0x0000004D:"         # black shadow, 30% opacity — HEX RGBA
            f"font=Arial"
        )
    else:
        wm_filter = None

    # ── ASS path fix for Windows FFmpeg ─────────────────────────────────────
    # PROBLEM: FFmpeg's ass= filter cannot handle Windows absolute paths (C:\...)
    # through any escaping strategy (forward-slash, \\:, :: — all fail with exit 4294967274).
    # SOLUTION: Copy the ASS file to a relative path in CWD (no drive letter, no colon).
    # FFmpeg finds it as "tmp_captions_XXXX.ass" with zero path issues.
    import shutil, uuid as _uuid
    ass_rel = None
    if captions and os.path.exists(captions):
        ass_rel = f"tmp_captions_{_uuid.uuid4().hex[:8]}.ass"
        shutil.copy2(captions, ass_rel)   # copy to CWD (backend/)
        ass_path = ass_rel                # relative path — no escaping needed
    else:
        ass_path = None

    timeout_s = max(300, int(duration * 2.5) + 120) if duration > 0 else 600
    dur_flags = ["-t", f"{duration:.3f}"] if duration > 0 else []

    # ── Watermark drawtext filter ─────────────────────────────────────────


    # Base FFmpeg args (no filters yet)
    base_args = [
        "ffmpeg",
        "-i", video,
        "-i", audio,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        *dur_flags,
        out, "-y",
    ]

    def run_with_vf(vf: str) -> int:
        """Run ffmpeg with a -vf filter. Returns returncode."""
        cmd = [
            "ffmpeg", "-i", video, "-i", audio,
            "-vf", vf,
            # Video: H.264 Main Profile — supported by ALL Windows players including WMP
            # 'high' profile requires DXVA hardware decoder; WMP falls back to 'unsupported'
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-profile:v", "main", "-level", "4.0",
            # Audio: FORCE stereo 44100Hz — Windows Media Player rejects mono AAC in MP4
            # edge-tts outputs 24kHz mono → must upsample to 44100Hz stereo for WMP
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart",
            *dur_flags, out, "-y",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        if r.returncode != 0:
            logger.warning(f"[Render] vf='{vf[:60]}' failed: {r.stderr[-300:]}")
        return r.returncode

    def run_bare() -> int:
        """Run ffmpeg with NO video filter (bare mux). Always works."""
        cmd = [
            "ffmpeg", "-i", video, "-i", audio,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-profile:v", "main", "-level", "4.0",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart",
            *dur_flags, out, "-y",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        return r.returncode

    try:
        # ── ATTEMPT 1: captions + watermark (full quality) ───────────────────
        vf_parts = []
        if ass_path:
            vf_parts.append(f"ass='{ass_path}'")
        if wm_filter:
            vf_parts.append(wm_filter)

        if vf_parts:
            vf = ",".join(vf_parts)
            rc = run_with_vf(vf)
            if rc == 0:
                logger.info("[Render] ✅ Full render (captions + watermark)")
                return

        # ── ATTEMPT 2: watermark only (ASS failed) ───────────────────────────
        if wm_filter:
            rc = run_with_vf(wm_filter)
            if rc == 0:
                logger.info("[Render] ✅ Watermark-only render (captions failed)")
                return

        # ── ATTEMPT 3: bare mux — always produces a video ────────────────────
        logger.warning("[Render] All filters failed — bare mux (no captions, no watermark)")
        rc = run_bare()
        if rc != 0:
            raise RuntimeError(
                "[Render] All 3 fallbacks failed — FFmpeg cannot mux video+audio. "
                "Check that raw_video.mp4 and audio_mixed.wav exist."
            )
        logger.info("[Render] ✅ Bare mux fallback succeeded")

    finally:
        # Clean up temp ASS file copied to CWD for Windows path workaround
        if ass_rel and os.path.exists(ass_rel):
            try:
                os.unlink(ass_rel)
            except Exception:
                pass



def _extract_thumb(video: str, out: str):
    """Extracts thumbnail at 20% through video (better than fixed 5s for long videos)."""
    import subprocess

    try:
        probe = subprocess.run([
            "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video
        ], capture_output=True, text=True, timeout=10)
        import json
        dur      = float(json.loads(probe.stdout).get("format", {}).get("duration", 30.0))
        thumb_t  = max(3.0, dur * 0.20)  # 20% mark, minimum 3s
    except Exception:
        thumb_t  = 5.0

    subprocess.run([
        "ffmpeg", "-i", video,
        "-ss", f"{thumb_t:.1f}", "-vframes", "1",
        "-q:v", "2", out, "-y"
    ], capture_output=True, check=False, timeout=30)

