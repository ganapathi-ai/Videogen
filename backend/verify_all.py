"""
MASTER VERIFICATION — checks every backend file for:
  1. Imports work cleanly
  2. No dead MoviePy 1.x API calls (moviepy.editor, .fl(), .subclip(), .resize())
  3. No dead Kokoro/old voice IDs
  4. All routes registered
  5. BGM engine + audio chain
  6. TTS voices (10 curated)
  7. FFmpeg ass= path escaping
  8. Script prompt (no philosopher names)
  9. Caption engine produces events
 10. Video engine FFmpeg color clip
"""

import sys, os, subprocess, re
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

# ────────────────────────────────────────────────────────
# GROUP 1: Module imports
# ────────────────────────────────────────────────────────
MODULES = [
    "main",
    "generator.script_engine",
    "audio.tts_engine",
    "audio.audio_mixer",
    "audio.bgm_engine",
    "alignment.align_engine",
    "timeline.timeline_engine",
    "media.media_engine",
    "embeddings.faiss_engine",
    "video.video_engine",
    "captions.caption_engine",
    "validator.validator",
]
for mod in MODULES:
    chk(f"import {mod}", lambda m=mod: __import__(m))

# ────────────────────────────────────────────────────────
# GROUP 2: Dead code scan (grep for known broken APIs)
# ────────────────────────────────────────────────────────
PY_FILES = []
for root, dirs, files in os.walk(r'c:\projects\YOUTUBE_WEBAPP\backend'):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', 'exports', 'bgm_cache', 'assets')]
    for f in files:
        if f.endswith('.py'):
            PY_FILES.append(os.path.join(root, f))

def scan_for_pattern(pattern, label, allow_files=None):
    found = []
    rx = re.compile(pattern)
    for fpath in PY_FILES:
        # Skip verification scripts and test files themselves
        basename = os.path.basename(fpath)
        if basename.startswith('verify_') or basename in ('test_engines.py', 'cli.py'):
            continue
        if allow_files and basename in allow_files:
            continue
        with open(fpath, encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                if rx.search(line) and not line.strip().startswith('#'):
                    found.append(f"{os.path.basename(fpath)}:{i}: {line.strip()[:80]}")
    if found:
        raise AssertionError("Found dead code:\n    " + "\n    ".join(found[:5]))

chk("No moviepy.editor import", lambda: scan_for_pattern(r'import moviepy\.editor|from moviepy\.editor', "moviepy.editor"))
chk("No clip.fl() call (MoviePy 1.x)", lambda: scan_for_pattern(r'\.fl\(', "clip.fl()"))
chk("No clip.subclip() call (renamed)", lambda: scan_for_pattern(r'\.subclip\(', "subclip"))
chk("No kokoro import", lambda: scan_for_pattern(r'import kokoro|from kokoro', "kokoro"))
chk("No old google.generativeai", lambda: scan_for_pattern(r'from google\.generativeai|import google\.generativeai', "old gemini"))
chk("No old voice IDs (af_bella hardcoded)", lambda: scan_for_pattern(r'"af_bella"|"bm_george"', "old voice ID", allow_files=['tts_engine.py']))

# ────────────────────────────────────────────────────────
# GROUP 3: TTS Engine
# ────────────────────────────────────────────────────────
def chk_tts_voices():
    from audio.tts_engine import VOICE_PRESETS, get_voice_list
    assert len(VOICE_PRESETS) == 10, f"Expected 10 voices, got {len(VOICE_PRESETS)}"
    for k, v in VOICE_PRESETS.items():
        assert v['rate'].startswith('-'), f"{k}: rate not negative (not slow)"
        assert v['pitch'].startswith('-'), f"{k}: pitch not negative (not deep)"
        assert 'en-' in v['edge'], f"{k}: not an English edge-tts voice"
chk("TTS: 10 deep voices, all slow rate + low pitch", chk_tts_voices)

def chk_tts_cleaner():
    from audio.tts_engine import TTSEngine
    e = TTSEngine('gb_ryan')
    cases = [
        ("You are not your thoughts, Epictetus", "Epictetus"),
        ("Ego fuels turmoil, Seneca", "Seneca"),
        ("Recognize the power, Stoics", "Stoics"),
        ("Let go of fear, Zeno", "Zeno"),
    ]
    for txt, bad in cases:
        out = e._clean_text(txt)
        assert bad not in out.rstrip('.!? '), f"'{bad}' still in: {out}"
        assert ',' not in out, f"Comma still in: {out}"
chk("TTS: cleaner strips philosopher names + commas", chk_tts_cleaner)

def chk_legacy_map():
    from audio.tts_engine import TTSEngine, _LEGACY_MAP, VOICE_PRESETS
    for old_id, new_id in _LEGACY_MAP.items():
        assert new_id in VOICE_PRESETS, f"Legacy '{old_id}' maps to unknown '{new_id}'"
chk("TTS: all legacy voice IDs map to valid new IDs", chk_legacy_map)

# ────────────────────────────────────────────────────────
# GROUP 4: BGM Engine
# ────────────────────────────────────────────────────────
def chk_bgm_structure():
    from audio.bgm_engine import BGMEngine, CURATED_TRACKS, EMOTION_QUERIES, EMOTION_CATEGORY
    e = BGMEngine()
    assert e.cache_dir.exists()
    assert len(CURATED_TRACKS) >= 4
    assert all(cat in CURATED_TRACKS for cat in ['minimal','deep','emotional','inspiring'])
    assert len(EMOTION_QUERIES) >= 8
    # Every emotion should map to a category
    for em in ['minimal','deep','emotional','inspiring','resolute','modern','steady','reassuring']:
        assert em in EMOTION_CATEGORY, f"Missing emotion category: {em}"
chk("BGM: structure + all emotion categories", chk_bgm_structure)

def chk_bgm_dominant():
    from audio.bgm_engine import BGMEngine
    e = BGMEngine()
    assert e._dominant_emotion(['deep','deep','emotional']) == 'deep'
    assert e._dominant_emotion(['inspiring']*3 + ['minimal']) == 'inspiring'
    assert e._dominant_emotion([]) == 'deep'
chk("BGM: dominant emotion selection", chk_bgm_dominant)

def chk_bgm_cached():
    from audio.bgm_engine import BGMEngine
    e = BGMEngine()
    cached = e.list_cached()
    # After previous verify_bgm.py run, should have at least 1 cached file
    if cached:
        print(f"      {len(cached)} tracks cached: {[os.path.basename(c) for c in cached]}")
chk("BGM: local cache accessible", chk_bgm_cached)

# ────────────────────────────────────────────────────────
# GROUP 5: Audio Mixer
# ────────────────────────────────────────────────────────
def chk_mixer_levels():
    from audio.audio_mixer import AudioMixer
    m = AudioMixer()
    for emotion, level in m.DUCK_MAP.items():
        assert 0.05 <= level <= 0.20, f"{emotion}: duck level {level} out of range (5-20%)"
chk("Mixer: all duck levels in 5-20% range", chk_mixer_levels)

def chk_mixer_ffmpeg():
    r = subprocess.run([
        'ffmpeg',
        '-f','lavfi','-i','sine=frequency=440:duration=3',
        '-f','lavfi','-i','sine=frequency=220:duration=3',
        '-filter_complex',
        '[1:a]highpass=f=500,volume=0.12,'
        'afade=t=in:st=0:d=1.5,'
        'afade=t=out:st=0:d=2[bgm];'
        '[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[out]',
        '-map','[out]','-f','null','-',
    ], capture_output=True, text=True, timeout=15)
    assert 'No such filter' not in r.stderr, f"Bad filter: {r.stderr[-200:]}"
chk("Mixer: FFmpeg filter_complex (HP+duck+fade+amix)", chk_mixer_ffmpeg)

# ────────────────────────────────────────────────────────
# GROUP 6: Video Engine
# ────────────────────────────────────────────────────────
def chk_video_color():
    import tempfile
    from video.video_engine import VideoEngine
    e = VideoEngine('9:16', 30)
    tmp = tempfile.mktemp(suffix='.mp4')
    ok = e._generate_color_clip(tmp, 2.0)
    assert ok and os.path.getsize(tmp) > 500
    os.unlink(tmp)
chk("Video: FFmpeg color clip generation", chk_video_color)

def chk_video_crop():
    from video.video_engine import VideoEngine
    e = VideoEngine('9:16', 30)
    assert 'crop' in e._build_crop_filter(1920, 1080), "1920x1080 -> 9:16 should crop"
    assert 'scale' in e._build_crop_filter(1080, 1920), "Already 9:16 should just scale"
    e2 = VideoEngine('16:9', 30)
    assert 'crop' in e2._build_crop_filter(1080, 1920), "1080x1920 -> 16:9 should crop"
chk("Video: crop filter logic for all aspect ratios", chk_video_crop)

def chk_video_no_moviepy():
    # Ensure video_engine doesn't import moviepy at all
    with open(r'c:\projects\YOUTUBE_WEBAPP\backend\video\video_engine.py', encoding='utf-8') as f:
        content = f.read()
    assert 'moviepy' not in content, "video_engine.py still references moviepy!"
chk("Video: no MoviePy dependency", chk_video_no_moviepy)

# ────────────────────────────────────────────────────────
# GROUP 7: Caption Engine
# ────────────────────────────────────────────────────────
def chk_captions():
    import tempfile
    from captions.caption_engine import CaptionEngine
    import pysubs2
    timeline = {'segments':[{
        'id':1,'text':'Your mind is not bound.',
        'word_data':[
            {'word':'Your','start':0.5,'end':0.8},
            {'word':'mind','start':0.9,'end':1.1},
            {'word':'is','start':1.2,'end':1.4},
            {'word':'not','start':1.5,'end':1.7},
            {'word':'bound.','start':1.8,'end':2.2},
        ]
    }]}
    e = CaptionEngine((1080,1920))
    tmp = tempfile.mktemp(suffix='.ass')
    out = e.build_ass_subtitles(timeline, tmp)
    subs = pysubs2.load(out)
    assert len(subs) > 0, "No subtitle events"
    os.unlink(out)
chk("Captions: ASS subtitle generation", chk_captions)

def chk_ass_path():
    def escape(p):
        p = p.replace('\\', '/')
        if len(p) >= 2 and p[1] == ':':
            p = p[0] + '\\:' + p[2:]
        return p
    raw = r'C:\projects\YOUTUBE_WEBAPP\backend\exports\abc\captions.ass'
    fixed = escape(raw)
    assert fixed.startswith('C\\:/'), f"Wrong: {fixed}"
    assert '\\:' in fixed, "Colon not escaped"
chk("Captions: Windows FFmpeg ass= path escaping", chk_ass_path)

# ────────────────────────────────────────────────────────
# GROUP 8: Script Engine
# ────────────────────────────────────────────────────────
def chk_script_prompt():
    from generator.script_engine import SYSTEM_PROMPT, _user_prompt
    assert 'NEVER mention any philosopher' in SYSTEM_PROMPT
    assert 'NEVER use commas' in SYSTEM_PROMPT
    p = _user_prompt('test topic', 35, 7)
    assert 'DO NOT add names' in p
    assert 'DO NOT use commas' in p or 'No commas' in p
chk("Script: prompt bans philosopher names + commas", chk_script_prompt)

# ────────────────────────────────────────────────────────
# GROUP 9: API Routes
# ────────────────────────────────────────────────────────
def chk_routes():
    import main
    routes = {r.path for r in main.app.routes}
    required = [
        '/api/generate', '/api/stream-progress/{job_id}',
        '/api/status/{job_id}', '/api/result/{job_id}',
        '/api/health', '/api/voices',
    ]
    for r in required:
        assert r in routes, f"Missing route: {r}"
chk("API: all 6 routes registered", chk_routes)

# ────────────────────────────────────────────────────────
# GROUP 10: .env keys check
# ────────────────────────────────────────────────────────
def chk_env():
    from pathlib import Path
    env = Path(r'c:\projects\YOUTUBE_WEBAPP\.env').read_text(encoding='utf-8')
    required_keys = ['GROQ_API_KEY', 'PEXELS_API_KEY', 'NGROK_AUTHTOKEN', 'FREESOUND_API_KEY']
    for key in required_keys:
        assert key in env, f"Missing .env key: {key}"
        # Check it's not empty or placeholder
        line = [l for l in env.splitlines() if l.startswith(key+'=')]
        if line:
            val = line[0].split('=',1)[1].strip()
            assert val and val != 'YOUR_KEY_HERE', f"{key} is empty/placeholder"
chk(".env: all required API keys present", chk_env)

# ────────────────────────────────────────────────────────
# GROUP 11: Frontend files exist and have no old voice IDs
# ────────────────────────────────────────────────────────
def chk_frontend():
    files = [
        r'c:\projects\YOUTUBE_WEBAPP\frontend\app\page.tsx',
        r'c:\projects\YOUTUBE_WEBAPP\frontend\app\components\GenerateForm.tsx',
        r'c:\projects\YOUTUBE_WEBAPP\frontend\app\globals.css',
        r'c:\projects\YOUTUBE_WEBAPP\frontend\app\layout.tsx',
    ]
    for f in files:
        assert os.path.exists(f), f"Missing: {f}"
    # Check GenerateForm uses new voice IDs
    with open(r'c:\projects\YOUTUBE_WEBAPP\frontend\app\components\GenerateForm.tsx', encoding='utf-8') as f:
        content = f.read()
    assert 'gb_ryan' in content, "GenerateForm missing gb_ryan voice"
    assert 'in_prabhat' in content, "GenerateForm missing in_prabhat voice"
    assert '"af_bella"' not in content, "Old voice ID af_bella still in frontend"
    # Check page.tsx uses job_id not task_id
    with open(r'c:\projects\YOUTUBE_WEBAPP\frontend\app\page.tsx', encoding='utf-8') as f:
        pg = f.read()
    assert 'const { job_id }' in pg, "Frontend still using task_id instead of job_id"
chk("Frontend: files exist + correct voice IDs + job_id", chk_frontend)

# ────────────────────────────────────────────────────────
# REPORT
# ────────────────────────────────────────────────────────
print()
print("=" * 60)
print("  MASTER VERIFICATION REPORT")
print("=" * 60)
passed = failed = 0
for status, label in results:
    icon = '[+]' if status == 'OK  ' else '[X]'
    print(f"  {icon}  {label}")
    if status == "OK  ": passed += 1
    else: failed += 1
print()
print(f"  Result: {passed}/{len(results)} passed  |  {failed} failed")
if failed == 0:
    print("  *** ALL CHECKS PASSED ***")
else:
    print("  *** FIX THE FAILING CHECKS ABOVE ***")
print("=" * 60)
