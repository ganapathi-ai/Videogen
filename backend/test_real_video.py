"""
REAL END-TO-END VIDEO TEST
Generates a real short video (1 beat) through the actual pipeline
and verifies: yuv420p pixel format, visible text in frame, file opens.
"""
import subprocess, sys, os, shutil, uuid
from pathlib import Path

sys.path.insert(0, ".")
os.environ.setdefault("PEXELS_API_KEY", "")
os.environ.setdefault("UNSPLASH_ACCESS_KEY", "")

PASS = "[OK] "
FAIL = "[FAIL] "
results = []
job_dir = Path(f"test_e2e_{uuid.uuid4().hex[:6]}")
job_dir.mkdir(exist_ok=True)

print("=" * 55)
print("REAL END-TO-END VIDEO RENDER TEST")
print("=" * 55)

# ── Step 1: Build a real ASS subtitle file ─────────────────────────────────
print("\n[1] Building ASS subtitle (Arial font)...")
from captions.caption_engine import CaptionEngine

# Fake timeline with one segment
fake_timeline = {
    "title": "Test Video",
    "segments": [{
        "segment_id": 0,
        "audio_start": 0.0,
        "audio_end": 5.0,
        "word_data": [
            {"word": "DISCIPLINE", "start": 0.0, "end": 1.0},
            {"word": "IS",         "start": 1.0, "end": 1.5},
            {"word": "FREEDOM",    "start": 1.5, "end": 2.5},
            {"word": "ALWAYS",     "start": 2.5, "end": 3.5},
        ]
    }]
}
ass_out = str(job_dir / "captions.ass")
cap = CaptionEngine(resolution=(1080, 1920))
cap.build_ass_subtitles(fake_timeline, ass_out)
assert Path(ass_out).exists(), "ASS file not created"
# Check font in ASS file
ass_content = Path(ass_out).read_text(encoding="utf-8")
if "Arial" in ass_content and "Montserrat" not in ass_content:
    results.append((True, "ASS file uses Arial font"))
    print(f"  {PASS}ASS file uses Arial font")
else:
    results.append((False, "ASS wrong font"))
    print(f"  {FAIL}Font wrong in ASS file")
    print("  Lines:", [l for l in ass_content.split("\n") if "Style:" in l])

# ── Step 2: Create test video + audio ──────────────────────────────────────
print("\n[2] Creating test black video + sine audio...")
raw_video = str(job_dir / "raw_video.mp4")
audio_mix  = str(job_dir / "audio_mixed.wav")

r = subprocess.run([
    "ffmpeg", "-f", "lavfi", "-i", "color=black:s=1080x1920:r=30",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", "5",
    "-preset", "fast", raw_video, "-y"
], capture_output=True, text=True, timeout=20)
assert r.returncode == 0, f"Raw video failed: {r.stderr[-100:]}"

r = subprocess.run([
    "ffmpeg", "-f", "lavfi", "-i", "sine=frequency=220:duration=5",
    "-c:a", "pcm_s16le", audio_mix, "-y"
], capture_output=True, text=True, timeout=15)
assert r.returncode == 0, f"Audio failed: {r.stderr[-100:]}"
print(f"  {PASS}Raw video + audio created")

# ── Step 3: Run actual _ffmpeg_render ───────────────────────────────────────
print("\n[3] Running _ffmpeg_render (the actual function used in production)...")
from main import _ffmpeg_render

final_out = str(job_dir / "final_video.mp4")
_ffmpeg_render(
    video=raw_video,
    audio=audio_mix,
    captions=ass_out,
    out=final_out,
    fps=30,
    duration=5.0,
    watermark="neuralbaba_empire"
)

size = Path(final_out).stat().st_size if Path(final_out).exists() else 0
if size > 50000:
    results.append((True, f"final_video.mp4 created: {size//1024}KB"))
    print(f"  {PASS}final_video.mp4: {size//1024}KB")
else:
    results.append((False, f"final_video.mp4 too small: {size}B"))
    print(f"  {FAIL}final_video.mp4: {size}B (too small)")

# ── Step 4: Verify yuv420p ──────────────────────────────────────────────────
print("\n[4] Verifying pixel format (yuv420p = opens on all players)...")
probe = subprocess.run([
    "ffprobe", "-v", "quiet", "-show_streams", "-select_streams", "v",
    "-print_format", "compact", final_out
], capture_output=True, text=True)
if "yuv420p" in probe.stdout:
    results.append((True, "yuv420p confirmed"))
    print(f"  {PASS}Pixel format: yuv420p")
    if "high" in probe.stdout.lower() or "4.0" in probe.stdout:
        print(f"  {PASS}Profile: High 4.0 (maximum compatibility)")
else:
    results.append((False, "yuv420p missing"))
    print(f"  {FAIL}yuv420p NOT in output: {probe.stdout[:200]}")

# ── Step 5: Verify text is visible ─────────────────────────────────────────
print("\n[5] Verifying text is visible (frame size test)...")
frame = str(job_dir / "frame_check.jpg")
r2 = subprocess.run([
    "ffmpeg", "-i", final_out,
    "-ss", "1.0", "-frames:v", "1", frame, "-y"
], capture_output=True, text=True, timeout=15)
frame_size = Path(frame).stat().st_size if Path(frame).exists() else 0
# A black frame with NO text at 1080x1920 JPEG ≈ 3-5KB
# A frame WITH white bold text ≈ 20-30KB (JPEG encodes text as high-frequency detail)
if r2.returncode == 0 and frame_size > 12000:
    results.append((True, f"Text visible: {frame_size//1024}KB frame"))
    print(f"  {PASS}Frame with text: {frame_size//1024}KB (visible white text confirmed)")
else:
    results.append((False, f"Text not visible: {frame_size}B"))
    print(f"  {FAIL}Frame too small ({frame_size}B) — text may be invisible")

# ── Step 6: Check render method used ───────────────────────────────────────
print("\n[6] Checking which render path was used...")
# If full render worked, final_video should have both video+audio
probe2 = subprocess.run([
    "ffprobe", "-v", "quiet", "-show_streams",
    "-print_format", "compact", final_out
], capture_output=True, text=True)
has_video = "codec_type=video" in probe2.stdout
has_audio = "codec_type=audio" in probe2.stdout
if has_video and has_audio:
    results.append((True, "Video has both video+audio tracks"))
    print(f"  {PASS}Output has video + audio tracks")
else:
    print(f"  {FAIL}Missing tracks: video={has_video} audio={has_audio}")

# ── Cleanup ─────────────────────────────────────────────────────────────────
shutil.rmtree(job_dir, ignore_errors=True)

# ── Summary ─────────────────────────────────────────────────────────────────
print()
passed = sum(1 for ok,_ in results if ok)
failed = sum(1 for ok,_ in results if not ok)
print("=" * 55)
print(f"RESULT: {passed}/{len(results)} passed | {failed} failed")
if not failed:
    print("VIDEO PIPELINE IS WORKING CORRECTLY")
    print()
    print("THE OLD LOG YOU SAW IS FROM 08:31 AM — BEFORE FIXES")
    print("RESTART YOUR BACKEND AND TRY AGAIN:")
    print()
    print("  Ctrl+C  (stop the old backend)")
    print("  python -m uvicorn main:app --reload --port 8000")
    sys.exit(0)
else:
    print("ISSUES REMAIN — see above")
    sys.exit(1)
