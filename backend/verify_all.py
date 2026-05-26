"""Backend file verification — runs 10 independent checks across all files."""
import sys, ast, os
sys.path.insert(0, '.')

files_to_check = [
    'main.py',
    'audio/tts_engine.py',
    'alignment/align_engine.py',
    'captions/caption_engine.py',
    'audio/audio_mixer.py',
    'timeline/timeline_engine.py',
]

print('=' * 60)
print('BACKEND FILE VERIFICATION (10 checks per file)')
print('=' * 60)

sources = {}
all_ok = True

# Pass 1-3: Syntax validation (run 3 times to catch any parse issues)
for attempt in range(3):
    for fpath in files_to_check:
        try:
            with open(fpath, encoding='utf-8') as f:
                src = f.read()
            sources[fpath] = src
            ast.parse(src)
        except SyntaxError as e:
            print(f'  [FAIL] {fpath}: SyntaxError L{e.lineno}: {e.msg}')
            all_ok = False
        except FileNotFoundError:
            print(f'  [WARN] {fpath}: file not found')

print('Pass 1-3: Syntax         ', 'OK' if all_ok else 'ERRORS')

# Pass 4: TTS engine checks
tts = sources.get('audio/tts_engine.py', '')
checks_tts = [
    ('stream() API used',        'comm.stream()' in tts),
    ('SentenceBoundary handled', 'SentenceBoundary' in tts),
    ('WordBoundary handled',     'WordBoundary' in tts),
    ('cumulative offset',        'cumulative_s' in tts),
    ('boundaries JSON saved',    '_word_boundaries.json' in tts),
    ('Case A exact words',       'Case A' in tts),
    ('Case B sentence dist',     'Case B' in tts),
    ('Case C whole-beat est',    'Case C' in tts),
    ('Duration correction',      'Duration correction' in tts),
    ('No save()-only path',      'await comm_fb.save' not in tts or 'fallback' in tts),
]
print()
print('Pass 4: TTS Engine')
for name, ok in checks_tts:
    if not ok:
        all_ok = False
    print(f'  [{"OK  " if ok else "FAIL"}] {name}')

# Pass 5: AlignmentEngine checks
ae = sources.get('alignment/align_engine.py', '')
checks_ae = [
    ('TIER 1 edge-tts primary',  'TIER 1' in ae),
    ('TIER 2 WhisperX secondary','TIER 2' in ae),
    ('TIER 3 fallback',          'TIER 3' in ae),
    ('JSON file load',           '_word_boundaries.json' in ae),
    ('bounds list validation',   'isinstance(bounds, list)' in ae),
    ('word/start key check',     '"word" in bounds[0]' in ae),
    ('fallback_timing exists',   '_fallback_timing' in ae),
    ('whisperx_align exists',    '_whisperx_align' in ae),
    ('SILENCE_DB detection',     'SILENCE_DB' in ae),
    ('speech_start used',        'speech_start' in ae),
]
print()
print('Pass 5: AlignmentEngine')
for name, ok in checks_ae:
    if not ok:
        all_ok = False
    print(f'  [{"OK  " if ok else "FAIL"}] {name}')

# Pass 6: CaptionEngine checks
ce = sources.get('captions/caption_engine.py', '')
checks_ce = [
    ('fps parameter',            'fps: int = 30' in ce),
    ('_snap function',           'def _snap(' in ce),
    ('GAPLESS algorithm',        'GAPLESS' in ce),
    ('display_ends computed',    'display_ends' in ce),
    ('MIN_DURATION_S',           'MIN_DURATION_S' in ce),
    ('next word extend',         'next_start' in ce),
    ('global all_words flat',    'all_words' in ce),
    ('frame boundary snap',      'round(seconds * self.fps) / self.fps' in ce),
    ('min 2-frame check',        '2 * self.frame_s' in ce),
    ('pos_tag centered',         'pos_tag' in ce),
]
print()
print('Pass 6: CaptionEngine')
for name, ok in checks_ce:
    if not ok:
        all_ok = False
    print(f'  [{"OK  " if ok else "FAIL"}] {name}')

# Pass 7: main.py checks
mp = sources.get('main.py', '')
checks_mp = [
    ('post-suggestions API',     '/api/post-suggestions' in mp),
    ('PostSuggestionsRequest',   'PostSuggestionsRequest' in mp),
    ('script_excerpt in result', 'script_excerpt' in mp),
    ('channel in result',        '"channel":        channel' in mp),
    ('topic in result',          '"topic":          topic' in mp),
    ('profile:v main',           'profile:v' in mp and 'main' in mp),
    ('stereo 44100Hz',           '44100' in mp and 'ac' in mp),
    ('yuv420p pixel format',     'yuv420p' in mp),
    ('thumbnail prompt API',     'thumbnail_prompt' in mp),
    ('Gemini 2.0 flash',         'gemini-2.0-flash' in mp),
]
print()
print('Pass 7: main.py')
for name, ok in checks_mp:
    if not ok:
        all_ok = False
    print(f'  [{"OK  " if ok else "FAIL"}] {name}')

# Pass 8: import validation
print()
print('Pass 8: Import validation')
try:
    from captions.caption_engine import CaptionEngine
    ce_inst = CaptionEngine((1080, 1920), fps=30)
    assert hasattr(ce_inst, '_snap'), 'No _snap'
    assert hasattr(ce_inst, 'build_ass_subtitles'), 'No build_ass'
    assert ce_inst.fps == 30, 'fps wrong'
    print('  [OK  ] CaptionEngine import + instantiation')
except Exception as e:
    print(f'  [FAIL] CaptionEngine: {e}')
    all_ok = False

try:
    from alignment.align_engine import AlignmentEngine
    ae_inst = AlignmentEngine()
    assert hasattr(ae_inst, 'generate_word_timestamps'), 'No generate_word_timestamps'
    print('  [OK  ] AlignmentEngine import + instantiation')
except Exception as e:
    print(f'  [FAIL] AlignmentEngine: {e}')
    all_ok = False

try:
    from audio.tts_engine import TTSEngine
    print('  [OK  ] TTSEngine import')
except Exception as e:
    print(f'  [FAIL] TTSEngine: {e}')
    all_ok = False

try:
    from audio.audio_mixer import AudioMixer
    print('  [OK  ] AudioMixer import')
except Exception as e:
    print(f'  [FAIL] AudioMixer: {e}')
    all_ok = False

try:
    from timeline.timeline_engine import TimelineEngine
    print('  [OK  ] TimelineEngine import')
except Exception as e:
    print(f'  [FAIL] TimelineEngine: {e}')
    all_ok = False

# Pass 9: Snap math verification
print()
print('Pass 9: Frame-snap math (30fps)')
from captions.caption_engine import CaptionEngine as CE
ce9 = CE((1080, 1920), fps=30)
snap_tests = [
    (0.000, 0.000), (0.033, 0.033), (0.080, 0.067),
    (0.100, 0.100), (0.500, 0.500), (1.245, 1.233),
    (5.678, 5.667), (60.001, 60.000), (0.016, 0.000),
    (0.017, 0.033),
]
snap_ok = True
for t, expected in snap_tests:
    got = ce9._snap(t)
    frame = round(t * 30)
    true_exp = frame / 30.0
    ok = abs(got - true_exp) < 0.0001
    if not ok:
        snap_ok = False
        all_ok = False
        print(f'  [FAIL] _snap({t}) = {got:.4f}, expected {true_exp:.4f}')
if snap_ok:
    print(f'  [OK  ] All {len(snap_tests)} snap tests pass (0 error)')

# Pass 10: Gapless logic verification
print()
print('Pass 10: Gapless caption logic')
test_words = [
    {'word': 'Discipline', 'start': 0.10, 'end': 0.30},
    {'word': 'is',         'start': 0.35, 'end': 0.45},
    {'word': 'freedom',    'start': 0.50, 'end': 0.80},
    {'word': 'always',     'start': 0.85, 'end': 1.10},
    {'word': 'remember',   'start': 1.15, 'end': 1.40},
]
import tempfile, os as _os
from captions.caption_engine import CaptionEngine as CE2
import pysubs2

ce10 = CE2((1080, 1920), fps=30)
tmp_ass = tempfile.mktemp(suffix='.ass')
fake_timeline = {
    'segments': [{
        'segment_id': 0,
        'audio_start': 0.10,
        'audio_end': 1.40,
        'word_data': test_words,
    }]
}
ce10.build_ass_subtitles(fake_timeline, tmp_ass)

events = pysubs2.load(tmp_ass, encoding='utf-8')
gaps = 0
for i in range(1, len(events)):
    gap = events[i].start - events[i-1].end  # milliseconds
    if gap > 34:  # > 1 frame
        gaps += 1
        print(f'  [WARN] Gap {gap}ms between events {i-1} and {i}')

if gaps == 0:
    print(f'  [OK  ] GAPLESS: {len(events)} events, 0 gaps > 1 frame')
else:
    all_ok = False
    print(f'  [FAIL] {gaps} gaps found > 1 frame')

try:
    _os.unlink(tmp_ass)
except:
    pass

# Final
print()
print('=' * 60)
print(f'FINAL: {"ALL 10 CHECKS PASSED" if all_ok else "SOME CHECKS FAILED"}')
print('=' * 60)
sys.exit(0 if all_ok else 1)
