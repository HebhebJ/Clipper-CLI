import subprocess
from pathlib import Path
from typing import Dict, Any, List
import re  # 👈 add this

WINDOWS_FONT = r"C\:/Windows/Fonts/arial.ttf"
TMP = Path(__file__).resolve().parent.parent / "tmp"

def escape_drawtext_text(text: str) -> str:
    # Escape characters that break drawtext
    return (
        text
        .replace("\\", r"\\\\")
        .replace(":", r"\:")
        .replace("'", r"\'")
        .replace(",", r"\,")
    )

def render_video(video_id: str, script: Dict[str, Any], full_audio_path: Path) -> Path:
    output_path = TMP / f"{video_id}_final.mp4"

    scenes = script["scenes"]

    # Filters for top titles + bottom colorful captions
    filter_parts: List[str] = []

    for scene in scenes:
        # --- Top headline (on_screen_text) ---
        raw_title = scene.get("on_screen_text", "")
        start = float(scene["start"])
        end = float(scene["end"])

        if raw_title.strip():
            title_text = escape_drawtext_text(raw_title)

            title_draw = (
                "drawtext="
                f"fontfile='{WINDOWS_FONT}':"
                f"text='{title_text}':"
                f"x=(w-text_w)/2:"
                f"y=h*0.15:"                 # top area
                f"fontsize=48:"
                f"fontcolor=white@1.0:"
                f"enable='between(t,{start},{end})'"
            )

            filter_parts.append(title_draw)

        # --- Bottom colorful caption (voice_text) ---
        raw_caption = scene.get("voice_text", "") or ""
        if raw_caption.strip():
            # Optional: truncate super long captions so they don't overflow
            if len(raw_caption) > 160:
                raw_caption = raw_caption[:157] + "..."

            caption_text = escape_drawtext_text(raw_caption)

            caption_draw = (
                "drawtext="
                f"fontfile='{WINDOWS_FONT}':"
                f"text='{caption_text}':"
                f"x=(w-text_w)/2:"
                f"y=h*0.80:"                 # bottom area
                f"fontsize=40:"
                f"fontcolor=yellow@1.0:"     # colorful subtitles
                f"box=1:"
                f"boxcolor=black@0.4:"
                f"boxborderw=10:"
                f"enable='between(t,{start},{end})'"
            )

            filter_parts.append(caption_draw)

    # Build filtergraph: [0:v] ... [vout]
    if filter_parts:
        filter_complex = "[0:v]" + ",".join(filter_parts) + "[vout]"
    else:
        filter_complex = "[0:v]null[vout]"

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", "color=c=black:s=1080x1920:r=30",    # 0:v
        "-i", str(full_audio_path),                # 1:a
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-shortest",                               # stop when audio ends
        str(output_path),
    ]

    print("[render]", " ".join(cmd))

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        print("FFmpeg stdout:\n", result.stdout)
        print("FFmpeg stderr:\n", result.stderr)
        raise RuntimeError(f"FFmpeg failed with code {result.returncode}")

    return output_path
