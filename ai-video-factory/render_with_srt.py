import json
import subprocess
import re
from pathlib import Path
import sys


def seconds_to_srt_ts(t: float) -> str:
    """
    Convert seconds (float) to SRT timestamp: HH:MM:SS,mmm
    """
    if t < 0:
        t = 0.0
    hours = int(t // 3600)
    minutes = int((t % 3600) // 60)
    seconds = int(t % 60)
    millis = int(round((t - int(t)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def sanitize_caption_text(text: str) -> str:
    """
    Cleanup text for subtitles: remove weird chars, collapse spaces.
    """
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    text = re.sub(r"[^A-Za-z0-9 .,!?\-']", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_srt_from_script(script: dict, srt_path: Path) -> int:
    """
    Build an SRT file from script['scenes'] using voice_text + timings.
    Returns number of entries written.
    """
    scenes = script.get("scenes", [])
    lines = []
    idx = 1

    for scene in scenes:
        raw_caption = (scene.get("voice_text") or "").strip()
        if not raw_caption:
            continue

        # Optional: shorten very long captions
        if len(raw_caption) > 180:
            raw_caption = raw_caption[:177] + "..."

        safe_caption = sanitize_caption_text(raw_caption)
        if not safe_caption:
            continue

        start = float(scene.get("start", 0.0))
        end = float(scene.get("end", start + 1.0))
        if end <= start:
            continue

        start_ts = seconds_to_srt_ts(start)
        end_ts = seconds_to_srt_ts(end)

        lines.append(str(idx))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(safe_caption)
        lines.append("")  # blank line

        idx += 1

    srt_path.write_text("\n".join(lines), encoding="utf-8")
    return idx - 1


def render_video_with_srt(
    script_path: Path,
    audio_path: Path,
    output_path: Path,
    resolution: str = "1080x1920",
    fps: int = 30,
) -> None:
    """
    - Reads script JSON
    - Creates an SRT file in the same folder as output video
    - Uses FFmpeg to render black bg + audio + burned SRT
    """
    script_path = script_path.resolve()
    audio_path = audio_path.resolve()
    output_path = output_path.resolve()

    out_dir = output_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # SRT will be: <output_stem>_captions.srt
    srt_path = out_dir / f"{output_path.stem}_captions.srt"

    # Load script JSON
    script = json.loads(script_path.read_text(encoding="utf-8"))

    entries = build_srt_from_script(script, srt_path)
    print(f"[render] Wrote {entries} subtitle entries to {srt_path}")

    if entries == 0:
        print("[render] WARNING: No subtitles were generated from script.")

    # We'll run ffmpeg from the output directory so we can use
    # simple filenames in the subtitles filter (no C:\ path issues).
    audio_rel = audio_path  # audio can stay absolute (not in a filter)
    srt_name = srt_path.name  # just the filename

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={resolution}:r={fps}",  # 0:v
        "-i", str(audio_rel),                           # 1:a
        "-vf", f"subtitles={srt_name}",
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-shortest",
        str(output_path),
    ]

    print("[render] Running FFmpeg:")
    print(" ".join(ffmpeg_cmd))

    # IMPORTANT: run ffmpeg in the output directory (cwd=out_dir)
    result = subprocess.run(
        ffmpeg_cmd,
        cwd=str(out_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        print("FFmpeg stdout:\n", result.stdout)
        print("FFmpeg stderr:\n", result.stderr)
        raise RuntimeError(f"FFmpeg failed with exit code {result.returncode}")

    print(f"[render] Done. Video written to {output_path}")


def main():
    if len(sys.argv) != 4:
        print(
            "Usage:\n"
            "  python render_with_srt.py <script.json> <audio.wav> <output.mp4>\n\n"
            "Example:\n"
            "  python render_with_srt.py script.json full.wav final.mp4"
        )
        sys.exit(1)

    script_path = Path(sys.argv[1])
    audio_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])

    if not script_path.exists():
        print(f"Error: script file not found: {script_path}")
        sys.exit(1)
    if not audio_path.exists():
        print(f"Error: audio file not found: {audio_path}")
        sys.exit(1)

    render_video_with_srt(script_path, audio_path, output_path)


if __name__ == "__main__":
    main()
