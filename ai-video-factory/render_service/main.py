from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import logging
import subprocess
import wave
import contextlib
import os
import glob
import re
from PIL import Image
import shutil
import math

app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

TMP_DIR = Path("../tmp")
TMP_DIR.mkdir(exist_ok=True, parents=True)


# ---------------------------------------------------------
# Models
# ---------------------------------------------------------
class RenderVideoRequest(BaseModel):
    video_id: str
    srt_path: str
    audio_path: str
    resolution: str = "1080x1920"  # vertical 9:16
    fps: int = 30
    image_folder: Optional[str] = None   # if None -> solid color bg
    style: Optional[str] = "word_box"  # NEW: default subtitle style


class RenderVideoResponse(BaseModel):
    video_id: str
    video_path: str



# ---------------------------------------------------------
# Subtitle styles (ASS force_style presets)
# ---------------------------------------------------------
STYLE_PRESETS = {
    # Clean centered small white text (middle of screen)
    "center_small": (
        "subtitles='{srt}':force_style="
        "'Fontname=Segoe UI Semibold,"
        "Fontsize=28,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "Outline=2,"
        "Shadow=0,"
        "Alignment=10,"    # center-middle
        "MarginV=40'"
    ),

    # Purple boxed captions (center-middle)
    "purple_box_center": (
        "subtitles='{srt}':force_style="
        "'Fontname=Segoe UI Semibold,"
        "Fontsize=28,"
        "PrimaryColour=&H00FFFFFF,"   # white text
        "BackColour=&H801A1AFF,"      # ~50% transparent purple box
        "OutlineColour=&H801A1AFF,"   # same color for outline
        "BorderStyle=3,"              # box mode
        "Outline=1,"
        "Shadow=0,"
        "Alignment=10,"
        "MarginV=30'"
    ),

    # Purple boxed with Arial Black (center-middle)
    "purple_box_center2": (
        "subtitles='{srt}':force_style="
        "'Fontname=Arial Black,"
        "Fontsize=28,"
        "PrimaryColour=&H00FFFFFF,"
        "BackColour=&H801A1AFF,"
        "OutlineColour=&H801A1AFF,"
        "BorderStyle=3,"
        "Outline=1,"
        "Shadow=0,"
        "Alignment=10,"
        "MarginV=30'"
    ),

    # NEW: Bottom-center, bigger, white text with black box (TikTok style)
    "bottom_black_box": (
        "subtitles='{srt}':force_style="
        "'Fontname=Segoe UI Semibold,"
        "Fontsize=42,"                 # bigger
        "PrimaryColour=&H00FFFFFF,"    # white text
        "BackColour=&H80000000,"       # semi-transparent black box
        "OutlineColour=&HFF000000,"    # solid black outline
        "BorderStyle=3,"               # boxed subtitles
        "Outline=2,"
        "Shadow=0,"
        "Alignment=2,"                 # bottom-center
        "MarginV=120,"                 # lift above bottom edge
        "MarginL=40,"
        "MarginR=40'"
    ),
  "word_box": (
    "subtitles='{srt}':force_style='"
    "Fontname=Segoe UI Semibold, Fontsize=14,"
    "BorderStyle=3,"
    "BackColour=&H88101010,"
    "PrimaryColour=&H00FFFFFF,"
    "Outline=1,"
    "MarginV=60, MarginL=20, MarginR=20'"
),





}

# ---------------------------------------------------------
# Utils
# ---------------------------------------------------------
def run_ffmpeg(cmd: List[str], description: str) -> None:
    logger.info(f"[FFMPEG] {description}: {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        if proc.stderr:
            logger.info(
                f"[FFMPEG] {description} stderr: "
                f"{proc.stderr.decode('utf-8', errors='ignore')}"
            )
    except subprocess.CalledProcessError as e:
        logger.error(
            f"[FFMPEG] {description} failed: "
            f"{e.stderr.decode('utf-8', errors='ignore')}"
        )
        raise HTTPException(status_code=500, detail=f"{description} failed.")


def get_wav_duration(path: Path) -> float:
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Audio file not found: {path}")
    with contextlib.closing(wave.open(str(path), "rb")) as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def build_color_background_video(
    audio_path: Path,
    output_path: Path,
    resolution: str,
    fps: int,
) -> None:
    """
    Create a simple vertical video with a solid black background matching audio duration.
    """
    dur = get_wav_duration(audio_path)
    logger.info(f"[RENDER] Building color background video, duration={dur:.3f}s")

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=size={resolution}:rate={fps}:duration={dur}:color=black",
        "-i",
        str(audio_path),
        "-shortest",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(output_path),
    ]
    run_ffmpeg(cmd, "color background video")




def build_slideshow_video(
    image_folder: Path,
    audio_path: Path,
    output_path: Path,
    resolution: str,
    fps: int,
) -> None:
    """
    Build a slideshow video from all images in `image_folder`,
    with total duration matching the audio duration.
    Uses a frame-rate based approach (no concat durations),
    so we get frames from 0 -> audio_dur for sure.
    """
    if not image_folder.exists():
        raise HTTPException(status_code=400, detail=f"Image folder not found: {image_folder}")

    patterns = ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.PNG"]
    image_paths: List[Path] = []
    for pat in patterns:
        image_paths.extend(Path(image_folder).glob(pat))

    image_paths = sorted(image_paths)
    if not image_paths:
        raise HTTPException(status_code=400, detail=f"No images found in {image_folder}")

    audio_dur = get_wav_duration(audio_path)
    n = len(image_paths)

    # fps at which we feed images so that total duration ~= audio_dur
    # duration = n / img_fps  =>  img_fps = n / duration
    img_fps = n / audio_dur if audio_dur > 0 else 1.0
    logger.info(
        f"[RENDER] Building slideshow from {n} images, "
        f"audio duration={audio_dur:.3f}s, img_fps={img_fps:.4f}"
    )

    # Parse resolution like "1080x1920" -> w=1080, h=1920
    try:
        w_str, h_str = resolution.split("x")
        w, h = int(w_str), int(h_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resolution format: {resolution}. Use 'WIDTHxHEIGHT', e.g. '1080x1920'.",
        )

    # Temp folder with sequentially named JPG images
    tmp_slides_dir = TMP_DIR / f"slides_{os.getpid()}"
    tmp_slides_dir.mkdir(exist_ok=True)

    try:
        # Copy/convert images as 0001.jpg, 0002.jpg, ...
        for idx, img in enumerate(image_paths, start=1):
            target = tmp_slides_dir / f"{idx:04d}.jpg"  # always .jpg

            try:
                im = Image.open(img)
                rgb = im.convert("RGB")
                rgb.save(target, "JPEG", quality=95)
            except Exception:
                # If conversion fails, just copy the file but still name it .jpg
                shutil.copy(str(img), str(target))

        slideshow_no_audio = TMP_DIR / f"{output_path.stem}_silent.mp4"

        # Scale & pad to target size, then force output fps
        vf_filter = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
            f"format=yuv420p"
        )

        # 1) Build silent slideshow (duration ~= n / img_fps ~= audio_dur)
        cmd_slideshow = [
            "ffmpeg",
            "-y",
            "-framerate",
            f"{img_fps}",
            "-i",
            str(tmp_slides_dir / "%04d.jpg"),
            "-vf",
            vf_filter,
            "-r",
            str(fps),             # output fps
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            str(slideshow_no_audio),
        ]
        run_ffmpeg(cmd_slideshow, "slideshow video")

        # 2) Mux with audio, cut to exact audio duration
        cmd_mux = [
            "ffmpeg",
            "-y",
            "-i",
            str(slideshow_no_audio),
            "-i",
            str(audio_path),
            "-t",
            f"{audio_dur}",       # force total duration == audio
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output_path),
        ]
        run_ffmpeg(cmd_mux, "slideshow mux with audio")

    finally:
        # Clean temp images
        try:
            shutil.rmtree(tmp_slides_dir)
        except Exception:
            pass


def burn_subtitles(
    video_path: Path,
    subs_path: Path,
    output_path: Path,
    style: Optional[str] = None,
) -> None:
    """
    Burn subtitles (ASS or SRT) onto an existing video.
    If 'style' is provided and found in STYLE_PRESETS, use force_style.
    """
    if not video_path.exists():
        raise HTTPException(status_code=400, detail=f"Base video not found: {video_path}")
    if not subs_path.exists():
        raise HTTPException(status_code=400, detail=f"Subtitle file not found: {subs_path}")

    subs_escaped = subs_path.as_posix()  # safe on Windows with forward slashes

    if style and style in STYLE_PRESETS:
        vf = STYLE_PRESETS[style].format(srt=subs_escaped)
        logger.info(f"[RENDER] Using subtitle style preset: {style}")
    else:
        if style:
            logger.warning(f"[RENDER] Unknown style '{style}', falling back to basic subtitles")
        # basic fallback (no styling)
        vf = f"subtitles='{subs_escaped}'"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-c:a",
        "copy",
        str(output_path),
    ]
    run_ffmpeg(cmd, "burn subtitles")


def _srt_time_to_seconds(t: str) -> float:
    # "HH:MM:SS,mmm" -> seconds (float)
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def _sec_to_ass_time(sec: float) -> str:
    # seconds -> "H:MM:SS.cc" (centiseconds)
    if sec < 0:
        sec = 0.0
    cs = int(round(sec * 100))  # centiseconds
    total = cs / 100.0
    h = int(total // 3600)
    total -= h * 3600
    m = int(total // 60)
    total -= m * 60
    s = total
    return f"{h}:{m:02d}:{s:05.2f}"  # e.g. 0:00:03.50


def srt_to_ass(srt_path: Path, ass_path: Path, style_name: str = "PurpleCenter") -> None:
    """
    Convert a simple SRT file to an ASS file with a single style.
    All dialogue lines use that style.
    """
    if not srt_path.exists():
        raise HTTPException(status_code=400, detail=f"SRT file not found: {srt_path}")

    raw = srt_path.read_text(encoding="utf-8", errors="ignore")

    # Split into blocks separated by blank lines
    blocks = re.split(r"\n\s*\n", raw.strip())

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
Collisions: Normal
Timer: 100.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: {style_name},Segoe UI Semibold,28,&H00FFFFFF,&H00000000,&H801A1AFF,&H801A1AFF,0,0,0,0,100,100,0,0,3,1,0,10,20,20,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    out_lines = [header]

    for block in blocks:
        lines = [ln.strip("\r") for ln in block.splitlines() if ln.strip()]

        if len(lines) < 2:
            continue

        # lines[0] is index, ignore
        # lines[1] is timing
        timing = lines[1]
        m = re.match(
            r"(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)",
            timing,
        )
        if not m:
            continue

        start_str, end_str = m.group(1), m.group(2)
        start_sec = _srt_time_to_seconds(start_str)
        end_sec = _srt_time_to_seconds(end_str)

        if end_sec <= start_sec:
            continue

        start_ass = _sec_to_ass_time(start_sec)
        end_ass = _sec_to_ass_time(end_sec)

        # Remaining lines are text
        text = "\\N".join(lines[2:])  # \N = newline in ASS

        dialogue = (
            f"Dialogue: 0,{start_ass},{end_ass},{style_name},,"
            f"0,0,0,,{text}"
        )
        out_lines.append(dialogue)

    ass_path.write_text("\n".join(out_lines), encoding="utf-8")

# ---------------------------------------------------------
# Endpoint
# ---------------------------------------------------------
@app.post("/render-video", response_model=RenderVideoResponse)
def render_video(req: RenderVideoRequest):
    video_id = req.video_id
    audio_path = Path(req.audio_path)
    srt_path = Path(req.srt_path)

    logger.info(
        f"[RENDER] Rendering video for video_id={video_id}, "
        f"image_folder={req.image_folder}, style={req.style}"
    )

    base_video_path = TMP_DIR / f"{video_id}_base.mp4"
    final_video_path = TMP_DIR / f"{video_id}_final.mp4"

    # 1) Build base video (either color background or slideshow)
    if req.image_folder:
        image_folder = Path(req.image_folder)
        build_slideshow_video(
            image_folder=image_folder,
            audio_path=audio_path,
            output_path=base_video_path,
            resolution=req.resolution,
            fps=req.fps,
        )
    else:
        build_color_background_video(
            audio_path=audio_path,
            output_path=base_video_path,
            resolution=req.resolution,
            fps=req.fps,
        )

    # 2) Burn subtitles on top, using chosen style preset
    burn_subtitles(
        video_path=base_video_path,
        subs_path=srt_path,
        output_path=final_video_path,
        style=req.style,
    )

    logger.info(f"[RENDER] Final video at {final_video_path}")
    return RenderVideoResponse(
        video_id=video_id,
        video_path=str(final_video_path),
    )
