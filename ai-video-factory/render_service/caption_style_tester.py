import argparse
import subprocess
from pathlib import Path
import shutil

TMP_DIR = Path("../tmp")
TMP_DIR.mkdir(exist_ok=True)

# ----------------------------------------------------------
#  STYLES (you can add as many as you want)
# ----------------------------------------------------------
STYLE_PRESETS = {

    # -------------------------------------------------------------
    # CLEAN / BASIC
    # -------------------------------------------------------------
    "clean_outline": (
        "subtitles={srt}:force_style='"
        "Fontname=Arial Black, Fontsize=36,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000, Outline=3,"
        "Shadow=0, Alignment=2, MarginV=80'"
    ),

    "clean_thin": (
        "subtitles={srt}:force_style='"
        "Fontname=Segoe UI Semibold, Fontsize=34,"
        "PrimaryColour=&H00FFFFFF,"
        "Outline=1, Shadow=0,"
        "Alignment=2, MarginV=85'"
    ),


    # -------------------------------------------------------------
    # BOXED CAPTIONS
    # -------------------------------------------------------------
    "soft_box": (
        "subtitles={srt}:force_style='"
        "Fontname=Arial Black, Fontsize=34,"
        "BorderStyle=3, BackColour=&H70111111,"
        "PrimaryColour=&H00FFFFFF, Outline=0,"
        "Alignment=2, MarginV=90'"
    ),

    "black_box": (
        "subtitles={srt}:force_style='"
        "Fontname=Arial Black, Fontsize=34,"
        "BorderStyle=3, BackColour=&HAA000000,"
        "PrimaryColour=&H00FFFFFF, Outline=0,"
        "Alignment=2, MarginV=80'"
    ),

    "white_box": (
        "subtitles={srt}:force_style='"
        "Fontname=Arial Black, Fontsize=34,"
        "BorderStyle=3, BackColour=&H80FFFFFF,"
        "PrimaryColour=&H00000000, Outline=0,"
        "Alignment=2, MarginV=80'"
    ),

    "yellow_box": (
        "subtitles={srt}:force_style='"
        "Fontname=Arial Black, Fontsize=34,"
        "BorderStyle=3,"
        "BackColour=&HAA222222,"
        "PrimaryColour=&H0000FFFF, Outline=0,"
        "Alignment=2, MarginV=80'"
    ),

    # full width bar (TikTok style)
    "full_bar": (
        "subtitles={srt}:force_style='"
        "Fontname=Arial Black, Fontsize=33,"
        "BorderStyle=3,"
        "BackColour=&HDD000000,"
        "PrimaryColour=&H00FFFFFF,"
        "Alignment=2, MarginV=65'"
    ),


    # -------------------------------------------------------------
    # ROUNDED CORNER / FAKE (by soft blur)
    # -------------------------------------------------------------
    "rounded_box": (
        "subtitles={srt}:force_style='"
        "Fontname=Segoe UI Black, Fontsize=33,"
        "BorderStyle=3, BackColour=&H55111111, Outline=0,"
        "Shadow=1, Alignment=2, MarginV=85'"
    ),


    # -------------------------------------------------------------
    # GLOW / NEON
    # -------------------------------------------------------------
    "glow_white": (
        "subtitles={srt}:force_style='"
        "Fontname=Arial Black, Fontsize=34,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00FFFFFF,"
        "Outline=6, Shadow=0,"
        "Alignment=2, MarginV=85'"
    ),

    "neon_blue": (
        "subtitles={srt}:force_style='"
        "Fontname=Arial Black, Fontsize=33,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00FF0000,"  # blue glow
        "Outline=6,"
        "Alignment=2, MarginV=85'"
    ),


    # -------------------------------------------------------------
    # DROP SHADOW
    # -------------------------------------------------------------
    "shadow_black": (
        "subtitles={srt}:force_style='"
        "Fontname=Arial Black, Fontsize=34,"
        "PrimaryColour=&H00FFFFFF,"
        "Outline=0, Shadow=4,"
        "Alignment=2, MarginV=90'"
    ),

    "shadow_soft": (
        "subtitles={srt}:force_style='"
        "Fontname=Segoe UI Semibold, Fontsize=33,"
        "PrimaryColour=&H00FFFFFF,"
        "Shadow=2, Outline=0,"
        "Alignment=2, MarginV=90'"
    ),


    # -------------------------------------------------------------
    # ANIME STYLE
    # -------------------------------------------------------------
    "anime_white": (
        "subtitles={srt}:force_style='"
        "Fontname=Verdana, Fontsize=34,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000, Outline=4,"
        "Shadow=0, Alignment=2, MarginV=90'"
    ),

    "anime_yellow": (
        "subtitles={srt}:force_style='"
        "Fontname=Verdana, Fontsize=34,"
        "PrimaryColour=&H0000FFFF,"
        "OutlineColour=&H00000000, Outline=4,"
        "Shadow=0, Alignment=2, MarginV=90'"
    ),


    # -------------------------------------------------------------
    # OVERSIZED CENTER TEXT / VIRAL STYLE
    # -------------------------------------------------------------
    "center_punch": (
        "subtitles={srt}:force_style='"
        "Fontname=Impact, Fontsize=55,"
        "PrimaryColour=&H00FFFFFF, Outline=6,"
        "Shadow=0, Alignment=5, MarginV=200'"
    ),

    "big_center_box": (
        "subtitles={srt}:force_style='"
        "Fontname=Arial Black, Fontsize=48,"
        "BorderStyle=3, BackColour=&HAA000000,"
        "PrimaryColour=&H00FFFFFF,"
        "Alignment=5, MarginV=220'"
    ),


    # -------------------------------------------------------------
    # SPLIT COLOR (white top, yellow bottom)
    # -------------------------------------------------------------
    "dual_color": (
        "subtitles={srt}:force_style='"
        "Fontname=Arial Black, Fontsize=34,"
        "PrimaryColour=&H00FFFFFF,"
        "SecondaryColour=&H0000FFFF,"    # bottom line
        "OutlineColour=&H00000000, Outline=3,"
        "Alignment=2, MarginV=85'"
    ),


    # -------------------------------------------------------------
    # BLUR BAR BACKGROUND
    # -------------------------------------------------------------
    "blur_bar": (
        "subtitles={srt}:force_style='"
        "Fontname=Arial Black, Fontsize=34,"
        "BorderStyle=3,"
        "BackColour=&H55111111,"
        "PrimaryColour=&H00FFFFFF,"
        "Outline=0,"
        "Alignment=2, MarginV=90'"
    ),


    # -------------------------------------------------------------
    # WORD BOXED (like motivational edits) like youtube captions
    # -------------------------------------------------------------
    "word_box": (
        "subtitles={srt}:force_style='"
        "Fontname=Segoe UI Semibold, Fontsize=34,"
        "BorderStyle=3,"
        "BackColour=&H88101010,"
        "PrimaryColour=&H00FFFFFF,"
        "Outline=1,"
        "Alignment=2, MarginV=95'"
    ),

  "word_box2": (
        "subtitles={srt}:force_style='"
        "Fontname=Segoe UI Semibold, Fontsize=34,"
        "BorderStyle=3,"
        "BackColour=&H88101010,"
        "PrimaryColour=&H00FFFFFF,"
        "Outline=0, shadow=1,"
        "Alignment=2, MarginV=95'"
    ),
"purple_box_center": (
    "subtitles={srt}:force_style='"
    "Fontname=Segoe UI Semibold, Fontsize=36,"
    "BorderStyle=3,"                         # box mode
    "OutlineColour=&H40FF00FF,"              # 💜 purple box (semi-transparent)
    "BackColour=&H40FF00FF,"                 # set same for compatibility
    "PrimaryColour=&H00FFFFFF,"              # white text
    "Outline=1, Shadow=0,"
    "Alignment=10,"                          # center-middle
    "MarginV=0'"
),

"purple_box_center2": (
    "subtitles={srt}:force_style='"
    "Fontname=Arial Black, Fontsize=36,"
    "BorderStyle=3,"                         # box mode
    "OutlineColour=&H40FF00FF,"              # 💜 purple box (semi-transparent)
    "BackColour=&H40FF00FF,"                 # set same for compatibility
    "PrimaryColour=&H00FFFFFF,"              # white text
    "Outline=1, Shadow=0,"
    "Alignment=10,"                          # center-middle
    "MarginV=0'"
),

"purple_box_center3": (
    "subtitles={srt}:force_style='"
    "Fontname=Comic Sans Ms, Fontsize=36,"
    "BorderStyle=3,"                         # box mode
    "OutlineColour=&H40FF00FF,"              # 💜 purple box (semi-transparent)
    "BackColour=&H40FF00FF,"                 # set same for compatibility
    "PrimaryColour=&H00FFFFFF,"              # white text
    "Outline=1, Shadow=0,"
    "Alignment=10,"                          # center-middle
    "MarginV=0'"
),

    # -------------------------------------------------------------
    # MINIMAL / AESTHETIC
    # -------------------------------------------------------------
    "minimal_white": (
        "subtitles={srt}:force_style='"
        "Fontname=Segoe UI, Fontsize=34,"
        "PrimaryColour=&H00FFFFFF,"
        "Outline=1, Shadow=0,"
        "Alignment=2, MarginV=100'"
    ),

    "minimal_blackbar": (
        "subtitles={srt}:force_style='"
        "Fontname=Segoe UI, Fontsize=32,"
        "BorderStyle=3,"
        "BackColour=&H66101010,"
        "PrimaryColour=&H00FFFFFF,"
        "Outline=0, Alignment=2, MarginV=95'"
    ),


    # -------------------------------------------------------------
    # MEME / HIGH CONTRAST (good for small text captions)
    # -------------------------------------------------------------
    "meme_impact": (
        "subtitles={srt}:force_style='"
        "Fontname=Impact, Fontsize=42,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000, Outline=6,"
        "Alignment=2, MarginV=85'"
    ),

    "meme_yellow": (
        "subtitles={srt}:force_style='"
        "Fontname=Impact, Fontsize=42,"
        "PrimaryColour=&H0000FFFF,"
        "OutlineColour=&H00000000, Outline=6,"
        "Alignment=2, MarginV=85'"
    ),
}


# ----------------------------------------------------------
#     RENDERER
# ----------------------------------------------------------
def render_test_video(
    srt_path: Path,
    audio_path: Path,
    video_path: Path,
    style_name: str,
    fps: int = 30,
) -> Path:

    srt_path = srt_path.resolve()
    audio_path = audio_path.resolve()
    video_path = video_path.resolve()

    # output folder
    out_dir = (TMP_DIR / "caption_tests").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # copy srt into working dir
    dest_srt = out_dir / srt_path.name
    shutil.copy2(srt_path, dest_srt)

    srt_name = dest_srt.name
    vf_style = STYLE_PRESETS[style_name].format(srt=srt_name)

    output_name = f"test_{style_name}.mp4"
    output_path = out_dir / output_name

    # -------------------------
    # ffmpeg:
    #   video input
    #   audio input (voice)
    #   burn subtitles onto video
    # -------------------------
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),    # video background
        "-i", str(audio_path),    # your voice audio
        "-vf", vf_style,          # subtitle style
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-shortest",
        output_name,
    ]

    print("\nRunning FFmpeg:")
    print(" ".join(ffmpeg_cmd))

    result = subprocess.run(
        ffmpeg_cmd,
        cwd=str(out_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"FFmpeg failed ({result.returncode})")

    print(f"\n✔ Output: {output_path}")
    return output_path


# ----------------------------------------------------------
#     CLI
# ----------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Test subtitle styles on real video.")
    parser.add_argument("--srt", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--style",
                        required=True,
                        choices=list(STYLE_PRESETS.keys()))
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    render_test_video(
        srt_path=Path(args.srt),
        audio_path=Path(args.audio),
        video_path=Path(args.video),
        style_name=args.style,
        fps=args.fps
    )


if __name__ == "__main__":
    main()
