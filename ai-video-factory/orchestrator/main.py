from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict
from pathlib import Path
import uuid
import logging
import httpx
import os

app = FastAPI()

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# --- Service URLs ---
SCRIPT_SERVICE_URL = os.environ.get("SCRIPT_SERVICE_URL", "http://127.0.0.1:8001")
VOICE_SERVICE_URL = os.environ.get("VOICE_SERVICE_URL", "http://127.0.0.1:8002")
RENDER_SERVICE_URL = os.environ.get("RENDER_SERVICE_URL", "http://127.0.0.1:8003")

TMP_DIR = Path("../tmp")
TMP_DIR.mkdir(exist_ok=True, parents=True)

#EXAMPLE REQUESTS:
# ---------------------------------------------------------
# {
#   "custom_text": "He was breaking legs on purpose and nobody could stop him – for years Jon Jones threw the most illegal kick in MMA history, stomping straight down on the knee like he was putting out a cigarette, a move so vicious it was literally banned under the old rules. Watch this: Ryan Bader’s leg buckles, Rampage limps for months, even Gustafsson collapses in slow-motion agony, yet the ref just lets it happen. Doctors screamed it tears ACLs and MCLs in one shot, Joe Rogan lost his mind on air yelling 'that should be illegal,' fighters called it dirty, but in 2015 the rules quietly changed and suddenly the oblique kick became 100% fair game. Now look – Israel Adesanya, Shavkat Rakhmonov, Kevin Holland, every top guy is copying Jon’s “evil” weapon in every main event. The same career-ending move that got Jon booed out of arenas is now mandatory if you want to win a title. So tell me: smartest technique in the game, or should it be banned again? Drop a fire emoji if you think it’s straight-up evil.",
#   "duration_seconds": 60,
#   "tone": "dramatic",
#   "language": "en",
#   "image_folder": "C:/path/to/local/images"
# }
# ---------------------------------------------------------
# Models
# ---------------------------------------------------------
class GenerateVideoRequest(BaseModel):
    # Choose ONE of these:
    topic: Optional[str] = None          # auto mode: generate paragraph from topic
    custom_text: Optional[str] = None    # manual mode: your own paragraph

    duration_seconds: int = 30
    tone: str = "motivational"
    language: str = "en"

    # Optional extras
    image_folder: Optional[str] = None   # path to folder with images (Khabib pics etc.)
    voice: Optional[str] = None          # for future multi-voice support


class GenerateVideoResponse(BaseModel):
    video_id: str
    video_path: str
    audio_path: str
    srt_path: str
    total_duration: float
    extra: Dict[str, Any]


# ---------------------------------------------------------
# Endpoint
# ---------------------------------------------------------
@app.post("/generate-video", response_model=GenerateVideoResponse)
async def generate_video(req: GenerateVideoRequest):
    """
    Orchestrates:
    1) script-service (topic OR custom paragraph)
    2) voice-service (TTS + SRT with real timings)
    3) render-service (video + burned subtitles + optional slideshow)
    """
    # 0) Basic validation
    if not req.topic and not req.custom_text:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'topic' or 'custom_text'.",
        )

    video_id = uuid.uuid4().hex
    logger.info(
        f"[ORCH] Starting generation video_id={video_id}, "
        f"topic={req.topic!r}, custom_text_len={len(req.custom_text or '')}"
    )

    async with httpx.AsyncClient(timeout=100.0) as client:
        # 1) SCRIPT SERVICE
        if req.custom_text:
            # Manual paragraph mode
            script_payload = {
                "text": req.custom_text,
                "duration_seconds": req.duration_seconds,
                "tone": req.tone,
                "language": req.language,
                "topic": req.topic or "Custom paragraph",
            }
            script_url = f"{SCRIPT_SERVICE_URL}/generate-script-from-text"
        else:
            # Topic mode
            script_payload = {
                "topic": req.topic,
                "duration_seconds": req.duration_seconds,
                "tone": req.tone,
                "language": req.language,
            }
            script_url = f"{SCRIPT_SERVICE_URL}/generate-script"

        logger.info(f"[ORCH] Calling script-service at {script_url}")
        try:
            script_resp = await client.post(script_url, json=script_payload)
        except Exception as e:
            logger.error(f"[ORCH] Error contacting script-service: {e}")
            raise HTTPException(status_code=502, detail="script-service unreachable")

        if script_resp.status_code != 200:
            logger.error(f"[ORCH] script-service error: {script_resp.text}")
            raise HTTPException(
                status_code=script_resp.status_code,
                detail=f"script-service error: {script_resp.text}",
            )

        script = script_resp.json()

        # 2) VOICE SERVICE (TTS + SRT)
        voice_payload = {
            "video_id": video_id,
            "script": script,
            "voice": req.voice,
        }

        logger.info("[ORCH] Calling voice-service /generate-voice")
        try:
            voice_resp = await client.post(
                f"{VOICE_SERVICE_URL}/generate-voice",
                json=voice_payload,
            )
        except Exception as e:
            logger.error(f"[ORCH] Error contacting voice-service: {e}")
            raise HTTPException(status_code=502, detail="voice-service unreachable")

        if voice_resp.status_code != 200:
            logger.error(f"[ORCH] voice-service error: {voice_resp.text}")
            raise HTTPException(
                status_code=voice_resp.status_code,
                detail=f"voice-service error: {voice_resp.text}",
            )

        voice_data = voice_resp.json()
        audio_path = voice_data["full_audio_path"]
        srt_path = voice_data["srt_path"]
        total_duration = voice_data["total_duration"]

        # 3) RENDER SERVICE (video with subs, slideshow if images provided)
        render_payload = {
            "video_id": video_id,
            "srt_path": srt_path,
            "audio_path": audio_path,
            "image_folder": req.image_folder,
            # You can extend with resolution/fps later if needed
        }

        logger.info("[ORCH] Calling render-service /render-video")
        try:
            render_resp = await client.post(
                f"{RENDER_SERVICE_URL}/render-video",
                json=render_payload,
            )
        except Exception as e:
            logger.error(f"[ORCH] Error contacting render-service: {e}")
            raise HTTPException(status_code=502, detail="render-service unreachable")

        if render_resp.status_code != 200:
            logger.error(f"[ORCH] render-service error: {render_resp.text}")
            raise HTTPException(
                status_code=render_resp.status_code,
                detail=f"render-service error: {render_resp.text}",
            )

        render_data = render_resp.json()
        video_path = render_data["video_path"]

    # 4) Final response
    return GenerateVideoResponse(
        video_id=video_id,
        video_path=video_path,
        audio_path=audio_path,
        srt_path=srt_path,
        total_duration=total_duration,
        extra={
            "script": script,
            "voice": voice_data,
            "render": render_data,
        },
    )
