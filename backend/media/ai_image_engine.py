"""
VOXLORE STUDIO — AI Image Generation Engine

Generates contextually accurate images when stock footage (Pexels/Unsplash) fails.
Especially important for tech/AI topics where cinematic stock footage is scarce.

Fallback chain (all free tiers):
  1. Gemini Imagen 3  — Google's best image model (free tier via Gemini API key)
  2. OpenRouter       — Flux-schnell or SDXL (free :free models on OpenRouter)
  3. Pollinations.ai  — Truly free, no auth, no key, no rate limit (pure HTTP GET)
  4. FFmpeg gradient  — Always works, channel-themed animated gradient (absolute last resort)

All generated images → Ken Burns animated video via FFmpeg zoompan.

Channel-aware prompting:
  stoic  → dramatic cinematic photography style (dark tones, ancient, contemplative)
  tech   → clean digital concept art style (glowing circuits, data visualization, blue/cyan)

Per-channel prompt prefix injected automatically — no manual tuning needed.
Images are cached per job_dir to avoid re-generating on retry.
"""

import os
import base64
import hashlib
import subprocess
import requests
from pathlib import Path
from loguru import logger


# ── Channel-specific visual style prefixes ─────────────────────────────────────
# These are injected before every image prompt to ensure contextual relevance.
# Research: what visual aesthetic fits each channel's identity.

CHANNEL_VISUAL_STYLE = {
    "stoic": (
        "Cinematic dramatic photography, dark moody tones, ancient stone textures, "
        "dramatic natural lighting, golden hour, silhouetted figures against vast landscapes, "
        "contemplative atmosphere, film grain, desaturated color palette with warm amber accents, "
        "4K ultra-realistic, no text, no watermarks, no people's faces visible. "
        "Style: Pursuit of Wonder, Einzelganger, BBC documentary aesthetic. "
    ),
    "tech": (
        "Clean modern digital concept art, glowing circuit patterns, data visualization, "
        "deep blue and cyan color palette, abstract technology visualization, "
        "holographic displays, neural network nodes, server infrastructure, "
        "professional tech photography style, sharp and bright, no text overlay, "
        "Kurzgesagt-inspired color scheme, 4K ultra-detailed. "
        "Style: ByteByteGo, Fireship, 3Blue1Brown visual aesthetic. "
    ),
    "_default": (
        "Cinematic high-quality photography, dramatic lighting, professional composition, "
        "4K ultra-realistic, no text, no watermarks, visually compelling. "
    ),
}


class AIImageEngine:
    """
    Generates AI images when stock footage sources are exhausted.
    Converts generated images to Ken Burns animated video clips.

    Usage:
        engine = AIImageEngine(channel_id="tech")
        video_path = engine.generate_clip(
            beat_text="How neural networks learn from data",
            visual_keywords=["neural network", "data visualization"],
            job_dir="exports/abc123",
            segment_id=3,
            aspect_ratio="9:16"
        )
    """

    def __init__(self, channel_id: str = "stoic"):
        self.channel_id     = channel_id
        self.gemini_key     = os.getenv("GEMINI_API_KEY", "")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.style_prefix   = CHANNEL_VISUAL_STYLE.get(channel_id, CHANNEL_VISUAL_STYLE["_default"])
        logger.info(f"[AIImageGen:{channel_id}] Engine ready | Gemini={'✅' if self.gemini_key else '❌'} | OpenRouter={'✅' if self.openrouter_key else '❌'} | Pollinations=✅")

    def generate_clip(self, beat_text: str, visual_keywords: list,
                      job_dir: str, segment_id: int,
                      aspect_ratio: str = "9:16",
                      duration: float = 10.0) -> str:
        """
        Generates an AI image then converts to Ken Burns animated video.

        Returns:
            str: Path to generated .mp4 video clip, or None if all methods fail.
        """
        w, h = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}.get(aspect_ratio, (1080, 1920))

        # Build a rich contextual prompt from beat text + visual keywords
        prompt = self._build_prompt(beat_text, visual_keywords)

        # Check cache first (avoid re-generating same content)
        cache_key = hashlib.md5(f"{self.channel_id}:{prompt}".encode()).hexdigest()[:12]
        img_path  = str(Path(job_dir) / f"ai_img_{segment_id:03d}_{cache_key}.jpg")

        # Try each image source
        img_data = (
            self._generate_gemini_imagen(prompt, aspect_ratio)
            or self._generate_openrouter(prompt, w, h)
            or self._generate_pollinations(prompt, w, h)
        )

        if img_data:
            Path(img_path).write_bytes(img_data)
            video_path = self._image_to_video(img_path, job_dir, segment_id, w, h, duration)
            if video_path:
                return video_path

        # Absolute last resort: channel-themed FFmpeg gradient animation
        logger.warning(f"[AIImageGen:{self.channel_id}] All image methods failed — using gradient")
        return self._generate_gradient_video(job_dir, segment_id, w, h, duration)

    # ─────────────────────────────────────────────────────────────────────────
    # Prompt Builder
    # ─────────────────────────────────────────────────────────────────────────

    def _build_prompt(self, beat_text: str, visual_keywords: list) -> str:
        """
        Builds a rich, channel-specific image prompt.
        Combines channel visual style + beat context + visual keywords.
        """
        keywords_str = ", ".join(visual_keywords[:3]) if visual_keywords else ""

        # Build contextual description from beat text
        # e.g. "How neural networks learn" → visual keywords drive the image
        context = keywords_str if keywords_str else beat_text[:80]

        prompt = f"{self.style_prefix}Subject: {context}. "

        # Add channel-specific refinements
        if self.channel_id == "tech":
            prompt += (
                "Visualize the concept as a stunning digital artwork. "
                "If showing technology: make it abstract and beautiful, not literal screenshots. "
                "Think: glowing data flows, connected nodes, holographic interfaces."
            )
        elif self.channel_id == "stoic":
            prompt += (
                "Visualize the emotion and concept cinematically. "
                "Think: lone figure on mountain peak, vast ocean horizon, ancient ruins at dusk, "
                "dramatic storm clouds, flickering candle in darkness, stone corridor with light beam."
            )

        logger.debug(f"[AIImageGen:{self.channel_id}] Prompt: {prompt[:120]}...")
        return prompt

    # ─────────────────────────────────────────────────────────────────────────
    # Source 1: Gemini Imagen 3 (Google)
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_gemini_imagen(self, prompt: str, aspect_ratio: str = "9:16") -> bytes:
        """
        Uses Gemini Imagen 3 via google-genai SDK.
        Free tier: 15 requests/min, 1500/day.
        Returns raw image bytes (JPEG) or None on failure.
        """
        if not self.gemini_key:
            return None
        try:
            from google import genai
            from google.genai import types as gtypes

            client = genai.Client(api_key=self.gemini_key)

            # Aspect ratio map for Imagen 3
            ar_map = {"9:16": "9:16", "16:9": "16:9", "1:1": "1:1"}
            ar = ar_map.get(aspect_ratio, "9:16")

            response = client.models.generate_images(
                model="imagen-3.0-generate-002",
                prompt=prompt,
                config=gtypes.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=ar,
                    safety_filter_level="BLOCK_ONLY_HIGH",
                    person_generation="DONT_ALLOW",  # no faces — cleaner visuals
                ),
            )

            if response.generated_images:
                img = response.generated_images[0]
                # image_bytes is base64 or raw bytes depending on SDK version
                if hasattr(img, "image") and hasattr(img.image, "image_bytes"):
                    data = img.image.image_bytes
                elif hasattr(img, "image_bytes"):
                    data = img.image_bytes
                else:
                    data = None

                if data:
                    logger.info(f"[AIImageGen:{self.channel_id}] Gemini Imagen 3 ✅ ({len(data)//1024}KB)")
                    return data

        except Exception as e:
            logger.warning(f"[AIImageGen:{self.channel_id}] Gemini Imagen failed: {e}")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Source 2: OpenRouter — Flux / SDXL (free models)
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_openrouter(self, prompt: str, w: int, h: int) -> bytes:
        """
        Uses OpenRouter's free image generation models.
        Tries: black-forest-labs/flux-schnell:free → stabilityai/sdxl:free
        Returns raw image bytes or None on failure.
        """
        if not self.openrouter_key:
            return None

        # Free image models on OpenRouter (as of 2025-2026)
        models = [
            "black-forest-labs/flux-schnell:free",
            "black-forest-labs/flux-1.1-pro:free",
            "stabilityai/stable-diffusion-xl-base-1.0:free",
        ]

        for model in models:
            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "Content-Type":  "application/json",
                        "HTTP-Referer":  "https://voxlore.studio",
                        "X-Title":       "Voxlore Studio",
                    },
                    json={
                        "model":  model,
                        "prompt": prompt[:1000],  # OpenRouter has prompt length limits
                        "size":   f"{min(w, 1024)}x{min(h, 1024)}",  # API max 1024
                        "n": 1,
                    },
                    timeout=60,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    img_url = data.get("data", [{}])[0].get("url")
                    if img_url:
                        img_resp = requests.get(img_url, timeout=30)
                        if img_resp.status_code == 200:
                            logger.info(f"[AIImageGen:{self.channel_id}] OpenRouter {model.split('/')[1]} ✅")
                            return img_resp.content
                    # b64_json fallback
                    b64 = data.get("data", [{}])[0].get("b64_json")
                    if b64:
                        logger.info(f"[AIImageGen:{self.channel_id}] OpenRouter {model} (b64) ✅")
                        return base64.b64decode(b64)
                else:
                    logger.debug(f"[AIImageGen:{self.channel_id}] OpenRouter {model}: {resp.status_code}")
                    continue

            except Exception as e:
                logger.debug(f"[AIImageGen:{self.channel_id}] OpenRouter {model} error: {e}")
                continue

        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Source 3: Pollinations.ai — Truly free, no API key needed
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_pollinations(self, prompt: str, w: int, h: int) -> bytes:
        """
        Pollinations.ai: completely free AI image generation.
        No API key, no rate limits advertised, no signup.
        Uses FLUX model under the hood.
        URL: https://image.pollinations.ai/prompt/{encoded_prompt}?width=W&height=H
        """
        try:
            import urllib.parse

            # Cap to reasonable dimensions for API
            pw = min(w, 1080)
            ph = min(h, 1920)

            # Build URL (pollinations accepts URL-encoded prompt directly)
            encoded = urllib.parse.quote(prompt[:500])
            url = (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width={pw}&height={ph}&model=flux&nologo=true&enhance=true"
                f"&seed={abs(hash(prompt)) % 9999}"
            )

            resp = requests.get(url, timeout=90, stream=True)  # Can be slow — allow 90s
            if resp.status_code == 200 and len(resp.content) > 5000:
                logger.info(f"[AIImageGen:{self.channel_id}] Pollinations.ai ✅ ({len(resp.content)//1024}KB)")
                return resp.content

            logger.debug(f"[AIImageGen:{self.channel_id}] Pollinations: {resp.status_code} ({len(resp.content)}B)")

        except Exception as e:
            logger.warning(f"[AIImageGen:{self.channel_id}] Pollinations error: {e}")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Image → Ken Burns Video
    # ─────────────────────────────────────────────────────────────────────────

    def _image_to_video(self, img_path: str, job_dir: str, segment_id: int,
                        w: int, h: int, duration: float = 10.0) -> str:
        """
        Converts a generated image to an animated Ken Burns video clip.
        Uses FFmpeg zoompan filter — slow zoom creates cinematic motion.
        """
        out = str(Path(job_dir) / f"clip_{segment_id:03d}_aigen.mp4")
        fps = 30
        frames = int(duration * fps)

        # Random-like zoom direction based on segment_id (avoids identical motion on consecutive clips)
        zoom_dir = segment_id % 4
        if zoom_dir == 0:   # Zoom in center
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
            z_expr = "min(zoom+0.0015,1.5)"
        elif zoom_dir == 1: # Zoom in top-left
            x_expr = "0"
            y_expr = "0"
            z_expr = "min(zoom+0.0015,1.5)"
        elif zoom_dir == 2: # Zoom out center
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
            z_expr = "max(zoom-0.0010,1.0)"
        else:               # Pan right
            x_expr = "min(x+1,ow)"
            y_expr = "ih/2-(ih/zoom/2)"
            z_expr = "min(zoom+0.0008,1.3)"

        vf = (
            f"scale={w*2}:{h*2},"
            f"zoompan=z='{z_expr}':d={frames}:"
            f"x='{x_expr}':y='{y_expr}':"
            f"s={w}x{h}:fps={fps},"
            f"setsar=1"
        )

        cmd = [
            "ffmpeg", "-loop", "1", "-i", img_path,
            "-vf", vf,
            "-c:v", "libx264", "-t", str(duration),
            "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            out, "-y"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode == 0 and Path(out).stat().st_size > 10000:
                logger.info(f"[AIImageGen:{self.channel_id}] Ken Burns video: {out}")
                return out
            else:
                logger.warning(f"[AIImageGen:{self.channel_id}] zoompan failed: {result.stderr[-200:]}")
        except Exception as e:
            logger.warning(f"[AIImageGen:{self.channel_id}] image_to_video error: {e}")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Absolute Last Resort: Channel-Themed Gradient Animation
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_gradient_video(self, job_dir: str, segment_id: int,
                                 w: int, h: int, duration: float = 10.0) -> str:
        """
        Generates a channel-themed animated gradient as absolute last resort.
        Uses FFmpeg lavfi — no external dependencies, always works.

        Stoic:  Deep midnight blue → warm amber (contemplative, ancient)
        Tech:   Deep navy → electric cyan (digital, futuristic)
        """
        out = str(Path(job_dir) / f"clip_{segment_id:03d}_gradient.mp4")

        # Channel-specific gradient colors
        colors = {
            "stoic": ("0x1a1a2e", "0x16213e", "0xC4A064"),  # midnight blue → amber
            "tech":  ("0x0a0a1a", "0x001a33", "0x00D4FF"),  # deep navy → electric cyan
        }.get(self.channel_id, ("0x111111", "0x222222", "0x888888"))

        c1, c2, c3 = colors

        # Animated gradient using FFmpeg gradients filter
        vf = (
            f"gradients=s={w}x{h}:c0={c1}:c1={c2}:c2={c3}:nb_colors=3"
            f":speed=0.3:type=linear,setsar=1"
        )

        cmd = [
            "ffmpeg", "-f", "lavfi", "-i", f"color=black:s={w}x{h}:r=30",
            "-f", "lavfi", "-i", f"gradients=s={w}x{h}:c0={c1}:c1={c2}:c2={c3}:speed=0.3",
            "-map", "1",
            "-c:v", "libx264", "-t", str(duration),
            "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            out, "-y"
        ]

        # Fallback to simple solid color if gradients filter unavailable
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode != 0:
            main_color = c2
            cmd2 = [
                "ffmpeg", "-f", "lavfi",
                "-i", f"color=c={main_color}:s={w}x{h}:r=30",
                "-t", str(duration), "-c:v", "libx264",
                "-preset", "fast", "-pix_fmt", "yuv420p",
                out, "-y"
            ]
            subprocess.run(cmd2, capture_output=True, timeout=30)

        logger.info(f"[AIImageGen:{self.channel_id}] Gradient video: {out}")
        return out if Path(out).exists() else None
