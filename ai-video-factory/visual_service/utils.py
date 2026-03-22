# utils.py
import shutil
from pathlib import Path
import subprocess
from typing import List

import torch
from diffusers import StableDiffusionPipeline

# ---------- GLOBAL PIPELINE (load once) ----------

# You can change to "cpu" if you don't want GPU (but it's MUCH slower)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Recommended 9:16 size in multiples of 8 (SD1.5 native is 512x512, but this works fine)
SD_WIDTH = 576   # 9:16 -> 576x1024
SD_HEIGHT = 1024

print(f"[sd] Loading StableDiffusion pipeline on {DEVICE}...")
sd_pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
    safety_checker=None,  # optional, you can keep it if you want filtering
)
sd_pipe = sd_pipe.to(DEVICE)
sd_pipe.enable_attention_slicing()  # helps on smaller GPUs
print("[sd] Pipeline loaded.")


# ---------- IMAGE GENERATION ----------

def build_scene_prompt(script: dict, scene: dict) -> str:
    topic = script.get("topic", "")
    tone = script.get("tone", "")
    visual_tags = scene.get("visual_tags", []) or []
    on_screen_text = scene.get("on_screen_text", "") or ""

    base = f"{topic}, {tone} style, " if topic or tone else ""
    tags = ", ".join(visual_tags)

    extras = "cinematic lighting, ultra detailed, 4k, concept art, vertical composition"
    prompt_parts = [base, tags, extras]
    if on_screen_text:
        prompt_parts.append(f"text on screen: \"{on_screen_text}\"")

    # Clean up spaces/commas
    prompt = ", ".join([p.strip().strip(",") for p in prompt_parts if p.strip()])
    return prompt


def generate_image_for_scene(script: dict, scene: dict, img_path: Path) -> None:
    """
    Generate one image for a scene using Stable Diffusion.
    """
    img_path = img_path.resolve()
    img_path.parent.mkdir(parents=True, exist_ok=True)

    prompt = build_scene_prompt(script, scene)
    print(f"[visual] Generating image for scene {scene.get('id')} with prompt:\n  {prompt}")

    with torch.autocast("cuda") if DEVICE == "cuda" else torch.no_grad():
        image = sd_pipe(
            prompt,
            width=SD_WIDTH,
            height=SD_HEIGHT,
            num_inference_steps=25,
            guidance_scale=7.5,
        ).images[0]

    image.save(img_path)
    print(f"[visual] Saved scene image to {img_path}")


# ---------- VIDEO HELPERS (your existing ones) ----------

def make_clip_from_image(img_path: Path, out_path: Path,
                         duration: float,
                         resolution: str = "1080x1920",
                         fps: int = 30) -> None:
    img_path = img_path.resolve()
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", str(img_path),
        "-t", str(duration),
        "-vf", f"scale={resolution}",
        "-r", str(fps),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-an",
        str(out_path),
    ]
    print("[visual] make_clip_from_image:", " ".join(ffmpeg_cmd))
    subprocess.run(ffmpeg_cmd, check=True)


def concat_clips(clips: List[Path], out_path: Path) -> None:
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    list_file = out_path.parent / "filelist.txt"
    with list_file.open("w", encoding="utf-8") as f:
        for clip in clips:
            f.write(f"file '{clip.resolve().as_posix()}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(out_path),
    ]
    print("[visual] concat_clips:", " ".join(cmd))
    subprocess.run(cmd, check=True)
