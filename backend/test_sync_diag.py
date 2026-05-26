"""
FRAME-LEVEL CAPTION SYNC DIAGNOSTIC
Traces the complete timing pipeline to find ALL sync offsets.

Pipeline order:
  TTS → audio.wav (44100Hz mono)
  AlignmentEngine → word_timestamps from audio.wav
  AudioMixer → audio_mixed.wav (voice + BGM, stereo)
  CaptionEngine → captions.ass (uses word_timestamps)
  FFmpeg render → final_video.mp4 (audio=audio_mixed, subs=captions.ass)

KEY QUESTION: Do word timestamps from audio.wav match timing in audio_mixed.wav?
If AudioMixer adds ANY leading silence/offset, captions drift from speech.
"""
import subprocess, json, sys, numpy as np, soundfile as sf, uuid, shutil
from pathlib import Path
sys.path.insert(0, ".")

PASS = "[OK] "
FAIL = "[FAIL] "
WARN = "[WARN] "
results = []
job = Path(f"sync_diag_{uuid.uuid4().hex[:6]}")
job.mkdir(exist_ok=True)

FPS = 30
FRAME_MS = 1000.0 / FPS  # 33.33ms per frame

print("=" * 65)
print("FRAME-LEVEL CAPTION SYNC DIAGNOSTIC")
print(f"Frame size at {FPS}fps = {FRAME_MS:.2f}ms")
print("=" * 65)

# ── Step 1: Synthesize test audio ────────────────────────────────────────────
print("\n[1] Creating test voice audio (simulates edge-tts output)...")
voice_wav = str(job / "audio.wav")
# 0.1s silence + 3.0s speech at 44100Hz mono (like processed TTS output)
silence_pre  = np.zeros(int(44100 * 0.10), dtype=np.float32)
speech_tone  = (np.sin(2 * np.pi * 220 * np.arange(int(44100 * 3.0)) / 44100) * 0.5).astype(np.float32)
silence_post = np.zeros(int(44100 * 0.15), dtype=np.float32)
voice_data   = np.concatenate([silence_pre, speech_tone, silence_post])
sf.write(voice_wav, voice_data, 44100)
voice_dur = len(voice_data) / 44100
print(f"  Voice: {voice_dur:.3f}s (0.10s pre-silence + 3.0s speech + 0.15s post)")

# ── Step 2: AlignmentEngine runs on audio.wav ────────────────────────────────
print("\n[2] AlignmentEngine on voice audio.wav...")
(job / "script.json").write_text(json.dumps({"beats": [
    {"text": "discipline is freedom always remember this stoic principle"},
]}), encoding="utf-8")

from alignment.align_engine import AlignmentEngine
words = AlignmentEngine()._fallback_timing(voice_wav)
first_word_start = words[0]["start"] if words else 0.0
last_word_end    = words[-1]["end"]  if words else 0.0
print(f"  Word count: {len(words)}")
print(f"  First word '{words[0]['word']}' start: {first_word_start:.4f}s")
print(f"  Last word  '{words[-1]['word']}' end:   {last_word_end:.4f}s")
print(f"  Expected speech start ~= 0.08s (100ms silence - 20ms pre-roll)")

# ── Step 3: AudioMixer → audio_mixed.wav ─────────────────────────────────────
print("\n[3] AudioMixer: checking if it shifts audio start time...")
# Create a minimal BGM (sine wave)
bgm_wav = str(job / "bgm.wav")
bgm_data = (np.sin(2 * np.pi * 55 * np.arange(int(44100 * 5.0)) / 44100) * 0.1).astype(np.float32)
sf.write(bgm_wav, np.stack([bgm_data, bgm_data], axis=1), 44100)

from audio.audio_mixer import AudioMixer
mixed_wav = str(job / "audio_mixed.wav")
fake_timeline = {
    "duration": voice_dur,
    "segments": [{"audio_start": 0.0, "audio_end": voice_dur, "emotion": "deep"}]
}
AudioMixer().mix(voice_wav, bgm_wav, fake_timeline, mixed_wav)

# Probe mixed audio for start time of actual speech
mixed_data, mixed_sr = sf.read(mixed_wav, dtype="float32")
if mixed_data.ndim > 1:
    mixed_data = mixed_data.mean(axis=1)
mixed_dur = len(mixed_data) / mixed_sr

# Detect speech start in mixed audio
THRESH = 10 ** (-35.0 / 20.0)  # -35dB threshold
loud_samples = np.where(np.abs(mixed_data) > THRESH)[0]
mixed_speech_start = loud_samples[0] / mixed_sr if len(loud_samples) > 0 else 0.0

print(f"  Mixed audio duration: {mixed_dur:.3f}s (voice was {voice_dur:.3f}s)")
print(f"  Voice start in audio.wav:   ~0.08s (after 0.1s silence - 20ms pre-roll)")
print(f"  Speech start in mixed audio: {mixed_speech_start:.4f}s")

# CRITICAL CHECK: does mixing shift the voice start time?
voice_in_mixed_offset = abs(mixed_speech_start - first_word_start)
frames_off = voice_in_mixed_offset / (FRAME_MS / 1000.0)
if voice_in_mixed_offset < 0.034:  # < 1 frame (33ms)
    results.append(True)
    print(f"  {PASS}Mixer timing offset: {voice_in_mixed_offset*1000:.1f}ms ({frames_off:.2f} frames) — WITHIN 1 FRAME")
else:
    results.append(False)
    print(f"  {FAIL}Mixer timing offset: {voice_in_mixed_offset*1000:.1f}ms ({frames_off:.2f} frames) — CAUSES DRIFT!")
    print(f"       → Captions aligned to audio.wav will be {voice_in_mixed_offset*1000:.0f}ms off in final video")

# ── Step 4: Caption ASS timing ───────────────────────────────────────────────
print("\n[4] CaptionEngine ASS timing verification...")
from captions.caption_engine import CaptionEngine
fake_tl = {
    "segments": [{
        "segment_id": 0,
        "audio_start": first_word_start,
        "audio_end": last_word_end,
        "word_data": [
            {"word": w["word"], "start": w["start"], "end": w["end"]}
            for w in words
        ]
    }]
}
ass_path = str(job / "captions.ass")
CaptionEngine((1080, 1920)).build_ass_subtitles(fake_tl, ass_path)
ass_text = Path(ass_path).read_text(encoding="utf-8")
# Parse ASS events to check first event timing
events = [l for l in ass_text.split("\n") if l.startswith("Dialogue:")]
if events:
    first_event = events[0]
    # Format: Dialogue: Layer,Start,End,...
    parts = first_event.split(",")
    ass_start_str = parts[1].strip()  # e.g. "0:00:00.08"
    print(f"  First ASS event start: '{ass_start_str}'")
    # Parse ASS time to seconds
    h, m, s_cs = ass_start_str.split(":")
    s, cs = s_cs.split(".")
    ass_start_s = int(h)*3600 + int(m)*60 + int(s) + int(cs)/100.0
    caption_vs_word_diff = abs(ass_start_s - first_word_start)
    if caption_vs_word_diff < 0.01:
        results.append(True)
        print(f"  {PASS}ASS event start={ass_start_s:.3f}s matches word_start={first_word_start:.3f}s "
              f"(diff={caption_vs_word_diff*1000:.1f}ms — sub-frame accurate)")
    else:
        results.append(False)
        print(f"  {FAIL}ASS timing mismatch: ASS={ass_start_s:.3f}s vs word={first_word_start:.3f}s "
              f"(diff={caption_vs_word_diff*1000:.0f}ms)")

# ── Step 5: End-to-end frame-level render test ───────────────────────────────
print("\n[5] End-to-end render + frame-level sync measurement...")
raw_video = str(job / "raw.mp4")
final_out  = str(job / "final.mp4")

subprocess.run([
    "ffmpeg", "-f", "lavfi", "-i", "color=black:s=1080x1920:r=30",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", f"{voice_dur:.3f}", "-preset", "fast",
    raw_video, "-y"
], capture_output=True, check=True)

from main import _ffmpeg_render
_ffmpeg_render(raw_video, mixed_wav, ass_path, final_out,
               fps=30, duration=voice_dur, watermark="neuralbaba_empire")

# Probe the final output
probe = subprocess.run(
    ["ffprobe", "-v", "quiet", "-show_streams", "-print_format", "json", final_out],
    capture_output=True, text=True
)
streams = json.loads(probe.stdout).get("streams", [])
v = next((s for s in streams if s.get("codec_type") == "video"), {})
a = next((s for s in streams if s.get("codec_type") == "audio"), {})

print(f"  Video: {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')}")
print(f"  Audio: {a.get('codec_name')} {a.get('channels')}ch {a.get('sample_rate')}Hz")

# Check audio start_time in the container
audio_start_time = float(a.get("start_time", 0.0))
video_start_time = float(v.get("start_time", 0.0))
av_offset_ms = abs(audio_start_time - video_start_time) * 1000
frames_off_av = av_offset_ms / FRAME_MS

print(f"  Container audio start_time: {audio_start_time:.6f}s")
print(f"  Container video start_time: {video_start_time:.6f}s")
print(f"  A/V offset in container:    {av_offset_ms:.2f}ms ({frames_off_av:.2f} frames)")

if av_offset_ms < FRAME_MS:
    results.append(True)
    print(f"  {PASS}A/V in container: {av_offset_ms:.2f}ms offset (<1 frame)")
else:
    results.append(False)
    print(f"  {FAIL}A/V mismatch in container: {av_offset_ms:.2f}ms (>{FRAME_MS:.1f}ms = caption drift!)")

# ── Step 6: Word text vs ASS text match ─────────────────────────────────────
print("\n[6] Word-for-word text accuracy check...")
ass_words = []
for ev in events:
    parts  = ev.split(",,", 1)
    if len(parts) > 1:
        text = parts[1].strip()
        # Strip ASS override tags
        import re
        clean = re.sub(r'\{[^}]*\}', '', text).strip().split()
        if clean:
            ass_words.append(clean[0])  # first word in this line = active word

script_words = [w["word"] for w in words]
# Compare first N words
compare_n = min(5, len(ass_words), len(script_words))
all_match = True
for i in range(compare_n):
    sw = script_words[i].lower().strip(".,!?")
    aw = ass_words[i].lower().strip(".,!?") if i < len(ass_words) else ""
    match = sw == aw
    if not match:
        all_match = False
        print(f"  {FAIL}Word {i+1}: script='{sw}' vs ASS='{aw}' — MISMATCH!")

if all_match:
    results.append(True)
    print(f"  {PASS}Word text matches in ASS: '{' '.join(ass_words[:compare_n])}...'")
else:
    results.append(False)

# ── Step 7: Frame accuracy of caption timing ─────────────────────────────────
print("\n[7] Frame-accuracy of caption start times...")
frame_issues = 0
for ev in events[:10]:  # Check first 10 events
    parts = ev.split(",")
    if len(parts) < 2: continue
    start_str = parts[1].strip()
    try:
        h, m, s_cs = start_str.split(":")
        s, cs = s_cs.split(".")
        start_s = int(h)*3600 + int(m)*60 + int(s) + int(cs)/100.0
        frame_num = start_s * FPS
        # Frame-accurate means start_s should be a multiple of 1/FPS (33.33ms)
        nearest_frame = round(frame_num) / FPS
        error_ms = abs(start_s - nearest_frame) * 1000
        if error_ms > 1.0:  # More than 1ms off from a frame boundary
            frame_issues += 1
    except Exception:
        pass

if frame_issues == 0:
    results.append(True)
    print(f"  {PASS}All caption timestamps are frame-aligned (nearest 33.33ms boundary)")
else:
    results.append(False)
    print(f"  {FAIL}{frame_issues} caption events not on frame boundaries — will appear 1 frame off")

# ── Cleanup ───────────────────────────────────────────────────────────────────
shutil.rmtree(job, ignore_errors=True)

# ── Summary ───────────────────────────────────────────────────────────────────
passed = sum(results)
failed = len(results) - passed
print()
print("=" * 65)
print(f"RESULT: {passed}/{len(results)} passed | {failed} failed")
if not failed:
    print("ALL SYNC CHECKS PASS — captions are frame-accurate")
else:
    print("SYNC ISSUES FOUND — see FAIL items above")
sys.exit(0 if not failed else 1)
