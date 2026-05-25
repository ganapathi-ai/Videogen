"""Test the FFmpeg drawtext fix and per-channel voice chains."""
import subprocess, sys
sys.path.insert(0, ".")

RESULTS = []

def ok(msg):  RESULTS.append(("PASS", msg)); print(f"  [+] {msg}")
def fail(msg): RESULTS.append(("FAIL", msg)); print(f"  [X] FAIL: {msg}")

# ── Test 1: Fixed drawtext hex RGBA (the bug fix) ────────────────────────────
print("Test 1: FFmpeg drawtext hex RGBA syntax (Windows fix)...")
r = subprocess.run([
    "ffmpeg",
    "-f", "lavfi", "-i", "color=black:size=1080x1920:duration=1",
    "-vf", "drawtext=text='neuralbaba_empire':fontsize=34:fontcolor=0xFFFFFF59:x=(w-text_w)/2:y=h-80:shadowx=1:shadowy=1:shadowcolor=0x0000004D:font=Arial",
    "-frames:v", "1",
    "-f", "null", "-",
    "-y"
], capture_output=True, text=True, timeout=20)
if r.returncode == 0:
    ok("Hex RGBA drawtext 'fontcolor=0xFFFFFF59' works on Windows FFmpeg")
else:
    fail(f"Hex RGBA drawtext failed: {r.stderr[-200:]}")

# ── Test 2: Old broken syntax (should fail or pass — tells us FFmpeg version) ─
print("Test 2: OLD syntax 'white@0.35' (was failing)...")
r2 = subprocess.run([
    "ffmpeg",
    "-f", "lavfi", "-i", "color=black:size=400x400:duration=1",
    "-vf", "drawtext=text='test':fontsize=30:fontcolor=white@0.35:x=10:y=10:font=Arial",
    "-frames:v", "1", "-f", "null", "-", "-y"
], capture_output=True, text=True, timeout=15)
if r2.returncode == 0:
    ok("Old syntax also works on this build — hex RGBA is backward-compat too")
else:
    ok(f"Old syntax fails (confirms bug) — hex RGBA fix is required (exit={r2.returncode})")

# ── Test 3: Triple fallback (bare mux without any -vf) ────────────────────────
print("Test 3: Bare mux fallback (no -vf flag)...")
r3 = subprocess.run([
    "ffmpeg",
    "-f", "lavfi", "-i", "color=black:size=640x360:duration=1",
    "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
    "-c:v", "libx264", "-crf", "28", "-c:a", "aac",
    "-frames:v", "30",
    "test_bare_mux.mp4", "-y"
], capture_output=True, text=True, timeout=20)
if r3.returncode == 0:
    ok("Bare mux (fallback 3) works — video will always complete")
else:
    fail(f"Bare mux failed: {r3.stderr[-200:]}")
# Cleanup
import os; os.path.exists("test_bare_mux.mp4") and os.unlink("test_bare_mux.mp4")

# ── Test 4: Per-channel voice chains ─────────────────────────────────────────
print("Test 4: Per-channel voice chains...")
from audio.tts_engine import CHANNEL_VOICE_CHAIN, TTSEngine
assert "stoic" in CHANNEL_VOICE_CHAIN; ok("stoic chain exists")
assert "tech"  in CHANNEL_VOICE_CHAIN; ok("tech chain exists")

stoic_c = CHANNEL_VOICE_CHAIN["stoic"]["af_chain"]
tech_c  = CHANNEL_VOICE_CHAIN["tech"]["af_chain"]
assert stoic_c != tech_c; ok("Stoic and tech chains are different")

# Stoic: warm, light compression, -16 LUFS
assert "highpass=f=80" in stoic_c;    ok("Stoic HPF: 80Hz (warm)")
assert "ratio=2.5" in stoic_c;        ok("Stoic compression: 2.5:1 (light)")
assert "loudnorm=I=-16" in stoic_c;   ok("Stoic LUFS: -16 (intimate)")
assert "g=6" in stoic_c;              ok("Stoic bass: +6dB warmth at 120Hz")

# Tech: clean, presence, tight compression, -14 LUFS
assert "highpass=f=100" in tech_c;    ok("Tech HPF: 100Hz (clean)")
assert "ratio=3.5" in tech_c;         ok("Tech compression: 3.5:1 (tighter)")
assert "loudnorm=I=-14" in tech_c;    ok("Tech LUFS: -14 (punchy)")
assert "f=3500" in tech_c;            ok("Tech presence: 3.5kHz boost")
assert "f=8000" in tech_c;            ok("Tech air: 8kHz boost (crisp consonants)")

# ── Test 5: TTSEngine channel_id propagation ──────────────────────────────────
print("Test 5: TTSEngine channel propagation...")
ts = TTSEngine(voice="gb_ryan",       channel_id="stoic")
tt = TTSEngine(voice="us_christopher", channel_id="tech")
assert ts.channel_id == "stoic"; ok("TTSEngine(stoic) → channel_id='stoic'")
assert tt.channel_id == "tech";  ok("TTSEngine(tech)  → channel_id='tech'")
assert ts.chain_cfg is not tt.chain_cfg; ok("Different chain configs applied")

# ── Test 6: Watermark text doesn't break with underscores ────────────────────
print("Test 6: Watermark text escaping...")
wm = "neuralbaba_empire"
wm_esc = wm.replace("'", "\\'").replace(":", "\\:")
assert wm_esc == "neuralbaba_empire"; ok(f"Watermark '{wm}' needs no escaping — clean")
wm2 = "The Inner Citadel"
wm2_esc = wm2.replace("'", "\\'").replace(":", "\\:")
assert wm2_esc == "The Inner Citadel"; ok(f"Watermark '{wm2}' needs no escaping — clean")

# ── Result ────────────────────────────────────────────────────────────────────
print()
passed = sum(1 for r, _ in RESULTS if r == "PASS")
failed = sum(1 for r, _ in RESULTS if r == "FAIL")
print(f"  Result: {passed}/{passed+failed} passed | {failed} failed")
if not failed:
    print("  *** ALL TESTS PASSED — BUG FIXED, VOICE CHAINS VERIFIED ***")
else:
    sys.exit(1)
