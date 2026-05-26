"""
VOXLORE STUDIO — Free Media Engine (Stock + AI Generated)

Priority per segment:
  1. Pexels video          — best quality, cinematic stock footage
  2. Pixabay video         — additional stock (if key present)
  3. Unsplash photo        — high-quality photos → animated Ken Burns video
  4. AI Image Generation   — Gemini Imagen 3 → OpenRouter Flux → Pollinations.ai
                             (channel-aware prompts — tech gets digital art, stoic gets cinematic)
  5. Channel gradient      — FFmpeg animated gradient (absolute last resort, always works)

Channel-aware: tech channel triggers AI image generation earlier (stock footage less relevant).
Stoic channel: stock footage (landscapes, nature) usually works well from Pexels.
"""

import os
import subprocess
import requests
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed


SIMILARITY_THRESHOLD = 0.70   # Relaxed — better recall without Pixabay


class FreeMediaEngine:
    """
    Fetches stock video clips from Pexels + Unsplash.
    Falls back to AI-generated images (Gemini Imagen 3 / OpenRouter Flux / Pollinations)
    when stock footage is unavailable or irrelevant (especially for tech topics).
    """

    def __init__(self, pexels_key: str, pixabay_key: str, faiss_engine,
                 unsplash_key: str = "", channel_id: str = "stoic"):
        self.pexels_key   = pexels_key
        self.pixabay_key  = pixabay_key
        self.unsplash_key = unsplash_key or os.getenv("UNSPLASH_ACCESS_KEY", "")
        self.faiss_engine = faiss_engine
        self.channel_id   = channel_id

        # AI image engine — lazy init on first use
        self._ai_engine   = None

        available = []
        if self.pexels_key:   available.append("Pexels ✅")
        if self.pixabay_key:  available.append("Pixabay ✅")
        else:                  available.append("Pixabay ❌ (no key)")
        if self.unsplash_key: available.append("Unsplash ✅")
        available.append("AI-Imagen ✅")   # always available (Pollinations needs no key)

        logger.info(f"[MediaEngine:{channel_id}] Sources: {', '.join(available)}")

        self.orientation_map = {
            "9:16": "portrait",
            "16:9": "landscape",
            "1:1":  "square",
        }

    @property
    def ai_engine(self):
        """Lazy-init AI image engine."""
        if self._ai_engine is None:
            from media.ai_image_engine import AIImageEngine
            self._ai_engine = AIImageEngine(channel_id=self.channel_id)
        return self._ai_engine

    def fetch_best_clip(self, script_text: str, queries: list, aspect_ratio: str,
                        job_dir: str, segment_id: int) -> str:
        """
        Fetches or generates the best visual clip for a script segment.

        For tech channel: if Pexels returns irrelevant results (abstract tech topics
        like 'neural network', 'binary search', 'transformer model'), AI generation
        is triggered immediately after Pexels attempt fails — no Unsplash fallback needed
        since stock photos of abstract CS concepts don't exist.

        For stoic channel: stock footage (landscapes, nature, architecture) is usually
        sufficient. AI is triggered only when stock sources are fully exhausted.

        Priority:
          1. Pexels video (all channels)
          2. Pixabay video (if key present)
          3. Unsplash photo → Ken Burns (all channels, but skipped for abstract tech)
          4. AI image generation (channel-aware, context-specific prompts)
          5. Gradient placeholder (always works)
        """
        orientation = self.orientation_map.get(aspect_ratio, "portrait")
        w, h = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}.get(aspect_ratio, (1080, 1920))

        for query in queries:
            logger.info(f"[MediaEngine:{self.channel_id}] Query: '{query}' ({orientation})")

            # ── 1. Pexels video ──────────────────────────────────────────
            if self.pexels_key:
                clip = self._fetch_pexels(script_text, query, orientation, job_dir, segment_id)
                if clip:
                    return clip

            # ── 2. Pixabay video (if key) ────────────────────────────────
            if self.pixabay_key:
                clip = self._fetch_pixabay(script_text, query, orientation, job_dir, segment_id)
                if clip:
                    return clip

            # ── 3. Unsplash photo → Ken Burns ────────────────────────────
            # Skip for abstract tech queries that have no real-world stock images
            if self.unsplash_key and not self._is_abstract_tech_query(query):
                clip = self._fetch_unsplash_as_video(
                    script_text, query, orientation, job_dir, segment_id, w, h
                )
                if clip:
                    return clip

            # ── 4. AI image generation (per-query, context-aware) ────────
            # For tech channel: try AI for EVERY failed query (abstract topics need it)
            # For stoic channel: try AI only as last resort within queries
            if self.channel_id == "tech" or queries.index(query) == len(queries) - 1:
                logger.info(f"[MediaEngine:{self.channel_id}] Generating AI image for: '{query}'")
                clip = self.ai_engine.generate_clip(
                    beat_text=script_text,
                    visual_keywords=queries,  # Pass all keywords for richer context
                    job_dir=job_dir,
                    segment_id=segment_id,
                    aspect_ratio=aspect_ratio,
                    duration=10.0,
                )
                if clip:
                    return clip

        # ── 5. Absolute last resort: gradient ────────────────────────────
        logger.warning(f"[MediaEngine:{self.channel_id}] All sources failed for segment {segment_id}")
        return self.ai_engine._generate_gradient_video(job_dir, segment_id, w, h)

    def _is_abstract_tech_query(self, query: str) -> bool:
        """
        Returns True for queries that have no relevant stock footage.
        These are abstract CS/AI concepts where only AI generation can create
        a relevant visual — stock photo sites have nothing useful.
        """
        abstract_tech_keywords = {
            "neural", "algorithm", "transformer", "model", "llm", "attention",
            "backpropagation", "gradient", "vector", "embedding", "token",
            "compiler", "binary", "recursion", "api", "docker", "kubernetes",
            "encryption", "protocol", "database index", "hash", "tcp", "ssl",
            "quantum", "superposition", "qubit", "bandwidth", "latency",
            "training", "inference", "weights", "activation", "softmax",
        }
        q_lower = query.lower()
        return any(kw in q_lower for kw in abstract_tech_keywords)

    # ─────────────────────────────────────────────────────────────────────────
    # Pexels
    # ─────────────────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _fetch_pexels(self, script_text: str, query: str, orientation: str,
                      job_dir: str, segment_id: int) -> str:
        """Fetches video from Pexels API."""
        try:
            resp = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": self.pexels_key},
                params={"query": query, "orientation": orientation,
                        "size": "medium", "per_page": 5},
                timeout=15,
            )
            resp.raise_for_status()

            videos = resp.json().get("videos", [])
            if not videos:
                # Retry without orientation filter
                resp2 = requests.get(
                    "https://api.pexels.com/videos/search",
                    headers={"Authorization": self.pexels_key},
                    params={"query": query, "per_page": 5},
                    timeout=15,
                )
                videos = resp2.json().get("videos", [])

            for video in videos:
                files = sorted(
                    video.get("video_files", []),
                    key=lambda x: x.get("width", 0),
                    reverse=True,
                )
                for vf in files:
                    if vf.get("file_type") == "video/mp4":
                        path = self._download(vf["link"], job_dir, segment_id, "pexels")
                        if path:
                            logger.info(f"[MediaEngine:{self.channel_id}] Pexels: '{query}' -> {Path(path).name}")
                            return path

        except Exception as e:
            logger.warning(f"[MediaEngine:{self.channel_id}] Pexels error '{query}': {e}")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Pixabay
    # ─────────────────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
    def _fetch_pixabay(self, script_text: str, query: str, orientation: str,
                       job_dir: str, segment_id: int) -> str:
        """Fetches video from Pixabay API (only if key present)."""
        try:
            pb_orient = {"portrait": "vertical", "landscape": "horizontal",
                         "square": "all"}.get(orientation, "vertical")
            resp = requests.get(
                "https://pixabay.com/api/videos/",
                params={"key": self.pixabay_key, "q": query, "video_type": "film",
                        "orientation": pb_orient, "per_page": 15, "safesearch": "true"},
                timeout=15,
            )
            resp.raise_for_status()

            for video in resp.json().get("hits", []):
                sim = self.faiss_engine.compute_similarity(script_text, video.get("tags", ""))
                if sim >= SIMILARITY_THRESHOLD:
                    videos = video.get("videos", {})
                    for size in ["large", "medium", "small", "tiny"]:
                        url = videos.get(size, {}).get("url")
                        if url:
                            path = self._download(url, job_dir, segment_id, "pixabay")
                            if path:
                                logger.info(f"[MediaEngine:{self.channel_id}] Pixabay: sim={sim:.2f}")
                                return path

        except Exception as e:
            logger.warning(f"[MediaEngine:{self.channel_id}] Pixabay error: {e}")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Unsplash → Ken Burns animated video
    # ─────────────────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _fetch_unsplash_as_video(self, script_text: str, query: str, orientation: str,
                                  job_dir: str, segment_id: int, w: int, h: int) -> str:
        """
        Downloads a cinematic photo from Unsplash and converts to Ken Burns video.
        Best for: nature, architecture, landscapes, people (stoic channel).
        Skipped for abstract tech queries — AI generation is better.
        """
        try:
            resp = requests.get(
                "https://api.unsplash.com/search/photos",
                headers={"Authorization": f"Client-ID {self.unsplash_key}"},
                params={"query": query, "per_page": 10,
                        "orientation": orientation, "content_filter": "high"},
                timeout=15,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])

            for photo in results:
                description = (photo.get("description") or photo.get("alt_description") or query)
                sim = self.faiss_engine.compute_similarity(script_text, description)

                if sim >= (SIMILARITY_THRESHOLD - 0.10):
                    urls = photo.get("urls", {})
                    img_url = urls.get("full") or urls.get("regular")
                    if not img_url:
                        continue

                    img_path = str(Path(job_dir) / f"unsplash_{segment_id:03d}.jpg")
                    img_resp = requests.get(img_url, timeout=30)
                    img_resp.raise_for_status()
                    Path(img_path).write_bytes(img_resp.content)

                    out = str(Path(job_dir) / f"clip_{segment_id:03d}_unsplash.mp4")
                    duration = 10
                    fps = 30

                    ffmpeg_cmd = [
                        "ffmpeg", "-loop", "1", "-i", img_path,
                        "-vf", (
                            f"scale={w * 2}:{h * 2},"
                            f"zoompan=z='min(zoom+0.0015,1.5)':d={duration * fps}:"
                            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                            f"s={w}x{h}:fps={fps},setsar=1"
                        ),
                        "-c:v", "libx264", "-t", str(duration),
                        "-preset", "fast", "-crf", "23",
                        "-pix_fmt", "yuv420p",
                        out, "-y"
                    ]
                    result = subprocess.run(ffmpeg_cmd, capture_output=True, timeout=120)
                    if result.returncode == 0 and Path(out).exists():
                        logger.info(f"[MediaEngine:{self.channel_id}] Unsplash→video: sim={sim:.2f} -> {Path(out).name}")
                        return out

        except Exception as e:
            logger.warning(f"[MediaEngine:{self.channel_id}] Unsplash error: {e}")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _download(self, url: str, job_dir: str, segment_id: int, source: str) -> str:
        """Downloads a video file to local storage."""
        try:
            out = str(Path(job_dir) / f"clip_{segment_id:03d}_{source}.mp4")
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(out, "wb") as f:
                    for chunk in r.iter_content(chunk_size=16384):
                        f.write(chunk)
            size_mb = Path(out).stat().st_size / 1024 / 1024
            logger.info(f"[MediaEngine:{self.channel_id}] Downloaded {size_mb:.1f}MB -> {Path(out).name}")
            return out
        except Exception as e:
            logger.error(f"[MediaEngine:{self.channel_id}] Download error: {e}")
            return None

    # Keep backward-compatible name (called from verify_all)
    def _generate_placeholder(self, job_dir: str, segment_id: int, aspect_ratio: str) -> str:
        """Backward-compat: calls AI gradient generator."""
        w, h = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}.get(aspect_ratio, (1080, 1920))
        return self.ai_engine._generate_gradient_video(job_dir, segment_id, w, h)


# Alias for backward compatibility
MediaEngine = FreeMediaEngine
