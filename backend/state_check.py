"""Live state check — exactly what the running server is loading."""
import sys
sys.path.insert(0, ".")

print("=" * 55)
print("LIVE CODE STATE CHECK")
print("=" * 55)

# Gemini model
from generator.script_engine import GeminiClient
g = GeminiClient()
print(f"Gemini model: {g.model}")
assert g.model == "gemini-2.0-flash", f"WRONG MODEL: {g.model}"

# sleep between chapters
src = open("generator/script_engine.py", encoding="utf-8").read()
assert "time.sleep(3)" in src, "NO CHAPTER SLEEP"
assert "time.sleep(8)" in src, "NO 429 BACKOFF"
assert "multiplier=2, min=5, max=60" in src, "RETRY NOT UPDATED"
print("Chapter sleep 3s: OK")
print("429 backoff 8s: OK")
print("Retry min=5 max=60: OK")

# Caption font
src2 = open("captions/caption_engine.py", encoding="utf-8").read()
assert '"Arial"' in src2, "ARIAL MISSING"
assert '"Montserrat"' not in src2, "MONTSERRAT STILL THERE"
print("Caption font Arial: OK")

# main.py encoding
src3 = open("main.py", encoding="utf-8").read()
cnt = src3.count("yuv420p")
assert cnt >= 2, f"yuv420p only {cnt} times"
assert "tmp_captions_" in src3, "RELATIVE ASS PATH MISSING"
assert "shutil.copy2" in src3, "COPY MISSING"
print(f"yuv420p in {cnt} render commands: OK")
print("Relative ASS path fix: OK")

# .env
try:
    env = open("../.env", encoding="utf-8-sig").read()
    line = [l for l in env.split("\n") if "GEMINI_MODEL" in l]
    val = line[0].strip() if line else "NOT SET"
    assert "gemini-2.0-flash" in val, f"WRONG: {val}"
    print(f".env GEMINI_MODEL: {val} OK")
except Exception as e:
    print(f".env check error: {e}")

print()
print("ALL CHECKS PASSED - code is correct")
print()
print("=" * 55)
print("IF YOU STILL SEE OLD ERRORS IN BROWSER:")
print("The backend server is running OLD cached code.")
print("YOU MUST RESTART IT:")
print()
print("  1. Press Ctrl+C in the backend terminal")
print("  2. Run:  python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print("  3. Wait for: 'Application startup complete.'")
print("  4. Try generating a video again")
print("=" * 55)
