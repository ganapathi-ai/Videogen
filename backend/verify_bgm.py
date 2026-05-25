"""Full BGM system verification."""
import sys, os
sys.path.insert(0, r'c:\projects\YOUTUBE_WEBAPP\backend')
os.chdir(r'c:\projects\YOUTUBE_WEBAPP\backend')
os.environ['FREESOUND_API_KEY'] = 'mF59G65s4J1OMrdDPiAWjuIgoHAvjIRztWOK7A2O'

results = []

def chk(label, fn):
    try:
        fn()
        results.append(("OK  ", label))
    except Exception as e:
        results.append(("FAIL", f"{label}: {e}"))

# 1. Import checks
chk("import bgm_engine",   lambda: __import__("audio.bgm_engine"))
chk("import audio_mixer",  lambda: __import__("audio.audio_mixer"))
chk("import main",         lambda: __import__("main"))

# 2. BGMEngine structure
def test_bgm_structure():
    from audio.bgm_engine import BGMEngine, CURATED_TRACKS, EMOTION_QUERIES
    e = BGMEngine(api_key='mF59G65s4J1OMrdDPiAWjuIgoHAvjIRztWOK7A2O')
    assert e.cache_dir.exists(), "Cache dir not created"
    assert len(CURATED_TRACKS) >= 4, "Not enough curated tracks"
    assert len(EMOTION_QUERIES) >= 6, "Not enough emotion queries"
chk("BGMEngine structure", test_bgm_structure)

# 3. Dominant emotion logic
def test_dominant():
    from audio.bgm_engine import BGMEngine
    e = BGMEngine()
    assert e._dominant_emotion(["deep", "deep", "emotional"]) == "deep"
    assert e._dominant_emotion(["inspiring", "inspiring", "deep"]) == "inspiring"
    assert e._dominant_emotion([]) == "deep"
chk("Dominant emotion logic", test_dominant)

# 4. Freesound API live test
def test_freesound_api():
    import requests
    resp = requests.get(
        "https://freesound.org/apiv2/search/text/",
        params={
            "query": "dark ambient meditation",
            "filter": 'license:"Creative Commons 0" duration:[60 TO 360]',
            "fields": "id,name,previews,duration",
            "token": "mF59G65s4J1OMrdDPiAWjuIgoHAvjIRztWOK7A2O",
            "page_size": "3",
        },
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json()
    count = results.get("count", 0)
    assert count > 0, f"No results from Freesound: {results}"
    first = results["results"][0]
    assert "preview-hq-mp3" in first.get("previews", {}), "No preview URL"
    preview_url = first["previews"]["preview-hq-mp3"]
    assert "cdn.freesound.org" in preview_url, f"Unexpected URL: {preview_url}"
    print(f"      Freesound: {count} results | First: '{first['name']}'")
chk("Freesound API live (CC0 tracks found)", test_freesound_api)

# 5. Preview URL download test
def test_preview_download():
    import requests
    # Use a known CC0 preview URL from our curated list
    url = "https://cdn.freesound.org/previews/854/854859_15636277-hq.mp3"
    r = requests.head(url, timeout=10)
    assert r.status_code == 200, f"Preview URL returned {r.status_code}"
    ct = r.headers.get("Content-Type", "")
    assert "audio" in ct or "mpeg" in ct or "mp3" in ct or "octet" in ct, f"Unexpected content type: {ct}"
    print(f"      Preview URL OK: {r.status_code}, type={ct}")
chk("Freesound preview URL accessible (no auth)", test_preview_download)

# 6. BGM download + cache (downloads curated fallback)
def test_bgm_download():
    from audio.bgm_engine import BGMEngine
    e = BGMEngine()
    # Use curated track (guaranteed to work)
    path = e._fetch_curated("minimal")
    if path:
        import os
        size = os.path.getsize(path)
        assert size > 10_000, f"Downloaded file too small: {size} bytes"
        print(f"      Downloaded: {os.path.basename(path)} ({size//1024}KB)")
    else:
        raise AssertionError("Curated track download failed")
chk("BGM curated track download + cache", test_bgm_download)

# 7. AudioMixer structure
def test_mixer():
    from audio.audio_mixer import AudioMixer
    m = AudioMixer()
    assert hasattr(m, "mix")
    assert hasattr(m, "DUCK_MAP")
    assert m.DUCK_MAP["minimal"] < 0.15, "Minimal should be very quiet"
    assert m.DUCK_MAP["inspiring"] <= 0.15, "Inspiring max 15%"
chk("AudioMixer duck levels (8-15%)", test_mixer)

# 8. FFmpeg filter syntax (mixer filter_complex)
def test_mixer_filter():
    import subprocess
    # Test the filter_complex with NUL inputs
    r = subprocess.run([
        "ffmpeg",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
        "-f", "lavfi", "-i", "sine=frequency=220:duration=5",
        "-filter_complex",
        "[1:a]highpass=f=500,volume=0.12,afade=t=in:st=0:d=1.5,afade=t=out:st=2:d=3[bgm];"
        "[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[out]",
        "-map", "[out]",
        "-f", "null", "-",
    ], capture_output=True, text=True, timeout=15)
    assert "Error" not in r.stderr or r.returncode == 0, f"Filter error: {r.stderr[-200:]}"
    assert "No such filter" not in r.stderr, f"Bad filter: {r.stderr[-200:]}"
chk("AudioMixer FFmpeg filter_complex valid", test_mixer_filter)

# ── Report ─────────────────────────────────────────────
print()
print("=" * 55)
print("  BGM SYSTEM VERIFICATION REPORT")
print("=" * 55)
passed = failed = 0
for status, label in results:
    print(f"  {status}  {label}")
    if status == "OK  ": passed += 1
    else: failed += 1
print()
print(f"  {passed}/{len(results)} passed")
if failed == 0:
    print("  ALL BGM CHECKS PASSED")
print("=" * 55)
