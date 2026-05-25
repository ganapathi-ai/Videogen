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
    length: str = "short"          # "short" (35s) | "medium" (60s)
    aspect_ratio: str = "9:16"     # "9:16" | "16:9" | "1:1"
    voice: str = "af_bella"
    fps: int = 60

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
    return {"status": "ok", "service": "Inner Citadel API", "version": "2.0.0",
            "mode": "CPU-only, no Redis/Celery"}


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
        req.length, req.aspect_ratio, req.voice, req.fps
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


@app.get("/api/health")
async def health():
    active = sum(1 for j in JOBS.values() if j["state"] == "running")
    return {"status": "ok", "active_jobs": active,
            "total_jobs": len(JOBS), "mode": "CPU"}


# ─────────────────────────────────────────────
# Pipeline Runner (runs in background)
# ─────────────────────────────────────────────

async def run_pipeline(job_id: str, topic: str, length: str,
                        aspect_ratio: str, voice: str, fps: int):
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
                lambda: _pipeline_sync(job_id, topic, length, aspect_ratio, voice, fps)
            )
        except Exception as e:
            logger.error(f"[{job_id[:8]}] Pipeline error: {e}")
            JOBS[job_id].update({"state": "error", "error": str(e)})


def _pipeline_sync(job_id: str, topic: str, length: str,
                   aspect_ratio: str, voice: str, fps: int):
    """Synchronous pipeline — all 9 steps, CPU mode."""
    import json, sys
    sys.path.insert(0, str(Path(__file__).parent))

    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    job_dir = EXPORTS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ── Step 1: Script ───────────────────────────────────
        set_progress(job_id, 1, "✍️ Generating Stoic script (Groq AI)...")
        from generator.script_engine import ScriptEngine
        script = ScriptEngine().generate_script(topic=topic, length=length)
        (job_dir / "script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

        # ── Step 2: TTS ──────────────────────────────────────
        set_progress(job_id, 2, "🎙️ Synthesizing voice (Kokoro-82M, CPU)...")
        from audio.tts_engine import TTSEngine
        audio_path = str(job_dir / "audio.wav")
        TTSEngine(voice=voice).synthesize(script_data=script, output_path=audio_path)

        # ── Step 3: Alignment ────────────────────────────────
        set_progress(job_id, 3, "🔬 Aligning words (WhisperX CPU mode)...")
        from alignment.align_engine import AlignmentEngine
        word_timeline = AlignmentEngine().generate_word_timestamps(audio_path=audio_path)

        # ── Step 4: Timeline ─────────────────────────────────
        set_progress(job_id, 4, "📐 Building master timeline JSON...")
        from timeline.timeline_engine import TimelineEngine
        timeline = TimelineEngine().build(script_data=script, word_timeline=word_timeline)
        (job_dir / "timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")

        # ── Step 5: Media ────────────────────────────────────
        set_progress(job_id, 5, "🎬 Fetching cinematic footage (Pexels/Pixabay)...")
        from embeddings.faiss_engine import FAISSEngine
        from media.media_engine import FreeMediaEngine
        faiss = FAISSEngine()
        media_engine = FreeMediaEngine(
            pexels_key=os.getenv("PEXELS_API_KEY", ""),
            pixabay_key=os.getenv("PIXABAY_API_KEY", ""),
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
        set_progress(job_id, 6, "🎞️ Compositing video (PIL LANCZOS Ken Burns)...")
        from video.video_engine import VideoEngine
        raw_video = str(job_dir / "raw_video.mp4")
        VideoEngine(aspect_ratio=aspect_ratio, fps=fps).compose(
            clips=clips, output_path=raw_video, timeline=timeline
        )

        # ── Step 7: Captions ─────────────────────────────────
        set_progress(job_id, 7, "💬 Generating karaoke subtitles (pysubs2 ASS)...")
        from captions.caption_engine import CaptionEngine
        w, h = {"9:16":(1080,1920),"16:9":(1920,1080),"1:1":(1080,1080)}.get(aspect_ratio,(1080,1920))
        captions_path = str(job_dir / "captions.ass")
        CaptionEngine(resolution=(w, h)).build_ass_subtitles(
            timeline=timeline, output_path=captions_path
        )

        # ── Step 8: Audio Mix ────────────────────────────────
        set_progress(job_id, 8, "🎵 Mixing audio + BGM (emotion-based ducking)...")
        from audio.audio_mixer import AudioMixer
        mixed_audio = str(job_dir / "audio_mixed.wav")
        bgm_files = list((Path(__file__).parent / "assets" / "bgm").glob("*.mp3"))
        bgm = str(bgm_files[0]) if bgm_files else audio_path
        AudioMixer().mix(voice_path=audio_path, bgm_path=bgm,
                         timeline=timeline, output_path=mixed_audio)

        # ── Step 9: Final Render ─────────────────────────────
        set_progress(job_id, 9, "🚀 Final FFmpeg render + quality validation...")
        final_video = str(job_dir / "final_video.mp4")
        _ffmpeg_render(raw_video, mixed_audio, captions_path, final_video, fps)

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

        JOBS[job_id].update({"state": "done", "step": 9, "status": "✅ Complete!", "result": result})
        logger.info(f"[{job_id[:8]}] ✅ Done → {result['video_url']}")

    except Exception as e:
        logger.error(f"[{job_id[:8]}] ❌ Failed: {e}")
        JOBS[job_id].update({"state": "error", "error": str(e),
                              "status": f"Failed: {e}"})
        raise


def _ffmpeg_render(video: str, audio: str, captions: str, out: str, fps: int):
    import subprocess
    # Try with burned captions first
    r = subprocess.run([
        "ffmpeg", "-i", video, "-i", audio,
        "-vf", f"ass={captions},fps={fps}",
        "-c:v", "libx264", "-preset", "fast",   # 'fast' for CPU
        "-crf", "23",                             # Quality-based (no fixed bitrate)
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", "-shortest",
        out, "-y"
    ], capture_output=True, text=True)

    if r.returncode != 0:
        # Fallback without burned captions
        subprocess.run([
            "ffmpeg", "-i", video, "-i", audio,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-shortest",
            out, "-y"
        ], check=True, capture_output=True)


def _extract_thumb(video: str, out: str):
    import subprocess
    subprocess.run(["ffmpeg", "-i", video, "-ss", "5", "-vframes", "1",
                    "-q:v", "2", out, "-y"], capture_output=True, check=False)
