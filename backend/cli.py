"""
THE INNER CITADEL — CLI Tool
Generate Stoic videos directly from the command line.

Usage:
    # Single video
    python cli.py --topic "Overcoming Fear"

    # With options
    python cli.py --topic "Memento Mori" --length medium --ratio 16:9 --voice bm_george

    # Dry run (generate script only, no video)
    python cli.py --topic "Discipline is Freedom" --dry-run

    # Batch from file (one topic per line)
    python cli.py --batch topics.txt

    # Random topic
    python cli.py --random
"""

import argparse
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

GREEN  = "\033[92m"
BLUE   = "\033[94m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
CYAN   = "\033[96m"


def banner():
    print(f"""
{CYAN}{BOLD}
 ████████╗██╗  ██╗███████╗
    ██╔══╝██║  ██║██╔════╝
    ██║   ███████║█████╗
    ██║   ██╔══██║██╔══╝
    ██║   ██║  ██║███████╗
    ╚═╝   ╚═╝  ╚═╝╚══════╝
 INNER CITADEL — CLI Pipeline
{RESET}""")


def run_pipeline(topic: str, length: str, aspect_ratio: str, voice: str,
                 fps: int, dry_run: bool, output_dir: str) -> dict:
    """Runs the full generation pipeline for a single topic."""
    import time

    print(f"\n{BOLD}Topic:{RESET} {topic}")
    print(f"{BOLD}Length:{RESET} {length} | {BOLD}Ratio:{RESET} {aspect_ratio} | {BOLD}Voice:{RESET} {voice}")
    print()

    job_dir = Path(output_dir) / f"cli_{topic[:30].replace(' ', '_').lower()}_{int(time.time())}"
    job_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Script Generation ─────────────────────────────
    print(f"{BLUE}[1/9]{RESET} Generating script with LLM...")
    sys.path.insert(0, str(Path(__file__).parent))
    from generator.script_engine import ScriptEngine
    script_engine = ScriptEngine()
    script_data = script_engine.generate_script(topic=topic, length=length)

    script_path = job_dir / "script.json"
    script_path.write_text(json.dumps(script_data, indent=2), encoding="utf-8")
    print(f"  {GREEN}✅ Script:{RESET} '{script_data['title']}' — {len(script_data['beats'])} beats")
    print(f"  {CYAN}Saved:{RESET} {script_path}")

    # Preview beats
    print(f"\n  {BOLD}Script Preview:{RESET}")
    for beat in script_data["beats"]:
        emotion = beat.get("emotion", "?")
        print(f"  [{beat['id']:2d}] {CYAN}{emotion:12s}{RESET} — {beat['text']}")

    if dry_run:
        print(f"\n{YELLOW}─── DRY RUN MODE: Stopping after script generation ───{RESET}")
        print(f"{GREEN}✅ Script saved to:{RESET} {script_path}")
        return {"script": script_data, "job_dir": str(job_dir)}

    # ── Step 2: TTS ───────────────────────────────────────────
    print(f"\n{BLUE}[2/9]{RESET} Synthesizing voice (Kokoro-82M)...")
    from audio.tts_engine import TTSEngine
    tts = TTSEngine(voice=voice)
    audio_path = str(job_dir / "audio.wav")
    tts.synthesize(script_data=script_data, output_path=audio_path)
    print(f"  {GREEN}✅ Audio:{RESET} {audio_path}")

    # ── Step 3: Forced Alignment ──────────────────────────────
    print(f"\n{BLUE}[3/9]{RESET} Running WhisperX alignment...")
    from alignment.align_engine import AlignmentEngine
    aligner = AlignmentEngine()
    word_timeline = aligner.generate_word_timestamps(audio_path=audio_path)
    print(f"  {GREEN}✅ Aligned:{RESET} {len(word_timeline)} words")

    # ── Step 4: Timeline Assembly ─────────────────────────────
    print(f"\n{BLUE}[4/9]{RESET} Building master timeline...")
    from timeline.timeline_engine import TimelineEngine
    timeline_engine = TimelineEngine()
    master_timeline = timeline_engine.build(script_data=script_data, word_timeline=word_timeline)
    timeline_path = job_dir / "timeline.json"
    timeline_path.write_text(json.dumps(master_timeline, indent=2), encoding="utf-8")
    print(f"  {GREEN}✅ Timeline:{RESET} {master_timeline['duration']:.2f}s, {len(master_timeline['segments'])} segments")

    # ── Step 5: Media Retrieval ───────────────────────────────
    print(f"\n{BLUE}[5/9]{RESET} Fetching cinematic footage...")
    from embeddings.faiss_engine import FAISSEngine
    from media.media_engine import FreeMediaEngine
    faiss_engine = FAISSEngine()
    media_engine = FreeMediaEngine(
        pexels_key=os.getenv("PEXELS_API_KEY", ""),
        pixabay_key=os.getenv("PIXABAY_API_KEY", ""),
        faiss_engine=faiss_engine,
    )
    media_clips = []
    for seg in master_timeline["segments"]:
        duration = seg["audio_end"] - seg["audio_start"]
        clip = media_engine.fetch_best_clip(
            script_text=seg["text"],
            queries=seg.get("visual_keywords", [seg["text"]]),
            aspect_ratio=aspect_ratio,
            job_dir=str(job_dir),
            segment_id=seg["id"],
        )
        media_clips.append({"path": clip, "duration": duration, "segment": seg})
        print(f"  {GREEN}✅{RESET} Segment {seg['id']}: {clip}")

    # ── Step 6: Video Engine ──────────────────────────────────
    print(f"\n{BLUE}[6/9]{RESET} Compositing video (PIL LANCZOS Ken Burns)...")
    from video.video_engine import VideoEngine
    video_engine = VideoEngine(aspect_ratio=aspect_ratio, fps=fps)
    raw_video = str(job_dir / "raw_video.mp4")
    video_engine.compose(clips=media_clips, output_path=raw_video, timeline=master_timeline)
    print(f"  {GREEN}✅ Video:{RESET} {raw_video}")

    # ── Step 7: Captions ──────────────────────────────────────
    print(f"\n{BLUE}[7/9]{RESET} Generating ASS karaoke subtitles...")
    from captions.caption_engine import CaptionEngine
    w, h = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}.get(aspect_ratio, (1080, 1920))
    cap_engine = CaptionEngine(resolution=(w, h))
    captions_path = str(job_dir / "captions.ass")
    cap_engine.build_ass_subtitles(timeline=master_timeline, output_path=captions_path)
    print(f"  {GREEN}✅ Captions:{RESET} {captions_path}")

    # ── Step 8: Audio Mix ─────────────────────────────────────
    print(f"\n{BLUE}[8/9]{RESET} Mixing audio with emotion-based ducking...")
    from audio.audio_mixer import AudioMixer
    mixer = AudioMixer()
    mixed_audio = str(job_dir / "audio_mixed.wav")
    bgm_files = list((Path(__file__).parent / "assets" / "bgm").glob("*.mp3"))
    bgm_path = str(bgm_files[0]) if bgm_files else audio_path
    mixer.mix(voice_path=audio_path, bgm_path=bgm_path, timeline=master_timeline, output_path=mixed_audio)
    print(f"  {GREEN}✅ Mixed:{RESET} {mixed_audio}")

    # ── Step 9: Final Render ──────────────────────────────────
    print(f"\n{BLUE}[9/9]{RESET} Final FFmpeg render + validation...")
    import subprocess
    final_video = str(job_dir / "final_video.mp4")
    subprocess.run([
        "ffmpeg", "-i", raw_video, "-i", mixed_audio,
        "-vf", f"ass={captions_path},fps={fps}",
        "-c:v", "libx264", "-preset", "slow", "-b:v", "8M",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", "-shortest",
        final_video, "-y"
    ], check=True, capture_output=True)

    # Thumbnail
    thumb = str(job_dir / "thumbnail.jpg")
    subprocess.run(["ffmpeg", "-i", final_video, "-ss", "5", "-vframes", "1", "-q:v", "2", thumb, "-y"],
                   capture_output=True)

    print(f"  {GREEN}✅ FINAL VIDEO:{RESET} {final_video}")

    return {
        "job_dir": str(job_dir),
        "final_video": final_video,
        "captions": captions_path,
        "timeline": str(timeline_path),
        "thumbnail": thumb,
        "duration": master_timeline["duration"],
        "title": script_data["title"],
    }


def main():
    banner()
    parser = argparse.ArgumentParser(
        description="THE INNER CITADEL — Autonomous Stoic Video Generator (CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--topic",    type=str,   help="Video topic (e.g. 'Overcoming Fear')")
    parser.add_argument("--length",   type=str,   default="short", choices=["short", "medium"],
                        help="Video length: short (~35s) or medium (~60s)")
    parser.add_argument("--ratio",    type=str,   default="9:16",  choices=["9:16", "16:9", "1:1"],
                        help="Aspect ratio")
    parser.add_argument("--voice",    type=str,   default="af_bella",
                        help="Kokoro voice: af_bella|bm_george|am_adam|bf_emma")
    parser.add_argument("--fps",      type=int,   default=60,
                        help="Output FPS (default: 60)")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Generate script only, no video render")
    parser.add_argument("--random",   action="store_true",
                        help="Pick a random Stoic topic automatically")
    parser.add_argument("--batch",    type=str,   metavar="FILE",
                        help="Process multiple topics from a text file (one per line)")
    parser.add_argument("--output",   type=str,   default="./exports",
                        help="Output directory (default: ./exports)")

    args = parser.parse_args()

    topics = []

    if args.random:
        from generator.script_engine import get_random_topic
        topics = [get_random_topic()]
        print(f"{CYAN}Random topic selected:{RESET} {topics[0]}")
    elif args.batch:
        batch_file = Path(args.batch)
        if not batch_file.exists():
            print(f"{RED}❌ Batch file not found: {args.batch}{RESET}")
            sys.exit(1)
        topics = [line.strip() for line in batch_file.read_text().splitlines() if line.strip()]
        print(f"{CYAN}Batch mode:{RESET} {len(topics)} topics from {args.batch}")
    elif args.topic:
        topics = [args.topic]
    else:
        parser.print_help()
        print(f"\n{YELLOW}Example: python cli.py --topic \"Overcoming Fear\"{RESET}\n")
        sys.exit(1)

    results = []
    for i, topic in enumerate(topics, 1):
        if len(topics) > 1:
            print(f"\n{BOLD}{'═'*50}{RESET}")
            print(f"{BOLD}Processing {i}/{len(topics)}: {topic}{RESET}")
            print(f"{BOLD}{'═'*50}{RESET}")
        try:
            result = run_pipeline(
                topic=topic,
                length=args.length,
                aspect_ratio=args.ratio,
                voice=args.voice,
                fps=args.fps,
                dry_run=args.dry_run,
                output_dir=args.output,
            )
            results.append({"topic": topic, "status": "success", **result})
        except Exception as e:
            print(f"\n{RED}❌ Failed for '{topic}': {e}{RESET}")
            results.append({"topic": topic, "status": "failed", "error": str(e)})

    # Final summary for batch
    if len(topics) > 1:
        print(f"\n{BOLD}{'═'*50}{RESET}")
        print(f"{BOLD}BATCH COMPLETE{RESET}")
        for r in results:
            status = f"{GREEN}✅{RESET}" if r["status"] == "success" else f"{RED}❌{RESET}"
            print(f"  {status} {r['topic']}")
        success = sum(1 for r in results if r["status"] == "success")
        print(f"\n{GREEN}{success}{RESET}/{len(topics)} videos generated successfully")


if __name__ == "__main__":
    main()
