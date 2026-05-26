"""Comprehensive caption fix validation — font rendering + path escaping on Windows."""
import subprocess, os
from pathlib import Path

PASS = "[OK ] "
FAIL = "[FAIL] "

results = []
def ok(msg):  results.append(("PASS", msg)); print(f"  {PASS}{msg}")
def fail(msg): results.append(("FAIL", msg)); print(f"  {FAIL}{msg}")

# ── Test correct fonts with FULL resolution ────────────────────────────────────
print("Test 1: Full 1080x1920 ASS render — checking each font for ACTUAL visible text")
RESOLUTION = "1080x1920"

for font in ["Impact", "Arial Bold", "Arial", "Calibri", "Trebuchet MS"]:
    ass = f"""[Script Info]
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},88,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,2,2,10,10,480,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{{\\pos(540,1440)}}YOUR MIND IS NOT YOUR IDENTITY
"""
    safe_font = font.replace(" ", "_")
    ass_path = f"test_font_{safe_font}.ass"
    out_path = f"test_font_{safe_font}.jpg"
    Path(ass_path).write_text(ass, encoding="utf-8")

    vf = "ass='" + ass_path + "'"
    r = subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", f"color=black:s={RESOLUTION}:r=30",
         "-vf", vf, "-frames:v", "1", out_path, "-y"],
        capture_output=True, text=True, timeout=20
    )
    size = Path(out_path).stat().st_size if Path(out_path).exists() else 0
    # A frame with visible white text on black is significantly larger than pure black (> 15KB for 1080x1920)
    if r.returncode == 0 and size > 15000:
        ok(f"font='{font}': size={size//1024}KB — TEXT IS VISIBLE")
    elif r.returncode == 0 and size > 5000:
        print(f"  [??] font='{font}': size={size//1024}KB — uncertain (check manually)")
    else:
        fail(f"font='{font}': size={size}B — TEXT NOT VISIBLE (probably not installed or missing)")
    for f_ in [ass_path]:
        try: os.unlink(f_)
        except: pass

# ── Test 2: ASS path escaping strategies on this machine ─────────────────────
print()
print("Test 2: ASS path escaping strategies")
abs_path = r"c:\projects\YOUTUBE_WEBAPP\backend\exports\test\captions.ass"

strategies = {
    "forward-slash only":           abs_path.replace("\\", "/"),
    "colon backslash-escaped":      abs_path.replace("\\", "/").replace(":", "\\:"),
    "double-colon (alternative)":   abs_path.replace("\\", "/").replace(":", "::"),
}

# Create a real ASS file at a known path to test with
test_ass_content = """[Script Info]
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,88,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,2,2,10,10,480,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{\\pos(540,1440)}PATH TEST OK
"""
# Use a relative path (no drive letter) — avoids Windows colon issue entirely
rel_ass = "test_path_escape.ass"
Path(rel_ass).write_text(test_ass_content, encoding="utf-8")
abs_ass = str(Path(rel_ass).resolve())

for name, escaped in strategies.items():
    escaped_for_rel = rel_ass  # relative path has no colon — always works
    vf = "ass='" + escaped + "'"
    r = subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "color=black:s=1080x1920:r=30",
         "-vf", vf, "-frames:v", "1", "test_path_out.jpg", "-y"],
        capture_output=True, text=True, timeout=15
    )
    size = Path("test_path_out.jpg").stat().st_size if Path("test_path_out.jpg").exists() else 0
    status = PASS if (r.returncode == 0 and size > 5000) else FAIL
    print(f"  {status}Strategy '{name}': exit={r.returncode} size={size}B")
    if r.returncode != 0:
        for line in r.stderr.split("\n"):
            if "error" in line.lower() or "invalid" in line.lower() or "no such" in line.lower():
                print(f"    -> {line.strip()[:80]}")

# cleanup
for f in list(Path(".").glob("test_*.jpg")) + list(Path(".").glob("test_path*.ass")):
    try: f.unlink()
    except: pass

# ── Summary ───────────────────────────────────────────────────────────────────
passed = sum(1 for r,_ in results if r=="PASS")
failed = sum(1 for r,_ in results if r=="FAIL")
print()
print(f"Result: {passed} passing, {failed} failing")
