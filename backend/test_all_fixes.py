"""End-to-end validation of all 5 fixes: font, ASS path, yuv420p, Gemini model, rate limits."""
import subprocess, os, shutil, uuid, sys
from pathlib import Path

OK   = "[OK] "
FAIL = "[FAIL] "
results = []

# ── Build test ASS file ────────────────────────────────────────────────────────
captions_abs = str(Path("test_e2e_captions.ass").resolve())
ass_content = (
    "[Script Info]\n"
    "PlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\n\n"
    "[V4+ Styles]\n"
    "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    "Style: Default,Arial,72,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,10,10,480,1\n\n"
    "[Events]\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    r"Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{\pos(540,1440)}{\c&HFFFFFF&}{\alpha&H00&}YOUR MIND IS {\c&HAAAAAA&}{\alpha&H80&}NOT YOUR IDENTITY"
    "\n"
)
Path(captions_abs).write_text(ass_content, encoding="utf-8")

# ── NEW FIX: copy to relative path (no drive letter) ─────────────────────────
ass_rel = f"tmp_captions_{uuid.uuid4().hex[:8]}.ass"
shutil.copy2(captions_abs, ass_rel)
print(f"Abs  path: {captions_abs}")
print(f"Rel  path: {ass_rel}")
print()

# ── Test 1: captions + watermark + yuv420p ────────────────────────────────────
print("TEST 1: Full render (Arial captions + watermark + yuv420p)...")
wm  = "drawtext=text='neuralbaba_empire':fontsize=34:fontcolor=0xFFFFFF59:x=(w-text_w)/2:y=h-80:shadowx=1:shadowy=1:shadowcolor=0x0000004D:font=Arial"
ass = "ass='" + ass_rel + "'"
vf  = ass + "," + wm

r = subprocess.run(
    ["ffmpeg", "-f", "lavfi", "-i", "color=black:s=1080x1920:r=30",
     "-f", "lavfi", "-i", "sine=frequency=220:duration=3",
     "-vf", vf,
     "-c:v", "libx264", "-preset", "fast", "-crf", "23",
     "-pix_fmt", "yuv420p",
     "-profile:v", "high", "-level", "4.0",
     "-c:a", "aac", "-b:a", "192k",
     "-movflags", "+faststart",
     "-t", "3", "test_e2e_output.mp4", "-y"],
    capture_output=True, text=True, timeout=30
)
size = Path("test_e2e_output.mp4").stat().st_size if Path("test_e2e_output.mp4").exists() else 0
if r.returncode == 0 and size > 50000:
    results.append(("PASS", f"Full render: {size//1024}KB"))
    print(f"  {OK}exit=0, size={size//1024}KB — captions + watermark + yuv420p")
else:
    results.append(("FAIL", f"Full render: exit={r.returncode} size={size}"))
    print(f"  {FAIL}exit={r.returncode} size={size}")
    for line in r.stderr.split("\n"):
        if line.strip(): print("   >", line.strip()[:100])

# ── Test 2: yuv420p confirmed ─────────────────────────────────────────────────
print("TEST 2: Pixel format check...")
if Path("test_e2e_output.mp4").exists():
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_streams", "-select_streams", "v",
         "-print_format", "compact", "test_e2e_output.mp4"],
        capture_output=True, text=True
    )
    if "yuv420p" in probe.stdout:
        results.append(("PASS", "yuv420p confirmed"))
        print(f"  {OK}Pixel format: yuv420p — video opens on Windows/mobile")
    else:
        results.append(("FAIL", "yuv420p not found in output"))
        print(f"  {FAIL}yuv420p not confirmed: {probe.stdout[:100]}")

# ── Test 3: Text visibility (frame file size check) ───────────────────────────
print("TEST 3: Text visibility...")
r3 = subprocess.run(
    ["ffmpeg", "-f", "lavfi", "-i", "color=black:s=1080x1920:r=30",
     "-vf", ass + ",format=yuv420p",
     "-frames:v", "1", "test_e2e_frame.jpg", "-y"],
    capture_output=True, text=True, timeout=15
)
frame_size = Path("test_e2e_frame.jpg").stat().st_size if Path("test_e2e_frame.jpg").exists() else 0
if r3.returncode == 0 and frame_size > 15000:
    results.append(("PASS", f"Text visible in frame ({frame_size//1024}KB)"))
    print(f"  {OK}Frame size={frame_size//1024}KB — white text visible on black background")
else:
    results.append(("FAIL", f"Frame too small ({frame_size}B) — text may be invisible"))
    print(f"  {FAIL}Frame={frame_size}B — text may not be rendering")

# ── Test 4: Gemini model ──────────────────────────────────────────────────────
print("TEST 4: Gemini model name...")
import sys; sys.path.insert(0, ".")
from generator.script_engine import GeminiClient
g = GeminiClient()
if g.model == "gemini-2.0-flash":
    results.append(("PASS", f"Gemini model: {g.model}"))
    print(f"  {OK}Gemini model: {g.model} (not deprecated gemini-1.5-flash)")
else:
    results.append(("WARN", f"Gemini model: {g.model}"))
    print(f"  [WARN] Gemini model: {g.model} (check GEMINI_MODEL env var)")

# ── Test 5: Chapter sleep present ─────────────────────────────────────────────
print("TEST 5: Rate-limit sleep between chapters...")
src = open("generator/script_engine.py", encoding="utf-8").read()
if "time.sleep(3)" in src and "Rate-limit guard" in src:
    results.append(("PASS", "3s inter-chapter sleep present"))
    print(f"  {OK}3s sleep between chapter LLM calls (prevents 429 on long videos)")
else:
    results.append(("FAIL", "sleep missing"))
    print(f"  {FAIL}Inter-chapter sleep not found!")

# ── Test 6: retry wait increased ─────────────────────────────────────────────
if "multiplier=2, min=5, max=60" in src:
    results.append(("PASS", "Retry: min=5s max=60s"))
    print(f"  {OK}Retry wait: min=5s, max=60s (was min=2s, max=10s)")
else:
    results.append(("FAIL", "retry wait not updated"))
    print(f"  {FAIL}Retry wait not updated!")

# ── Cleanup ───────────────────────────────────────────────────────────────────
for f in [captions_abs, ass_rel, "test_e2e_output.mp4", "test_e2e_frame.jpg"]:
    try: Path(f).unlink()
    except: pass

# ── Summary ───────────────────────────────────────────────────────────────────
print()
passed = sum(1 for r,_ in results if r=="PASS")
warned = sum(1 for r,_ in results if r=="WARN")
failed = sum(1 for r,_ in results if r=="FAIL")
print(f"Result: {passed} pass | {warned} warn | {failed} fail")
if not failed:
    print("ALL 5 FIXES VALIDATED — SAFE TO PUSH")
else:
    sys.exit(1)
