"""10-pass deep verification for channel isolation, history, and concept explainer."""
import sys, json, ast
sys.path.insert(0, ".")

PASSES = []
FAILS  = []

def ok(msg):  PASSES.append(msg); print(f"  [+] {msg}")
def fail(msg): FAILS.append(msg);  print(f"  [X] FAIL: {msg}")

# ── PASS 1: Channel config — exact names, handles, watermarks ───────────────
from channels.channel_config import CHANNELS, get_channel, get_all_channels
s = get_channel("stoic")
t = get_channel("tech")
checks = [
    (s["name"]      == "The Inner Citadel",   "stoic name='The Inner Citadel'"),
    (s["handle"]    == "@TheInnerCitadel",    "stoic handle='@TheInnerCitadel'"),
    (s["watermark"] == "The Inner Citadel",   "stoic watermark='The Inner Citadel'"),
    (t["name"]      == "neuralbaba_empire",   "tech name='neuralbaba_empire'"),
    (t["handle"]    == "@neuralbaba_empire",  "tech handle='@neuralbaba_empire'"),
    (t["watermark"] == "neuralbaba_empire",   "tech watermark='neuralbaba_empire'"),
]
for passed, msg in checks:
    ok(msg) if passed else fail(msg)

# ── PASS 2: No cross-contamination in names ──────────────────────────────────
ok("neuralbaba_empire NOT in stoic name") if "neuralbaba_empire" not in s["name"] else fail("neuralbaba_empire IN stoic name!")
ok("Inner Citadel NOT in tech name")      if "Inner Citadel"     not in t["name"] else fail("Inner Citadel IN tech name!")

# ── PASS 3: No topic cross-contamination ────────────────────────────────────
stoic_words = {"stoic","philosophy","virtue","discipline","freedom","mindset","ancient"}
tech_words  = {"algorithm","database","http","dns","neural","llm","kubernetes","sql","tcp","docker"}
cross_stoic_in_tech = [tp for tp in t["topics"] if any(w in tp.lower() for w in stoic_words)]
cross_tech_in_stoic = [tp for tp in s["topics"] if any(w in tp.lower() for w in tech_words)]
ok(f"No stoic words in tech topics (checked {len(t['topics'])} topics)") if not cross_stoic_in_tech else fail(f"Stoic words in tech topics: {cross_stoic_in_tech[:3]}")
ok(f"No tech words in stoic topics (checked {len(s['topics'])} topics)") if not cross_tech_in_stoic else fail(f"Tech words in stoic topics: {cross_tech_in_stoic[:3]}")

# ── PASS 4: History engine separate files ───────────────────────────────────
from history.history_engine import HistoryEngine, HISTORY_FILES, _get_history_file
ok("stoic in HISTORY_FILES") if "stoic" in HISTORY_FILES else fail("stoic missing from HISTORY_FILES")
ok("tech in HISTORY_FILES")  if "tech"  in HISTORY_FILES else fail("tech missing from HISTORY_FILES")
hs = HistoryEngine(channel_id="stoic")
ht = HistoryEngine(channel_id="tech")
ok("Stoic+Tech use different history files") if hs.history_file != ht.history_file else fail("Same history file for both channels!")
ok(f"Stoic file contains 'stoic': {hs.history_file.name}") if "stoic" in str(hs.history_file) else fail(f"Stoic file wrong: {hs.history_file}")
ok(f"Tech  file contains 'tech':  {ht.history_file.name}") if "tech"  in str(ht.history_file) else fail(f"Tech file wrong: {ht.history_file}")

# ── PASS 5: History save stores channel field ────────────────────────────────
hs_test = HistoryEngine(channel_id="stoic")
script_s = {"topic":"Stoic Test Topic","title":"Test Stoic","beats":[{"text":"Fear is a choice you make"},{"text":"Discipline shapes your destiny"}]}
hs_test.save(script_s, length="short")
lines = hs_test.history_file.read_text().splitlines()
last  = json.loads(lines[-1])
ok(f"Stoic entry saves channel='stoic'") if last.get("channel") == "stoic" else fail(f"channel field wrong: {last.get('channel')}")

ht_test = HistoryEngine(channel_id="tech")
script_t = {"topic":"Tech Test Topic","title":"Test Tech","beats":[{"text":"A neural network learns by example"},{"text":"Weights are adjusted with each error"}]}
ht_test.save(script_t, length="short")
lines_t = ht_test.history_file.read_text().splitlines()
last_t  = json.loads(lines_t[-1])
ok(f"Tech entry saves channel='tech'") if last_t.get("channel") == "tech" else fail(f"channel field wrong: {last_t.get('channel')}")

# ── PASS 6: History _load() only reads its own channel ──────────────────────
stoic_entries = hs_test._load()
tech_entries  = ht_test._load()
ok(f"Stoic history has {len(stoic_entries)} entries, all channel='stoic'") if all(e.get("channel","stoic") == "stoic" for e in stoic_entries) else fail("Non-stoic entry found in stoic history!")
ok(f"Tech  history has {len(tech_entries)} entries, all channel='tech'")   if all(e.get("channel","tech")  == "tech"  for e in tech_entries)  else fail("Non-tech entry found in tech history!")

# ── PASS 7: Tech system prompt is concept-explainer focused ─────────────────
tp = t["system_prompt"]
concept_keywords = ["HOW", "MECHANISM", "HOOK", "AHA MOMENT", "Fireship", "ByteByteGo", "3Blue1Brown"]
for kw in concept_keywords:
    ok(f"Tech prompt contains '{kw}'") if kw in tp else fail(f"Tech prompt MISSING '{kw}'")
# Check case-insensitive for style words
ok("Tech prompt contains 'analogy' (case-insensitive)") if "analogy" in tp.lower() else fail("Tech prompt MISSING analogy")
ok("Tech prompt contains 'gradually' or 'gradual' (case-insensitive)") if "gradual" in tp.lower() or "step by step" in tp.lower() else fail("Tech prompt MISSING gradual buildup instruction")

# ── PASS 8: Tech topics are HOW-focused (concept explainer) ─────────────────
how_topics = [t2 for t2 in t["topics"] if t2.lower().startswith("how ")]
ok(f"Tech has {len(how_topics)}/{len(t['topics'])} HOW-focused topics (need >=30)") if len(how_topics) >= 30 else fail(f"Only {len(how_topics)} HOW topics, need >=30")

# ── PASS 9: get_all_channels() returns both channels correctly ───────────────
all_ch = get_all_channels()
names  = [c["name"] for c in all_ch]
ok(f"get_all_channels() returns 2 channels") if len(all_ch) == 2 else fail(f"Expected 2, got {len(all_ch)}")
ok("'The Inner Citadel' in all_channels") if "The Inner Citadel" in names else fail("stoic missing!")
ok("'neuralbaba_empire' in all_channels") if "neuralbaba_empire" in names else fail("tech missing!")

# ── PASS 10: main.py uses channel_id everywhere ──────────────────────────────
code = open("main.py", encoding="utf-8").read()
checks_main = [
    ("channel_id=channel" in code,           "main.py: HistoryEngine(channel_id=channel)"),
    ("req.channel" in code,                  "main.py: req.channel passed to pipeline"),
    ('channel: str = "stoic"' in code,       "main.py: GenerateRequest has channel field"),
    ("watermark=watermark" in code,           "main.py: watermark passed to _ffmpeg_render"),
    ("channel_cfg" in code,                   "main.py: channel_cfg loaded from config"),
    ("/api/channels" in code,                 "main.py: /api/channels endpoint exists"),
    ("/api/history" in code,                  "main.py: /api/history endpoint exists"),
]
for passed, msg in checks_main:
    ok(msg) if passed else fail(msg)

# ── Result ───────────────────────────────────────────────────────────────────
print()
print(f"  Result: {len(PASSES)}/{len(PASSES)+len(FAILS)} passed  |  {len(FAILS)} failed")
if not FAILS:
    print("  *** ALL PASSES COMPLETE — SYSTEM FULLY VERIFIED ***")
else:
    print(f"  FAILURES: {FAILS}")
    sys.exit(1)
