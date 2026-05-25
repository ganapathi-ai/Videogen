"""
THE INNER CITADEL — Free Media Engine
Priority: Pexels (video) → Unsplash (photo→video) → Placeholder

Pexels: cinematic videos (your primary key)
Unsplash: high-quality photos converted to Ken Burns video clips
Pixabay: disabled (no key), gracefully skipped
FAISS: semantic filtering (cosine ≥ 0.70 — relaxed for better recall)
"""

import os
import subprocess
import requests
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed


SIMILARITY_THRESHOLD = 0.70   # Relaxed from 0.82 — better recall without Pixabay


class FreeMediaEngine:
    """
    Fetches stock video clips from Pexels + Unsplash.
    Falls back to solid-color placeholder only if both fail.
    """

    def __init__(self, pexels_key: str, pixabay_key: str, faiss_engine,
                 unsplash_key: str = ""):
        self.pexels_key   = pexels_key
        self.pixabay_key  = pixabay_key   # May be empty — handled gracefully
        self.unsplash_key = unsplash_key or os.getenv("UNSPLASH_ACCESS_KEY", "")
        self.faiss_engine = faiss_engine

        available = []
        if self.pexels_key:   available.append("Pexels ✅")
        if self.pixabay_key:  available.append("Pixabay ✅")
        else:                  available.append("Pixabay ❌ (no key)")
        if self.unsplash_key: available.append("Unsplash ✅")

        logger.info(f"[MediaEngine] Sources: {', '.join(available)}")

        self.orientation_map = {
            "9:16": "portrait",
            "16:9": "landscape",
            "1:1":  "square",
        }

    def fetch_best_clip(self, script_text: str, queries: list, aspect_ratio: str,
                        job_dir: str, segment_id: int) -> str:
        """
        Fetches the best matching clip for a script segment.

        Priority:
          1. Pexels video (highest quality)
          2. Unsplash photo → animated Ken Burns video
          3. Solid dark placeholder (last resort)
        """
        orientation = self.orientation_map.get(aspect_ratio, "portrait")
        w, h = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}.get(aspect_ratio, (1080, 1920))

        for query in queries:
            logger.info(f"[MediaEngine] Query: '{query}' ({orientation})")

            # 1. Pexels video
            if self.pexels_key:
                clip = self._fetch_pexels(script_text, query, orientation, job_dir, segment_id)
                if clip:
                    return clip

            # 2. Pixabay video (if key present)
            if self.pixabay_key:
                clip = self._fetch_pixabay(script_text, query, orientation, job_dir, segment_id)
                if clip:
                    return clip

            # 3. Unsplash photo → Ken Burns video
            if self.unsplash_key:
                clip = self._fetch_unsplash_as_video(
                    script_text, query, orientation, job_dir, segment_id, w, h
                )
                if clip:
                    return clip

        # Last resort
        logger.warning(f"[MediaEngine] No media found for segment {segment_id}. Using placeholder.")
        return self._generate_placeholder(job_dir, segment_id, aspect_ratio)

    # ─────────────────────────────────────────────────────────
    # Pexels
    # ─────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _fetch_pexels(self, script_text: str, query: str, orientation: str,
                      job_dir: str, segment_id: int) -> str:
        """Fetches video from Pexels API. Takes best result directly (no FAISS filter)."""
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
                # Pick the best MP4 file (highest resolution that fits)
                files = sorted(
                    video.get("video_files", []),
                    key=lambda x: x.get("width", 0),
                    reverse=True,
                )
                for vf in files:
                    if vf.get("file_type") == "video/mp4":
                        path = self._download(vf["link"], job_dir, segment_id, "pexels")
                        if path:
                            logger.info(f"[MediaEngine] Pexels: '{query}' -> {path}")
                            return path

        except Exception as e:
            logger.warning(f"[MediaEngine] Pexels error for '{query}': {e}")
        return None


    # ─────────────────────────────────────────────────────────
    # Pixabay
    # ─────────────────────────────────────────────────────────

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
                                logger.info(f"[MediaEngine] ✅ Pixabay: sim={sim:.2f}")
                                return path

        except Exception as e:
            logger.warning(f"[MediaEngine] Pixabay error: {e}")
        return None

    # ─────────────────────────────────────────────────────────
    # Unsplash → Ken Burns animated video
    # ─────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _fetch_unsplash_as_video(self, script_text: str, query: str, orientation: str,
                                  job_dir: str, segment_id: int, w: int, h: int) -> str:
        """
        Downloads a cinematic photo from Unsplash and converts it to a
        Ken Burns slow-zoom video clip using FFmpeg zoompan filter.
        """
        try:
            # Fetch photo
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

                if sim >= (SIMILARITY_THRESHOLD - 0.10):  # Slightly lower for photos
                    # Download the highest resolution available
                    urls = photo.get("urls", {})
                    img_url = urls.get("full") or urls.get("regular")
                    if not img_url:
                        continue

                    img_path = str(Path(job_dir) / f"unsplash_{segment_id:03d}.jpg")
                    img_resp = requests.get(img_url, timeout=30)
                    img_resp.raise_for_status()
                    Path(img_path).write_bytes(img_resp.content)

                    # Convert photo to 10s Ken Burns video with FFmpeg zoompan
                    out = str(Path(job_dir) / f"clip_{segment_id:03d}_unsplash.mp4")
                    duration = 10
                    fps = 30

                    ffmpeg_cmd = [
                        "ffmpeg",
                        "-loop", "1",
                        "-i", img_path,
                        "-vf", (
                            f"scale={w * 2}:{h * 2},"
                            f"zoompan=z='min(zoom+0.0015,1.5)':d={duration * fps}:"
                            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                            f"s={w}x{h}:fps={fps},"
                            f"setsar=1"
                        ),
                        "-c:v", "libx264",
                        "-t", str(duration),
                        "-preset", "fast",
                        "-crf", "23",
                        "-pix_fmt", "yuv420p",
                        out, "-y"
                    ]
                    result = subprocess.run(ffmpeg_cmd, capture_output=True, timeout=120)
                    if result.returncode == 0 and Path(out).exists():
                        logger.info(f"[MediaEngine] ✅ Unsplash→video: sim={sim:.2f} → {out}")
                        return out
                    else:
                        logger.warning(f"[MediaEngine] FFmpeg zoompan failed: {result.stderr[:200]}")

        except Exception as e:
            logger.warning(f"[MediaEngine] Unsplash error: {e}")
        return None

    # ─────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────

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
            logger.info(f"[MediaEngine] Downloaded {size_mb:.1f}MB → {out}")
            return out
        except Exception as e:
            logger.error(f"[MediaEngine] Download error: {e}")
            return None

    def _generate_placeholder(self, job_dir: str, segment_id: int, aspect_ratio: str) -> str:
        """Creates a dark cinematic placeholder video (absolute last resort)."""
        w, h = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}.get(aspect_ratio, (1080, 1920))
        out = str(Path(job_dir) / f"placeholder_{segment_id:03d}.mp4")
        subprocess.run([
            "ffmpeg", "-f", "lavfi",
            "-i", f"color=c=0x1a1a2e:s={w}x{h}:r=30",
            "-t", "10", "-c:v", "libx264",
            out, "-y"
        ], capture_output=True, check=False)
        logger.warning(f"[MediaEngine] Placeholder created: {out}")
        return out
