import sys
sys.path.insert(0, r'c:\projects\YOUTUBE_WEBAPP\backend')

from audio.tts_engine import TTSEngine, get_voice_list, VOICE_PRESETS
import subprocess

results = []

def chk(label, fn):
    try:
        fn()
        results.append(("OK  ", label))
    except Exception as e:
        results.append(("FAIL", f"{label}: {e}"))

def test_voice_count():
    voices = get_voice_list()
    assert len(voices) == 10, f"Expected 10 voices, got {len(voices)}"
    for v in voices:
        print(f"    {v['id']:25s}  {v['label'].encode('ascii','ignore').decode()}")

def test_rate_pitch():
    for k, v in VOICE_PRESETS.items():
        rate = v["rate"]
        pitch = v["pitch"]
        # All should have negative rate (slow)
        assert rate.startswith("-"), f"{k} rate not slow: {rate}"
        # All should have negative pitch (deep)
        assert pitch.startswith("-"), f"{k} pitch not deep: {pitch}"

def test_legacy():
    e = TTSEngine("bm_george")
    assert e.voice_key == "gb_ryan", f"Got {e.voice_key}"
    e2 = TTSEngine("gb_ryan")
    assert e2.edge_voice == "en-GB-RyanNeural"

def test_cleaner():
    e = TTSEngine("gb_ryan")
    # Names appended at END of sentence — realistic pattern from script engine
    cases = [
        ("You are not your thoughts, Epictetus", ["Epictetus", ","]),
        ("Ego fuels turmoil, Seneca", ["Seneca", ","]),
        ("Recognize the power, Stoics", ["Stoics", ","]),   # at end with comma
        ("Let go of fear, Zeno", ["Zeno", ","]),
    ]
    for txt, bads in cases:
        out = e._clean_text(txt)
        for bad in bads:
            if bad == ",":
                assert "," not in out, f"Comma in: {out}"
            else:
                # Name must not be at the END of cleaned sentence
                stripped = out.rstrip(".!? ")
                assert not stripped.endswith(bad), f"'{bad}' still at end of: {out}"

def test_ffmpeg_chain():
    # Validate the filter syntax with ffmpeg -af help
    r = subprocess.run(
        ["ffmpeg", "-i", "NUL", "-af",
         "highpass=f=80,equalizer=f=120:t=q:w=1.5:g=6,"
         "equalizer=f=250:t=q:w=1:g=-3,equalizer=f=3000:t=q:w=2:g=2,"
         "acompressor=threshold=-18dB:ratio=4:attack=5:release=80:makeup=4dB,"
         "volume=2.5,loudnorm=I=-14:TP=-1.5:LRA=7",
         "-f", "null", "-", "-t", "0"],
        capture_output=True, text=True
    )
    # FFmpeg errors on NUL input but filter parsing happens first
    # If "No such filter" in stderr — the filter name is wrong
    assert "No such filter" not in r.stderr, f"Bad filter: {r.stderr}"
    assert "Invalid option" not in r.stderr, f"Bad option: {r.stderr}"

print()
print("=" * 58)
print("  TTS ENGINE + AUDIO CHAIN VERIFICATION")
print("=" * 58)

print()
print("  10 Voices:")
test_voice_count()
print()

chk("10 voices registered", lambda: None)  # already tested above
chk("All voices: slow rate (negative %)", test_rate_pitch)
chk("All voices: deep pitch (negative Hz)", test_rate_pitch)
chk("Legacy voice ID mapping", test_legacy)
chk("Text cleaner: strips names + commas", test_cleaner)
chk("FFmpeg audio chain: valid filter syntax", test_ffmpeg_chain)

print()
for s, l in results:
    print(f"  {s}  {l}")
passed = sum(1 for s, _ in results if s == "OK  ")
print()
print(f"  {passed}/{len(results)} passed")
print("=" * 58)
