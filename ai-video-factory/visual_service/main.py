# visual_service/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import subprocess
import uuid
import json
from utils import generate_image_for_scene, make_clip_from_image, concat_clips

# from ./utils
TMP_DIR = Path("../tmp")
ASSETS_DIR = Path("../assets")
VISUALS_DIR = TMP_DIR / "visuals"

for d in [TMP_DIR, ASSETS_DIR, VISUALS_DIR]:
    d.mkdir(exist_ok=True, parents=True)

app = FastAPI()

class GenerateVisualsRequest(BaseModel):
    video_id: str
    script: dict          # the JSON you showed
    resolution: str = "1080x1920"
    fps: int = 30

@app.post("/generate-visuals")
async def generate_visuals(req: GenerateVisualsRequest):
    video_id = req.video_id
    script   = req.script
    scenes   = script.get("scenes", [])

    scene_clips = []

    for scene in scenes:
        sid    = scene["id"]
        start  = float(scene.get("start", 0.0))
        end    = float(scene.get("end", start + 1.0))
        dur    = max(0.5, end - start)

        # 1) Generate image for this scene (placeholder here)
        img_path = ASSETS_DIR / f"{video_id}_scene_{sid:02d}.png"
        generate_image_for_scene(script, scene, img_path)  # you implement this

        # 2) Turn image → video segment
        clip_path = VISUALS_DIR / f"{video_id}_scene_{sid:02d}.mp4"
        make_clip_from_image(
            img_path=img_path,
            out_path=clip_path,
            duration=dur,
            resolution=req.resolution,
            fps=req.fps,
        )
        scene_clips.append(clip_path)

    # 3) Concatenate all segments
    final_visual_path = VISUALS_DIR / f"{video_id}_visuals.mp4"
    concat_clips(scene_clips, final_visual_path)

    return {
        "video_id": video_id,
        "visual_video_path": str(final_visual_path),
        "scene_clips": [str(p) for p in scene_clips],
    }
