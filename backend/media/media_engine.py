"""
THE INNER CITADEL — Free Media Engine
Fetches cinematic stock footage from Pexels and Pixabay APIs (both 100% free).
Uses FAISS cosine similarity to semantically filter irrelevant clips (threshold: 0.82).
"""

import os
import time
import requests
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed


SIMILARITY_THRESHOLD = 0.82    # Per research mandate: reject clips below this


class FreeMediaEngine:
    """
    Fetches stock video clips from Pexels and Pixabay.
    Ranks clips by semantic similarity to the script text.
    Downloads highest-resolution MP4 available.
    """

    def __init__(self, pexels_key: str, pixabay_key: str, faiss_engine):
        self.pexels_key = pexels_key
        self.pixabay_key = pixabay_key
        self.faiss_engine = faiss_engine

        if not pexels_key:
            logger.warning("[MediaEngine] PEXELS_API_KEY not set — Pexels disabled")
        if not pixabay_key:
            logger.warning("[MediaEngine] PIXABAY_API_KEY not set — Pixabay disabled")

        # Aspect ratio → API orientation parameter
        self.orientation_map = {
            "9:16": "portrait",
            "16:9": "landscape",
            "1:1": "square",
        }

        logger.info("[MediaEngine] Initialized with Pexels + Pixabay + FAISS")

    def fetch_best_clip(self, script_text: str, queries: list, aspect_ratio: str,
                        job_dir: str, segment_id: int) -> str:
        """
        Fetches the best matching video clip for a script segment.

        Priority order:
        1. Pexels API (highest quality)
        2. Pixabay API (fallback)
        3. Solid color placeholder (last resort)

        Args:
            script_text: The script beat text for semantic matching
            queries: List of visual search queries from ScriptEngine
            aspect_ratio: "9:16" | "16:9" | "1:1"
            job_dir: Directory to download clips into
            segment_id: Segment ID for unique filename

        Returns:
            str: Local path to downloaded video clip
        """
        orientation = self.orientation_map.get(aspect_ratio, "portrait")

        for query in queries:
            logger.info(f"[MediaEngine] Searching: '{query}' ({orientation})")

            # Try Pexels first
            if self.pexels_key:
                clip = self._fetch_from_pexels(script_text, query, orientation, job_dir, segment_id)
                if clip:
                    return clip

            # Fallback to Pixabay
            if self.pixabay_key:
                clip = self._fetch_from_pixabay(script_text, query, orientation, job_dir, segment_id)
                if clip:
                    return clip

        # Last resort: generate solid color placeholder
        logger.warning(f"[MediaEngine] No clip found for segment {segment_id}. Using placeholder.")
        return self._generate_placeholder(job_dir, segment_id, aspect_ratio)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _fetch_from_pexels(self, script_text: str, query: str, orientation: str,
                            job_dir: str, segment_id: int) -> str:
        """Fetches video from Pexels API."""
        try:
            headers = {"Authorization": self.pexels_key}
            params = {
                "query": query,
                "orientation": orientation,
                "size": "large",
                "per_page": 15,
            }
            resp = requests.get(
                "https://api.pexels.com/videos/search",
                headers=headers,
                params=params,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            for video in data.get("videos", []):
                tags = video.get("url", "") + " " + str(video.get("tags", ""))
                similarity = self.faiss_engine.compute_similarity(script_text, tags)

                if similarity >= SIMILARITY_THRESHOLD:
                    # Find best quality file
                    video_files = sorted(
                        video.get("video_files", []),
                        key=lambda x: x.get("width", 0),
                        reverse=True
                    )
                    for vf in video_files:
                        if vf.get("file_type") == "video/mp4":
                            url = vf["link"]
                            path = self._download_clip(url, job_dir, segment_id, "pexels")
                            if path:
                                logger.info(f"[MediaEngine] ✅ Pexels clip: similarity={similarity:.3f}")
                                return path

        except Exception as e:
            logger.error(f"[MediaEngine] Pexels error: {e}")
        return None

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _fetch_from_pixabay(self, script_text: str, query: str, orientation: str,
                             job_dir: str, segment_id: int) -> str:
        """Fetches video from Pixabay API."""
        try:
            # Map orientation
            pixabay_orientation = {
                "portrait": "vertical",
                "landscape": "horizontal",
                "square": "all"
            }.get(orientation, "vertical")

            params = {
                "key": self.pixabay_key,
                "q": query,
                "video_type": "film",
                "orientation": pixabay_orientation,
                "per_page": 15,
                "safesearch": "true",
            }
            resp = requests.get(
                "https://pixabay.com/api/videos/",
                params=params,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            for video in data.get("hits", []):
                tags = video.get("tags", "")
                similarity = self.faiss_engine.compute_similarity(script_text, tags)

                if similarity >= SIMILARITY_THRESHOLD:
                    # Get large MP4
                    videos = video.get("videos", {})
                    for size in ["large", "medium", "small", "tiny"]:
                        vid = videos.get(size, {})
                        url = vid.get("url")
                        if url:
                            path = self._download_clip(url, job_dir, segment_id, "pixabay")
                            if path:
                                logger.info(f"[MediaEngine] ✅ Pixabay clip: similarity={similarity:.3f}")
                                return path

        except Exception as e:
            logger.error(f"[MediaEngine] Pixabay error: {e}")
        return None

    def _download_clip(self, url: str, job_dir: str, segment_id: int, source: str) -> str:
        """Downloads a video clip to local storage."""
        try:
            output_path = str(Path(job_dir) / f"clip_{segment_id:03d}_{source}.mp4")
            logger.info(f"[MediaEngine] Downloading: {url[:60]}...")

            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            size_mb = Path(output_path).stat().st_size / 1024 / 1024
            logger.info(f"[MediaEngine] Downloaded: {output_path} ({size_mb:.1f} MB)")
            return output_path

        except Exception as e:
            logger.error(f"[MediaEngine] Download error: {e}")
            return None

    def _generate_placeholder(self, job_dir: str, segment_id: int, aspect_ratio: str) -> str:
        """Creates a solid dark color placeholder video (last resort fallback)."""
        import subprocess

        w, h = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}.get(aspect_ratio, (1080, 1920))
        output_path = str(Path(job_dir) / f"placeholder_{segment_id:03d}.mp4")

        # Generate 10s dark charcoal placeholder
        subprocess.run([
            "ffmpeg",
            "-f", "lavfi",
            "-i", f"color=c=0x1a1a2e:s={w}x{h}:r=60",
            "-t", "10",
            "-c:v", "libx264",
            output_path, "-y"
        ], capture_output=True, check=False)

        logger.warning(f"[MediaEngine] Created placeholder: {output_path}")
        return output_path
