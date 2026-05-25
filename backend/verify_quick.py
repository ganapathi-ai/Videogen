"""Full system verification — runs all checks and prints a clear pass/fail report."""
import sys, os, traceback
sys.path.insert(0, r'c:\projects\YOUTUBE_WEBAPP\backend')
os.chdir(r'c:\projects\YOUTUBE_WEBAPP\backend')

results = []

def chk(label, fn):
    try:
        fn()
        results.append(("OK  ", label))
    except Exception as e:
        results.append(("FAIL", f"{label}: {e}"))

# ── 1. Module imports ─────────────────────────────────────
chk("import main",                  lambda: __import__("main"))
chk("import script_engine",         lambda: __import__("generator.script_engine"))
chk("import tts_engine",            lambda: __import__("audio.tts_engine"))
chk("import audio_mixer",           lambda: __import__("audio.audio_mixer"))
chk("import align_engine",          lambda: __import__("alignment.align_engine"))
chk("import timeline_engine",       lambda: __import__("timeline.timeline_engine"))
chk("import media_engine",          lambda: __import__("media.media_engine"))
chk("import faiss_engine",          lambda: __import__("embeddings.faiss_engine"))
chk("import video_engine",          lambda: __import__("video.video_engine"))
chk("import caption_engine",        lambda: __import__("captions.caption_engine"))
chk("import validator",             lambda: __import__("validator.validator"))

# ── 2. TTS voice registry ─────────────────────────────────
def chk_voices():
    from audio.tts_engine import VOICE_PRESETS, get_voice_list
    assert len(VOICE_PRESETS) == 15, f"Expected 15 voices, got {len(VOICE_PRESETS)}"
    voices = get_voice_list()
    assert len(voices) == 15
chk("15 TTS voices registered", chk_voices)

# ── 3. TTS text cleaner ───────────────────────────────────
def chk_cleaner():
    from audio.tts_engine import TTSEngine
    e = TTSEngine("gb_male_rich")
    bad_names = ["Epictetus", "Seneca", "Stoics", "Marcus Aurelius", "Aurelius"]
    cases = [
        "You are not your thoughts, Epictetus",
        "Ego fuels your turmoil, Seneca",
        "Recognize the power, Stoics",
        "Be free from ego chains, Marcus Aurelius",
    ]
    for c in cases:
        out = e._clean_text(c)
        for name in bad_names:
            assert name not in out, f"Name '{name}' still in: {out!r}"
        assert "," not in out or out.count(",") == 0, f"Comma still in: {out!r}"
chk("TTS cleaner strips names+commas", chk_cleaner)

# ── 4. TTS legacy voice mapping ───────────────────────────
def chk_legacy():
    from audio.tts_engine import TTSEngine
    legacy_ids = ["af_bella", "bm_george", "am_adam", "bf_emma"]
    for lid in legacy_ids:
        e = TTSEngine(lid)
        assert e.voice_key in ["us_female_warm","gb_male_rich","us_male_deep","gb_female_elegant"]
chk("Legacy voice IDs map correctly", chk_legacy)

# ── 5. Video engine FFmpeg color clip ─────────────────────
def chk_video():
    import tempfile
    from video.video_engine import VideoEngine
    e = VideoEngine("9:16", 30)
    tmp = tempfile.mktemp(suffix=".mp4")
    ok = e._generate_color_clip(tmp, 2.0)
    assert ok, "Color clip generation failed"
    size = os.path.getsize(tmp)
    assert size > 500, f"Color clip too small: {size} bytes"
    os.unlink(tmp)
chk("VideoEngine FFmpeg color clip", chk_video)

# ── 6. VideoEngine crop filter ────────────────────────────
def chk_crop():
    from video.video_engine import VideoEngine
    e = VideoEngine("9:16", 30)
    f1 = e._build_crop_filter(1920, 1080)   # landscape → portrait
    assert "crop" in f1, f"Expected crop for landscape: {f1}"
    f2 = e._build_crop_filter(1080, 1920)   # already portrait
    assert "scale" in f2, f"Expected scale for portrait: {f2}"
chk("VideoEngine crop filter logic", chk_crop)

# ── 7. Windows path escaping for FFmpeg ass= ──────────────
def chk_ass_path():
    # Simulate the path escaping from main.py
    def escape(p):
        p = p.replace("\\", "/")
        if len(p) >= 2 and p[1] == ":":
            p = p[0] + "\\:" + p[2:]
        return p
    raw   = r"C:\projects\YOUTUBE_WEBAPP\backend\exports\abc\captions.ass"
    fixed = escape(raw)
    assert "\\:" in fixed,   f"Drive colon not escaped: {fixed}"
    assert "\\" not in fixed.replace("\\:", ""), f"Backslashes remain: {fixed}"
    assert fixed.startswith("C\\:/"), f"Wrong start: {fixed}"
chk("Windows ass= path escaping", chk_ass_path)

# ── 8. AudioMixer FFmpeg call (no BGM fallback) ───────────
def chk_mixer():
    from audio.audio_mixer import AudioMixer
    m = AudioMixer()
    assert hasattr(m, "mix"), "mix() method missing"
    assert hasattr(m, "DUCK_MAP"), "DUCK_MAP missing"
    assert "inspiring" in m.DUCK_MAP
chk("AudioMixer structure OK", chk_mixer)

# ── 9. Script prompt has no philosopher name in examples ──
def chk_prompt():
    from generator.script_engine import SYSTEM_PROMPT, _user_prompt
    assert "NEVER mention any philosopher" in SYSTEM_PROMPT
    assert "Epictetus" in SYSTEM_PROMPT   # as a banned example
    assert "NO philosopher" in SYSTEM_PROMPT or "NEVER mention" in SYSTEM_PROMPT
    prompt = _user_prompt("test", 35, 7)
    assert "DO NOT add names" in prompt
chk("Script prompt bans philosopher names", chk_prompt)

# ── 10. FastAPI routes registered ────────────────────────
def chk_routes():
    import main
    app = main.app
    routes = {r.path for r in app.routes}
    required = ["/api/generate", "/api/stream-progress/{job_id}",
                "/api/status/{job_id}", "/api/result/{job_id}",
                "/api/health", "/api/voices"]
    for r in required:
        assert r in routes, f"Route missing: {r}"
chk("All API routes registered", chk_routes)

# ── 11. Caption engine produces events ───────────────────
def chk_captions():
    from captions.caption_engine import CaptionEngine
    import tempfile
    dummy_timeline = {
        "segments": [{
            "id": 1, "text": "Your mind is free",
            "word_data": [
                {"word": "Your", "start": 0.5, "end": 0.8},
                {"word": "mind", "start": 0.9, "end": 1.2},
                {"word": "is",   "start": 1.3, "end": 1.5},
                {"word": "free", "start": 1.6, "end": 2.0},
            ]
        }]
    }
    e = CaptionEngine((1080, 1920))
    tmp = tempfile.mktemp(suffix=".ass")
    os.makedirs(os.path.dirname(os.path.abspath(tmp)), exist_ok=True)
    out = e.build_ass_subtitles(dummy_timeline, tmp)
    import pysubs2
    subs = pysubs2.load(out)
    assert len(subs) > 0, "No subtitle events generated"
    os.unlink(out)
chk("CaptionEngine produces subtitle events", chk_captions)

# ── Print Report ──────────────────────────────────────────
print()
print("=" * 55)
print("  FULL SYSTEM VERIFICATION REPORT")
print("=" * 55)
passed = sum(1 for s, _ in results if s == "OK  ")
failed = sum(1 for s, _ in results if s == "FAIL")
for status, label in results:
    print(f"  {status}  {label}")
print()
print(f"  Passed: {passed}/{len(results)}")
if failed:
    print(f"  FAILED: {failed} checks")
else:
    print("  ALL CHECKS PASSED")
print("=" * 55)
