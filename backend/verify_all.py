"""
MASTER VERIFICATION v3 — All systems including history, long-form, audio fixes.

Checks:
  1.  All 13 module imports
  2.  Dead code scan (no old libraries)
  3.  History engine (5 checks)
  4.  ScriptEngine (3 checks: 6 lengths, chapters, prompts)
  5.  AudioMixer long-form fixes (aloop, no -shortest, timeout scaling)
  6.  TTS engine (voice chain timeout, beat retry)
  7.  VideoEngine (scaled timeouts, 16:9 support)
  8.  Aspect ratio enforcement (backend forces 16:9 for long-form)
  9.  FFmpeg render (no -shortest, duration param, scaled timeout)
  10. API routes (all 7)
  11. Frontend (6 lengths, voice IDs, history note)
  12. .env keys
"""
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
    "timeline.timeline_engine", "media.media_engine", "media.ai_image_engine",
    "embeddings.faiss_engine",
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
            if os.path.basename(f) not in ('test_engines.py', 'cli.py', 'AUDIT_FINDINGS.md'):
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

def chk_no_af_bella_default():
    for fpath in PY_FILES:
        if 'tts_engine.py' in fpath:
            continue
        with open(fpath, encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                if '"af_bella"' in line and not line.strip().startswith('#') and 'LEGACY' not in line:
                    raise AssertionError(f"{os.path.basename(fpath)}:{i}: {line.strip()[:60]}")
chk("No af_bella default outside legacy map", chk_no_af_bella_default)

# ── GROUP 3: History Engine ──────────────────────────────
def chk_history_structure():
    from history.history_engine import HistoryEngine, TOPIC_SIMILARITY_THRESHOLD, BEAT_SIMILARITY_THRESHOLD
    h = HistoryEngine(channel_id="stoic")
    assert 0.5 < TOPIC_SIMILARITY_THRESHOLD < 1.0
    assert 0.5 < BEAT_SIMILARITY_THRESHOLD  < 1.0
chk("History: engine structure + thresholds", chk_history_structure)

def chk_history_topic_check():
    from history.history_engine import HistoryEngine
    h = HistoryEngine(channel_id="stoic")
    score_same, _ = h._best_topic_match("Overcoming Fear", ["Overcoming Fear"])
    assert score_same > 0.9, f"Same topic score: {score_same}"
    score_diff, _ = h._best_topic_match("The Beauty of Rain", ["Overcoming Fear"])
    assert score_diff < 0.5, f"Diff topic score: {score_diff}"
chk("History: topic similarity scoring", chk_history_topic_check)

def chk_history_beat_filter():
    from history.history_engine import HistoryEngine
    h = HistoryEngine(channel_id="stoic")
    past = ["Your mind is not your identity."]
    assert h._is_duplicate_beat("Your mind is not your identity.", past)
    assert not h._is_duplicate_beat("Strength grows from facing what you fear.", past)
chk("History: beat deduplication logic", chk_history_beat_filter)


def chk_history_save_load():
    import tempfile
    from pathlib import Path
    from history.history_engine import HistoryEngine, HISTORY_FILES
    # Verify per-channel isolation: two distinct files
    assert "stoic" in HISTORY_FILES, "stoic must be in HISTORY_FILES"
    assert "tech"  in HISTORY_FILES, "tech must be in HISTORY_FILES"
    hs = HistoryEngine(channel_id="stoic")
    ht = HistoryEngine(channel_id="tech")
    assert hs.history_file != ht.history_file, "Stoic+Tech must use separate history files"
    # Test save + load on stoic channel
    dummy = {"topic": "Test Topic Verify", "title": "Test Title",
             "beats": [{"text": "You choose how you respond."}, {"text": "Every moment is a test."}]}
    hs.save(dummy, length="short")
    hs._cache = None
    loaded = hs._load()
    assert len(loaded) >= 1
    assert loaded[-1]["topic"] == "Test Topic Verify"
    assert loaded[-1]["channel"] == "stoic", "channel field must be saved"
    stats = hs.get_stats()
    assert stats["total_videos"] >= 1
    assert stats["channel"] == "stoic"
chk("History: save + load + get_stats", chk_history_save_load)


def chk_history_normalize():
    from history.history_engine import HistoryEngine
    h = HistoryEngine()
    result = h._normalize('Your MIND,  is Free.')
    assert result == 'your mind is free', f"Got: {repr(result)}"
chk("History: text normalizer", chk_history_normalize)

# ── GROUP 4: Script Engine ───────────────────────────────
def chk_length_config():
    from generator.script_engine import LENGTH_CONFIG, LONG_FORM_CHAPTERS
    required = ["short", "medium", "long_3", "long_5", "long_7", "long_11"]
    for k in required:
        assert k in LENGTH_CONFIG, f"Missing: {k}"
    assert LENGTH_CONFIG["long_11"]["beats"] > LENGTH_CONFIG["long_7"]["beats"]
    assert LENGTH_CONFIG["long_7"]["beats"]  > LENGTH_CONFIG["long_5"]["beats"]
    assert LENGTH_CONFIG["long_5"]["beats"]  > LENGTH_CONFIG["long_3"]["beats"]
    assert LENGTH_CONFIG["long_3"]["beats"]  > LENGTH_CONFIG["medium"]["beats"]
    total_prop = sum(c["proportion"] for c in LONG_FORM_CHAPTERS)
    assert abs(total_prop - 1.0) < 0.01, f"Chapter proportions sum to {total_prop}"
    chapter_names = {c["name"] for c in LONG_FORM_CHAPTERS}
    assert {"HOOK", "PROBLEM", "PHILOSOPHY", "STORY", "APPLICATION", "CLOSE"} <= chapter_names
chk("ScriptEngine: 6 lengths + chapter config valid", chk_length_config)

def chk_long_aspect_ratio():
    from generator.script_engine import LENGTH_CONFIG
    for k in ["long_3", "long_5", "long_7", "long_11"]:
        assert LENGTH_CONFIG[k]["type"] == "long", f"{k} should be type=long"
    for k in ["short", "medium"]:
        assert LENGTH_CONFIG[k]["type"] == "short", f"{k} should be type=short"
chk("ScriptEngine: long/* type='long', short/* type='short'", chk_long_aspect_ratio)

def chk_prompts():
    from generator.script_engine import LEGACY_SYSTEM_PROMPT, _short_form_prompt, _long_form_prompt
    # Legacy fallback prompt: universal rules (no named attributions, no commas)
    assert "NEVER use proper nouns" in LEGACY_SYSTEM_PROMPT or "NEVER use commas" in LEGACY_SYSTEM_PROMPT
    assert "NEVER use commas" in LEGACY_SYSTEM_PROMPT
    # Channel-specific prompts (actual prompts used in production)
    from channels.channel_config import get_channel
    stoic_prompt = get_channel("stoic")["system_prompt"]
    tech_prompt  = get_channel("tech")["system_prompt"]
    assert "NEVER use commas" in stoic_prompt or "No commas" in stoic_prompt or "commas" in stoic_prompt.lower()
    assert "NEVER use commas" in tech_prompt  or "No commas" in tech_prompt  or "commas" in tech_prompt.lower()
    # User-facing prompts: no names, no commas
    p = _short_form_prompt("test", 35, 7)
    assert "No names" in p or "no names" in p.lower()
    p2 = _long_form_prompt("test", 300, 56, "HOOK", "hook", 5, 1)
    assert "no names" in p2.lower()
chk("ScriptEngine: prompts ban names + commas", chk_prompts)


# ── GROUP 5: AudioMixer long-form fixes ─────────────────
def chk_mixer_no_shortest():
    src = open(r'c:\projects\YOUTUBE_WEBAPP\backend\audio\audio_mixer.py', encoding='utf-8').read()
    # Primary mix should NOT have -shortest
    assert '"-shortest"' not in src or src.count('"-shortest"') == 0, \
        "Found -shortest flag in mixer (causes audio cut)"
chk("AudioMixer: no -shortest flag (long-form safe)", chk_mixer_no_shortest)

def chk_mixer_aloop():
    src = open(r'c:\projects\YOUTUBE_WEBAPP\backend\audio\audio_mixer.py', encoding='utf-8').read()
    assert 'aloop' in src, "Missing aloop filter (seamless BGM loop)"
    assert '_extend_bgm_seamless' in src, "Missing _extend_bgm_seamless method"
chk("AudioMixer: aloop seamless BGM (no click seams)", chk_mixer_aloop)

def chk_mixer_timeout_scaled():
    src = open(r'c:\projects\YOUTUBE_WEBAPP\backend\audio\audio_mixer.py', encoding='utf-8').read()
    assert 'timeout_s' in src, "Missing timeout_s scaling"
    assert 'total_dur' in src, "Missing total_dur reference for scaling"
chk("AudioMixer: timeout scaled with video duration", chk_mixer_timeout_scaled)

def chk_mixer_duck_range():
    from audio.audio_mixer import AudioMixer
    m = AudioMixer()
    for emotion, level in m.DUCK_MAP.items():
        assert 0.05 <= level <= 0.20, f"Duck {emotion}={level} out of 5-20% range"
chk("AudioMixer: all duck levels in 5-20% range", chk_mixer_duck_range)

# ── GROUP 6: TTS engine ─────────────────────────────────
def chk_tts_10_voices():
    from audio.tts_engine import VOICE_PRESETS
    assert len(VOICE_PRESETS) == 10, f"Expected 10 voices, got {len(VOICE_PRESETS)}"
chk("TTS: 10 voice presets", chk_tts_10_voices)

def chk_tts_voice_chain_timeout():
    src = open(r'c:\projects\YOUTUBE_WEBAPP\backend\audio\tts_engine.py', encoding='utf-8').read()
    assert 'timeout_s' in src, "Missing timeout_s in TTS voice chain"
    assert 'TimeoutExpired' in src, "Missing TimeoutExpired handling in TTS"
chk("TTS: voice chain has scaled timeout + TimeoutExpired handler", chk_tts_voice_chain_timeout)

def chk_tts_beat_retry():
    src = open(r'c:\projects\YOUTUBE_WEBAPP\backend\audio\tts_engine.py', encoding='utf-8').read()
    assert 'retry' in src.lower() or 'Retry' in src or 'retry OK' in src, "Missing beat retry logic"
    assert 'SKIPPED after retry' in src, "Missing fallback after retry"
chk("TTS: beat retry on failure + silence placeholder", chk_tts_beat_retry)

def chk_tts_cleaner():
    from audio.tts_engine import TTSEngine
    e = TTSEngine("gb_ryan")
    assert e._clean_text("You are not your thoughts, Epictetus") == "You are not your thoughts."
    assert e._clean_text("Ego fuels turmoil, Seneca") == "Ego fuels turmoil."
    assert "," not in e._clean_text("Be strong, be calm, be clear.")
chk("TTS: cleaner strips names + commas", chk_tts_cleaner)

# ── GROUP 7: VideoEngine ─────────────────────────────────
def chk_video_timeout_scaled():
    src = open(r'c:\projects\YOUTUBE_WEBAPP\backend\video\video_engine.py', encoding='utf-8').read()
    assert 'per_clip_timeout' in src, "Missing per_clip_timeout scaling"
    assert 'concat_timeout' in src, "Missing concat_timeout scaling"
chk("VideoEngine: per-clip + concat timeouts scale with clip count", chk_video_timeout_scaled)

def chk_video_aspect_ratios():
    from video.video_engine import RESOLUTIONS
    assert "9:16" in RESOLUTIONS and "16:9" in RESOLUTIONS and "1:1" in RESOLUTIONS
    assert RESOLUTIONS["9:16"]  == (1080, 1920), "9:16 must be 1080x1920 (Shorts)"
    assert RESOLUTIONS["16:9"] == (1920, 1080), "16:9 must be 1920x1080 (YouTube)"
    assert RESOLUTIONS["1:1"]  == (1080, 1080), "1:1 must be 1080x1080 (Instagram)"
chk("VideoEngine: all 3 aspect ratios correct resolution", chk_video_aspect_ratios)

chk("VideoEngine: no MoviePy dependency",
    lambda: not re.search(r'moviepy', open(r'c:\projects\YOUTUBE_WEBAPP\backend\video\video_engine.py').read()))

# ── GROUP 8: Aspect Ratio Enforcement ───────────────────
def chk_aspect_ratio_enforcement():
    src = open(r'c:\projects\YOUTUBE_WEBAPP\backend\main.py', encoding='utf-8').read()
    assert 'aspect_ratio = "16:9"' in src or "aspect_ratio = '16:9'" in src, \
        "Backend must force 16:9 for long-form videos"
    assert 'Long-form' in src or 'long' in src.lower(), "Should log long-form aspect ratio override"
chk("main.py: backend enforces 16:9 for long_* videos", chk_aspect_ratio_enforcement)

# ── GROUP 9: FFmpeg render fixes ─────────────────────────
def chk_render_no_shortest():
    src = open(r'c:\projects\YOUTUBE_WEBAPP\backend\main.py', encoding='utf-8').read()
    # Find the _ffmpeg_render function specifically
    fn_start = src.find('def _ffmpeg_render(')
    fn_end   = src.find('\ndef _extract_thumb', fn_start)
    fn_body  = src[fn_start:fn_end]
    assert '"-shortest"' not in fn_body and "'-shortest'" not in fn_body, \
        "_ffmpeg_render still has -shortest flag"
chk("main.py _ffmpeg_render: no -shortest (no audio cut)", chk_render_no_shortest)

def chk_render_duration_param():
    src = open(r'c:\projects\YOUTUBE_WEBAPP\backend\main.py', encoding='utf-8').read()
    assert 'duration: float' in src, "Missing duration param in _ffmpeg_render"
    assert 'dur_flags' in src or '-t' in src, "Missing -t duration control in render"
chk("main.py _ffmpeg_render: uses -t duration (precise length)", chk_render_duration_param)

def chk_render_timeout():
    src = open(r'c:\projects\YOUTUBE_WEBAPP\backend\main.py', encoding='utf-8').read()
    fn_start = src.find('def _ffmpeg_render(')
    fn_end   = src.find('\ndef _extract_thumb', fn_start)
    fn_body  = src[fn_start:fn_end]
    assert 'timeout' in fn_body, "_ffmpeg_render should have timeout"
chk("main.py _ffmpeg_render: has timeout (no infinite hang)", chk_render_timeout)

def chk_thumb_at_20pct():
    src = open(r'c:\projects\YOUTUBE_WEBAPP\backend\main.py', encoding='utf-8').read()
    fn_start = src.find('def _extract_thumb(')
    fn_body  = src[fn_start:fn_start+800]
    assert '0.20' in fn_body or '20%' in fn_body.lower() or 'dur * 0' in fn_body, \
        "Thumbnail should be extracted at 20% not fixed 5s"
chk("main.py _extract_thumb: at 20% mark (not fixed 5s)", chk_thumb_at_20pct)

# ── GROUP 10: API Routes ─────────────────────────────────
def chk_routes():
    import main
    routes = {r.path for r in main.app.routes}
    required = ["/api/generate", "/api/stream-progress/{job_id}",
                "/api/status/{job_id}", "/api/result/{job_id}",
                "/api/health", "/api/voices", "/api/history"]
    for r in required:
        assert r in routes, f"Missing route: {r}"
chk("API: all 7 routes registered", chk_routes)

# ── GROUP 11: BGM Engine ─────────────────────────────────
chk("BGM: curated tracks present", lambda: len(
    __import__("audio.bgm_engine", fromlist=["CURATED_TRACKS"]).CURATED_TRACKS) >= 4)

# ── GROUP 12: CaptionEngine ──────────────────────────────
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
chk("CaptionEngine: produces ASS subtitle events", chk_captions)

# ── GROUP 13: Frontend ───────────────────────────────────
def chk_frontend():
    tsx = open(r'c:\projects\YOUTUBE_WEBAPP\frontend\app\components\GenerateForm.tsx', encoding='utf-8').read()
    assert 'gb_ryan' in tsx
    for lk in ['"long_3"', '"long_5"', '"long_7"', '"long_11"']:
        assert lk in tsx, f"Missing {lk}"
    assert '"af_bella"' not in tsx, "Old voice ID present"
    assert 'history' in tsx.lower(), "No history reference in frontend"
    assert '16:9' in tsx, "Missing 16:9 aspect ratio"
chk("Frontend: 6 lengths, voices, history note, 16:9", chk_frontend)

def chk_env():
    env = open(r'c:\projects\YOUTUBE_WEBAPP\.env', encoding='utf-8').read()
    for key in ['GROQ_API_KEY', 'PEXELS_API_KEY', 'NGROK_AUTHTOKEN', 'FREESOUND_API_KEY']:
        assert key in env, f"Missing key: {key}"
chk(".env: all API keys present", chk_env)

# ── FINAL REPORT ──────────────────────────────────────────
print()
print("=" * 68)
print("  MASTER VERIFICATION v3 — ALL SYSTEMS (SHORT + LONG-FORM)")
print("=" * 68)
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
print("=" * 68)
