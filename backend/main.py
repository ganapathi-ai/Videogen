"""
THE INNER CITADEL — FastAPI Backend (CPU-Only, No Celery/Redis)
Uses FastAPI BackgroundTasks — zero external dependencies for the queue.
Progress tracked in-memory. SSE streams live updates to the frontend.

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
    title="Inner Citadel API",
    description="Autonomous Stoic Video Pipeline — CPU Mode",
    version="2.0.0",
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
    channel: str = "stoic"         # "stoic" | "tech" (NeuralBaba Empire channels)

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
    return {"status": "ok", "service": "NeuralBaba Empire API", "version": "3.0.0",
            "channels": ["stoic", "tech"], "mode": "CPU-only, no Redis/Celery"}


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
    """Returns per-channel history stats + past topics. No channel mixing."""
    from history.history_engine import HistoryEngine, HISTORY_FILES
    result = {}
    for ch_id in HISTORY_FILES:
        h = HistoryEngine(channel_id=ch_id)
        result[ch_id] = {
            "stats":       h.get_stats(),
            "past_topics": h.get_all_topics(),
        }
    return {"channels": result, "note": "Each channel's history is completely isolated"}



@app.get("/api/health")
async def health():
    active = sum(1 for j in JOBS.values() if j["state"] == "running")
    return {"status": "ok", "active_jobs": active,
            "total_jobs": len(JOBS), "mode": "CPU"}


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
        TTSEngine(voice=voice).synthesize(script_data=script, output_path=audio_path)

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
        CaptionEngine(resolution=(w, h)).build_ass_subtitles(
            timeline=timeline, output_path=captions_path
        )

        # ── Step 8: BGM + Audio Mix ──────────────────────────────
        set_progress(job_id, 8, "🎵 Fetching Stoic BGM + professional mix...", total_steps)
        from audio.bgm_engine import BGMEngine
        from audio.audio_mixer import AudioMixer

        # Get dominant emotions from timeline for BGM selection
        emotions = [seg.get("emotion", "deep") for seg in timeline.get("segments", [])]

        bgm_engine = BGMEngine(api_key=os.getenv("FREESOUND_API_KEY", ""))
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

        result = {
            "job_id":       job_id,
            "title":        script.get("title", topic),
            "duration":     timeline.get("duration", 0),
            "video_url":    f"{backend_url}/exports/{job_id}/final_video.mp4",
            "captions_url": f"{backend_url}/exports/{job_id}/captions.ass",
            "timeline_url": f"{backend_url}/exports/{job_id}/timeline.json",
            "thumbnail_url":f"{backend_url}/exports/{job_id}/thumbnail.jpg",
            "validation":   report,
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

    Watermark: Professional transparent text, bottom-center, 35% opacity.
    Research basis: ByteByteGo, 3Blue1Brown, NetworkChuck style watermarks.
      - Position: bottom-center (NOT bottom-right — captions are center, watermark above them)
      - Opacity:  0.35 (35%) — visible but never distracts from content
      - Color:    white with black 1px shadow — readable on any background
      - Size:     ~1.8% of frame height (scales automatically)
      - Timing:   always present throughout video

    Long-form fixes:
      - NO -shortest flag (was cutting audio prematurely)
      - -t duration: precise output length from timeline
      - Scaled timeout for 11+ min videos
    """
    import subprocess

    def _escape_ass_path(p: str) -> str:
        p = p.replace("\\", "/")
        if len(p) >= 2 and p[1] == ":":
            p = p[0] + "\\:" + p[2:]
        return p

    ass_path  = _escape_ass_path(captions)
    timeout_s = max(300, int(duration * 2.5) + 120) if duration > 0 else 600
    dur_flags = ["-t", f"{duration:.3f}"] if duration > 0 else []

    # ── Watermark drawtext filter ─────────────────────────────────
    # Professional transparent watermark:
    #   - Bottom-center, 80px above bottom (above captions, not covering them)
    #   - White text, 35% opacity, 1px black shadow for legibility
    #   - Font size = 1.8% of frame height (auto-scales for 9:16 vs 16:9)
    #   - No box/background — clean transparent overlay
    watermark_text = (watermark or "").replace("'", "\\'").replace(":", "\\:")
    if watermark_text:
        wm_filter = (
            f"drawtext="
            f"text='{watermark_text}':"
            f"fontsize=ih*0.018:"           # 1.8% of frame height (scales per aspect ratio)
            f"fontcolor=white@0.35:"        # White, 35% opacity — professional standard
            f"x=(w-text_w)/2:"             # Horizontally centered
            f"y=h-80:"                     # 80px from bottom (above caption area)
            f"shadowx=1:shadowy=1:"        # 1px shadow for legibility on bright frames
            f"shadowcolor=black@0.30:"     # Shadow at 30% opacity — subtle
            f"font=Arial"                  # Clean sans-serif (standard on all OS)
        )
    else:
        wm_filter = None

    # ── Build vf filter chain: captions [+ watermark] ────────────
    def build_vf(include_captions: bool) -> str:
        filters = []
        if include_captions:
            filters.append(f"ass='{ass_path}'")
        if wm_filter:
            filters.append(wm_filter)
        return ",".join(filters) if filters else "null"

    # Try with captions + watermark
    r = subprocess.run([
        "ffmpeg",
        "-i", video,
        "-i", audio,
        "-vf", build_vf(include_captions=True),
        "-c:v", "libx264", "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        *dur_flags,
        out, "-y"
    ], capture_output=True, text=True, timeout=timeout_s)

    if r.returncode != 0:
        logger.warning(f"Caption+watermark render failed: {r.stderr[-200:]} — trying no captions")
        # Fallback: watermark only (no captions)
        vf_fallback = build_vf(include_captions=False)
        subprocess.run([
            "ffmpeg",
            "-i", video,
            "-i", audio,
            "-vf", vf_fallback,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            *dur_flags,
            out, "-y"
        ], check=True, capture_output=True, timeout=timeout_s)


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

