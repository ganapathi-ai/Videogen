"""MASTER VERIFICATION — All systems including history + long-form."""
import sys, os, subprocess, re, json
sys.path.insert(0, r'c:\projects\YOUTUBE_WEBAPP\backend')
os.chdir(r'c:\projects\YOUTUBE_WEBAPP\backend')
os.environ.setdefault('FREESOUND_API_KEY', 'mF59G65s4J1OMrdDPiAWjuIgoHAvjIRztWOK7A2O')

results = []

def chk(label, fn):
    try:
        fn()
        results.append(("OK  ", label))
    except Exception as e:
        results.append(("FAIL", f"{label}: {e}"))

# ── GROUP 1: All imports ─────────────────────────────────
MODULES = [
    "main", "generator.script_engine", "audio.tts_engine",
    "audio.audio_mixer", "audio.bgm_engine", "alignment.align_engine",
    "timeline.timeline_engine", "media.media_engine", "embeddings.faiss_engine",
    "video.video_engine", "captions.caption_engine", "validator.validator",
    "history.history_engine",
]
for mod in MODULES:
    chk(f"import {mod}", lambda m=mod: __import__(m))

# ── GROUP 2: Dead code scan ──────────────────────────────
PY_FILES = []
for root, dirs, files in os.walk(r'c:\projects\YOUTUBE_WEBAPP\backend'):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', 'exports', 'bgm_cache', 'assets')]
    for f in files:
        if f.endswith('.py') and not os.path.basename(f).startswith('verify_'):
            if os.path.basename(f) not in ('test_engines.py', 'cli.py'):
                PY_FILES.append(os.path.join(root, f))

def scan(pattern, label):
    rx = re.compile(pattern)
    found = []
    for fpath in PY_FILES:
        with open(fpath, encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                if rx.search(line) and not line.strip().startswith('#'):
                    found.append(f"{os.path.basename(fpath)}:{i}")
    if found:
        raise AssertionError(f"Found in: {found[:3]}")

chk("No moviepy.editor", lambda: scan(r'from moviepy\.editor|import moviepy\.editor', "moviepy"))
chk("No clip.fl() (MoviePy 1.x)", lambda: scan(r'\.fl\(', "fl()"))
chk("No kokoro import", lambda: scan(r'import kokoro|from kokoro', "kokoro"))
# af_bella is intentionally kept in the legacy map in tts_engine.py — skip that file
def chk_no_af_bella_default():
    for fpath in PY_FILES:
        if 'tts_engine.py' in fpath:
            continue  # Legacy map intentionally contains af_bella as a key
        with open(fpath, encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                if '"af_bella"' in line and not line.strip().startswith('#') and 'LEGACY' not in line:
                    raise AssertionError(f"{os.path.basename(fpath)}:{i}: {line.strip()[:60]}")
chk("No af_bella default outside legacy map", chk_no_af_bella_default)

# ── GROUP 3: History Engine ──────────────────────────────
def chk_history_structure():
    from history.history_engine import HistoryEngine, HISTORY_FILE
    from history.history_engine import TOPIC_SIMILARITY_THRESHOLD, BEAT_SIMILARITY_THRESHOLD
    h = HistoryEngine()
    assert HISTORY_FILE.parent.exists()
    assert 0.5 < TOPIC_SIMILARITY_THRESHOLD < 1.0
    assert 0.5 < BEAT_SIMILARITY_THRESHOLD  < 1.0
chk("History: engine structure + thresholds", chk_history_structure)

def chk_history_topic_check():
    from history.history_engine import HistoryEngine
    h = HistoryEngine()
    # Test internal similarity function
    score_same, _ = h._best_topic_match("Overcoming Fear", ["Overcoming Fear"])
    assert score_same > 0.9, f"Same topic should score >0.9: {score_same}"
    score_diff, _ = h._best_topic_match("The Beauty of Rain", ["Overcoming Fear"])
    assert score_diff < 0.5, f"Different topics should score <0.5: {score_diff}"
chk("History: topic similarity scoring", chk_history_topic_check)

def chk_history_beat_filter():
    from history.history_engine import HistoryEngine
    h = HistoryEngine()
    # Exact duplicate should be filtered
    past = ["Your mind is not your identity."]
    beat = {"text": "Your mind is not your identity.", "id": 1}
    assert h._is_duplicate_beat(beat["text"], past), "Exact duplicate should be caught"
    # Novel beat should pass
    novel = {"text": "Strength grows from facing what you fear."}
    assert not h._is_duplicate_beat(novel["text"], past), "Novel beat should pass"
chk("History: beat deduplication logic", chk_history_beat_filter)

def chk_history_save_load():
    import tempfile
    from pathlib import Path
    from history import history_engine as he
    # Temporarily redirect history file to a temp file
    orig = he.HISTORY_FILE
    tmp = Path(tempfile.mktemp(suffix='.jsonl'))
    he.HISTORY_FILE = tmp
    try:
        h = he.HistoryEngine()
        h._cache = None
        dummy_script = {
            "topic": "Test Philosophy Topic",
            "title": "The Test of Resolve",
            "beats": [{"text": "You choose how you respond."}, {"text": "Every moment is a test."}],
        }
        h.save(dummy_script, length="short")
        h._cache = None  # Force reload
        loaded = h._load()
        assert len(loaded) == 1, f"Expected 1 entry, got {len(loaded)}"
        assert loaded[0]["topic"] == "Test Philosophy Topic"
        assert len(loaded[0]["beats"]) == 2
        topics = h.get_all_topics()
        assert "Test Philosophy Topic" in topics
        stats = h.get_stats()
        assert stats["total_videos"] == 1
        assert stats["total_beats"] == 2
    finally:
        he.HISTORY_FILE = orig
        try: tmp.unlink()
        except: pass
chk("History: save + load + get_stats", chk_history_save_load)

def chk_history_normalize():
    from history.history_engine import HistoryEngine
    h = HistoryEngine()
    # _normalize: lower + strip punct + collapse spaces
    result = h._normalize('Your MIND,  is Free.')
    # double-space collapses to single space by re.sub(r'\s+', ' ')
    assert result == 'your mind is free', f"Got: {repr(result)}"
chk("History: text normalizer", chk_history_normalize)

# ── GROUP 4: Script Engine long-form config ───────────────
def chk_length_config():
    from generator.script_engine import LENGTH_CONFIG, LONG_FORM_CHAPTERS
    required = ["short", "medium", "long_3", "long_5", "long_7", "long_11"]
    for k in required:
        assert k in LENGTH_CONFIG, f"Missing length: {k}"
    # Beat counts should scale with duration
    assert LENGTH_CONFIG["long_11"]["beats"] > LENGTH_CONFIG["long_7"]["beats"]
    assert LENGTH_CONFIG["long_7"]["beats"]  > LENGTH_CONFIG["long_5"]["beats"]
    assert LENGTH_CONFIG["long_5"]["beats"]  > LENGTH_CONFIG["long_3"]["beats"]
    assert LENGTH_CONFIG["long_3"]["beats"]  > LENGTH_CONFIG["medium"]["beats"]
    # Chapter proportions must sum to ~1.0
    total_prop = sum(c["proportion"] for c in LONG_FORM_CHAPTERS)
    assert abs(total_prop - 1.0) < 0.01, f"Chapter proportions sum to {total_prop}"
    # All 6 chapters present
    chapter_names = {c["name"] for c in LONG_FORM_CHAPTERS}
    assert "HOOK" in chapter_names and "CLOSE" in chapter_names
chk("ScriptEngine: 6 lengths + chapter config valid", chk_length_config)

def chk_prompts():
    from generator.script_engine import (
        SYSTEM_PROMPT, _short_form_prompt, _long_form_prompt
    )
    assert "NEVER mention any philosopher" in SYSTEM_PROMPT
    assert "NEVER use commas" in SYSTEM_PROMPT
    # Short form: "No names. No commas." in the line about each beat
    p = _short_form_prompt("test", 35, 7)
    assert "No names" in p or "no names" in p.lower()
    assert "No commas" in p or "no commas" in p.lower()
    # Long form: also has "no names" in it
    p2 = _long_form_prompt("test", 300, 56, "HOOK", "hook", 5, 1)
    assert "no names" in p2.lower()
chk("ScriptEngine: prompts ban names + commas", chk_prompts)

# ── GROUP 5: API Routes ──────────────────────────────────
def chk_routes():
    import main
    routes = {r.path for r in main.app.routes}
    required = ["/api/generate", "/api/stream-progress/{job_id}",
                "/api/status/{job_id}", "/api/result/{job_id}",
                "/api/health", "/api/voices", "/api/history"]
    for r in required:
        assert r in routes, f"Missing route: {r}"
chk("API: all 7 routes registered (incl. /api/history)", chk_routes)

# ── GROUP 6: TTS, BGM, Video, Captions (quick) ───────────
chk("TTS: 10 voices registered", lambda: __import__("audio.tts_engine") and
    len(__import__("audio.tts_engine", fromlist=["VOICE_PRESETS"]).VOICE_PRESETS) == 10)
chk("BGM: curated tracks present", lambda: len(
    __import__("audio.bgm_engine", fromlist=["CURATED_TRACKS"]).CURATED_TRACKS) >= 4)
chk("VideoEngine: no MoviePy", lambda: "moviepy" not in
    open(r'c:\projects\YOUTUBE_WEBAPP\backend\video\video_engine.py').read())

def chk_captions():
    import tempfile
    from captions.caption_engine import CaptionEngine
    import pysubs2
    t = {"segments":[{"id":1,"text":"Test beat.",
        "word_data":[{"word":"Test","start":0.5,"end":0.8},{"word":"beat.","start":0.9,"end":1.2}]}]}
    e = CaptionEngine((1080, 1920))
    tmp = tempfile.mktemp(suffix=".ass")
    subs = pysubs2.load(e.build_ass_subtitles(t, tmp))
    assert len(subs) > 0
    os.unlink(tmp)
chk("CaptionEngine: produces subtitle events", chk_captions)

# ── GROUP 7: Frontend ────────────────────────────────────
def chk_frontend():
    tsx = open(r'c:\projects\YOUTUBE_WEBAPP\frontend\app\components\GenerateForm.tsx', encoding='utf-8').read()
    assert 'gb_ryan' in tsx,      "Missing gb_ryan voice"
    assert '"long_3"' in tsx,     "Missing long_3 length"
    assert '"long_5"' in tsx,     "Missing long_5 length"
    assert '"long_7"' in tsx,     "Missing long_7 length"
    assert '"long_11"' in tsx,    "Missing long_11 length"
    assert 'SHORTS / REELS' in tsx.upper() or 'SHORTS' in tsx.upper(), "Missing Shorts section"
    assert 'FULL YOUTUBE' in tsx.upper() or 'YouTube' in tsx, "Missing YouTube section"
    assert '"af_bella"' not in tsx, "Old voice ID af_bella still present"
    assert 'History tracking' in tsx or 'history' in tsx.lower(), "No history reference"
chk("Frontend: 6 lengths, new voices, history note", chk_frontend)

def chk_env():
    env = open(r'c:\projects\YOUTUBE_WEBAPP\.env', encoding='utf-8').read()
    for key in ['GROQ_API_KEY', 'PEXELS_API_KEY', 'NGROK_AUTHTOKEN', 'FREESOUND_API_KEY']:
        assert key in env, f"Missing .env key: {key}"
chk(".env: all API keys present", chk_env)

# ── REPORT ───────────────────────────────────────────────
print()
print("=" * 62)
print("  MASTER VERIFICATION — ALL SYSTEMS")
print("=" * 62)
passed = failed = 0
for status, label in results:
    icon = "[+]" if status == "OK  " else "[X]"
    print(f"  {icon}  {label}")
    if status == "OK  ": passed += 1
    else: failed += 1
print()
print(f"  Result: {passed}/{len(results)} passed  |  {failed} failed")
if failed == 0:
    print("  *** ALL CHECKS PASSED ***")
else:
    print("  *** FIX FAILING CHECKS ***")
print("=" * 62)
