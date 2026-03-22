from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import subprocess
import logging
import wave
import contextlib
import os

# ---------------------------------------------------------
# FastAPI app + logging
# ---------------------------------------------------------
app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------
TMP_DIR = Path("../tmp")
SUBTITLES_DIR = Path("../subtitles")
TMP_DIR.mkdir(exist_ok=True, parents=True)
SUBTITLES_DIR.mkdir(exist_ok=True, parents=True)

PIPER_BIN = os.environ.get("PIPER_BIN", "piper")
PIPER_MODEL_PATH = os.environ.get(
    "PIPER_MODEL_PATH",
    r"C:\piper\models\en_US-ryan-high.onnx",
)

# ---------------------------------------------------------
# Data models
# ---------------------------------------------------------
class Scene(BaseModel):
    id: int
    voice_text: str
    start: float = 0.0
    end: float = 0.0
    visual_tags: Optional[List[str]] = None
    on_screen_text: Optional[str] = None


class Script(BaseModel):
    topic: str
    duration_seconds: float
    tone: str
    language: str
    scenes: List[Scene]


class VoiceRequest(BaseModel):
    video_id: str
    script: Script
    # Optional: later you can use this to switch Piper models
    voice: Optional[str] = None


class ClipInfo(BaseModel):
    scene_id: int
    audio_path: str
    duration: float
    start: float
    end: float


class VoiceResponse(BaseModel):
    video_id: str
    total_duration: float
    clips: List[ClipInfo]
    full_audio_path: str
    full_audio_duration: float
    srt_path: str


# ---------------------------------------------------------
# Utils: audio
# ---------------------------------------------------------
def get_wav_duration(path: Path) -> float:
    """Return duration (seconds) of a WAV file."""
    if not path.exists():
        raise FileNotFoundError(f"WAV file not found: {path}")
    with contextlib.closing(wave.open(str(path), "rb")) as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def concat_wav_files(input_paths: List[Path], output_path: Path) -> float:
    """
    Concatenate a list of WAV files into a single WAV.
    Returns the duration of the resulting file.
    """
    if not input_paths:
        raise ValueError("No input WAV files to concatenate")

    logger.info(f"[AUDIO] Concatenating {len(input_paths)} clips into {output_path}")
    with wave.open(str(input_paths[0]), "rb") as first_wav:
        params = first_wav.getparams()

    with wave.open(str(output_path), "wb") as out_wav:
        out_wav.setparams(params)
        for wav_path in input_paths:
            with wave.open(str(wav_path), "rb") as in_wav:
                if in_wav.getparams() != params:
                    logger.warning(
                        f"Input WAV params differ for {wav_path}, "
                        f"this may cause issues."
                    )
                frames = in_wav.readframes(in_wav.getnframes())
                out_wav.writeframes(frames)

    return get_wav_duration(output_path)


def synthesize_tts(
    text: str,
    output_path: Path,
    voice: Optional[str] = None,
) -> None:
    """
    Use Piper TTS to synthesize `text` to `output_path`.
    Adjust the model_path to your setup.
    """
    model_path = voice or PIPER_MODEL_PATH

    if not Path(model_path).exists():
        raise HTTPException(
            status_code=500,
            detail=(
                "Piper model not found. Set PIPER_MODEL_PATH env var or pass "
                "'voice' in the request payload."
            ),
        )

    cmd = [
        PIPER_BIN,
        "--model",
        model_path,
        "--output_file",
        str(output_path),
    ]

    try:
        logger.info(f"[TTS] Synthesizing scene audio to {output_path}")
        proc = subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        if proc.stderr:
            logger.info(f"[TTS] Piper stderr: {proc.stderr.decode('utf-8', errors='ignore')}")
    except subprocess.CalledProcessError as e:
        logger.error(f"[TTS] Piper failed: {e.stderr.decode('utf-8', errors='ignore')}")
        raise HTTPException(status_code=500, detail="TTS synthesis failed.")


# ---------------------------------------------------------
# Utils: SRT
# ---------------------------------------------------------
def format_timecode(seconds: float) -> str:
    """
    Convert seconds (float) to SRT timecode "HH:MM:SS,mmm".
    """
    millis = int(round(seconds * 1000))
    s, ms = divmod(millis, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def smart_chunk_text(
    text: str,
    max_chars: int = 42,
) -> List[str]:
    """
    Split text into readable chunks for subtitles:
    - Prefer splitting on punctuation
    - Otherwise split on spaces
    - Ensure no chunk exceeds max_chars
    """
    import re

    # Normalize spaces
    text = re.sub(r"\s+", " ", text).strip()

    # Preferred split points: punctuation
    parts = re.split(r'(?<=[\.\!\?\,;:])\s+', text)

    chunks = []
    for part in parts:
        if len(part) <= max_chars:
            chunks.append(part.strip())
        else:
            # Over max chars → split by words
            words = part.split(" ")
            buffer = ""
            for w in words:
                if len(buffer) + len(w) + 1 <= max_chars:
                    buffer += (" " + w if buffer else w)
                else:
                    chunks.append(buffer)
                    buffer = w
            if buffer:
                chunks.append(buffer)
    return chunks


def format_subtitle_lines(text: str) -> str:
    """
    If a chunk is long, break into two lines
    for better vertical readability.
    """
    words = text.split()
    if len(words) <= 4:
        return text  # keep single line

    mid = len(words) // 2
    return " ".join(words[:mid]) + "\n" + " ".join(words[mid:])


def build_srt_from_scenes(
    scenes: List[Scene],
    srt_path: Path,
    audio_duration: float,
) -> None:
    """
    SRT builder with:
    - smart text chunking
    - global monotonic timing
    - small gap between each subtitle (min_gap)
    - clamped to [0, audio_duration)
    """
    logger.info(f"[SRT] Building improved subtitle file at {srt_path}")

    scenes_sorted = sorted(scenes, key=lambda s: s.start)

    lines: List[str] = []
    index = 1

    EPS = 0.01         # epsilon for end < audio_duration
    MIN_GAP = 0.03     # 30ms gap between subtitles
    MIN_CHUNK_DUR = 0.40  # 400ms minimum subtitle display time

    last_end = 0.0

    for scene in scenes_sorted:
        text = (scene.voice_text or "").strip()
        if not text:
            continue

        scene_start = max(0.0, scene.start)
        scene_end = min(audio_duration - EPS, scene.end)
        scene_duration = scene_end - scene_start
        if scene_duration <= 0:
            continue

        chunks = smart_chunk_text(text)
        if not chunks:
            continue

        # Base chunk duration for this scene
        chunk_dur = max(MIN_CHUNK_DUR, scene_duration / len(chunks))

        for ch in chunks:
            # Start must be:
            # - at or after scene_start
            # - after last_end + MIN_GAP
            start = max(scene_start, last_end + MIN_GAP)

            if start >= scene_end or start >= audio_duration - EPS:
                break  # no more room for this scene

            end = start + chunk_dur
            end = min(end, scene_end, audio_duration - EPS)

            # If we don’t have enough room for a readable subtitle, stop
            if end <= start + 0.05:
                break

            start_tc = format_timecode(start)
            end_tc = format_timecode(end)

            pretty_text = format_subtitle_lines(ch)

            lines.append(str(index))
            lines.append(f"{start_tc} --> {end_tc}")
            lines.append(pretty_text)
            lines.append("")

            index += 1
            last_end = end  # global timeline moves forward

    srt_path.write_text("\n".join(lines), encoding="utf-8")

# ---------------------------------------------------------
# Endpoint
# ---------------------------------------------------------
@app.post("/generate-voice", response_model=VoiceResponse)
def generate_voice(req: VoiceRequest):
    """
    Generate voice audio clips for each scene, rebuild the real timeline
    based on measured durations, concatenate the audio into a full WAV,
    and create an SRT file that is perfectly aligned to the audio.
    """
    video_id = req.video_id
    script = req.script

    logger.info(
        f"[VOICE] Generating voice for video_id={video_id}, "
        f"{len(script.scenes)} scenes, topic={script.topic!r}"
    )

    # Folder for per-scene WAVs
    video_dir = TMP_DIR / video_id
    video_dir.mkdir(exist_ok=True, parents=True)

    clips_raw: List[Dict[str, Any]] = []
    clip_paths: List[Path] = []

    # 1) TTS per scene
    for scene in script.scenes:
        scene_id = scene.id
        text = scene.voice_text or ""

        if not text.strip():
            logger.warning(f"[VOICE] Scene {scene_id} has empty voice_text, skipping TTS")
            continue

        out_path = video_dir / f"{video_id}_scene{scene_id}.wav"
        synthesize_tts(text=text, output_path=out_path, voice=req.voice)
        dur = get_wav_duration(out_path)

        logger.info(f"[VOICE] Scene {scene_id} duration = {dur:.3f}s")

        clip_paths.append(out_path)
        clips_raw.append(
            {
                "scene_id": scene_id,
                "audio_path": str(out_path),
                "duration": dur,
                "start": 0.0,  # to be filled after we compute the timeline
                "end": 0.0,
            }
        )

    if not clips_raw:
        raise HTTPException(status_code=400, detail="No valid scenes to synthesize.")

    # 2) Rebuild the timeline from real durations
    current_start = 0.0
    scene_by_id: Dict[int, Scene] = {s.id: s for s in script.scenes}

    for clip in clips_raw:
        dur = clip["duration"]
        start = current_start
        end = start + dur
        current_start = end

        clip["start"] = round(start, 3)
        clip["end"] = round(end, 3)

        # Update the corresponding Scene object
        scene_obj = scene_by_id.get(clip["scene_id"])
        if scene_obj:
            scene_obj.start = clip["start"]
            scene_obj.end = clip["end"]

    total_duration = current_start
    logger.info(f"[VOICE] Total duration (from audio) = {total_duration:.3f}s")

    # 3) Concatenate audio into full WAV
    full_path = TMP_DIR / f"{video_id}_full.wav"
    try:
        full_dur = concat_wav_files(clip_paths, full_path)
    except Exception as e:
        logger.error(f"[VOICE] Failed to build full WAV for {video_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to concatenate audio.")

    logger.info(f"[VOICE] Full audio duration (measured) = {full_dur:.3f}s")

    # 4) Create SRT based on the updated scene timings
 
    srt_path = SUBTITLES_DIR / f"{video_id}.srt"
    build_srt_from_scenes(
    scenes=list(scene_by_id.values()),
    srt_path=srt_path,
    audio_duration=full_dur,
)

    # 5) Build response
    clips = [ClipInfo(**clip) for clip in clips_raw]

    resp = VoiceResponse(
        video_id=video_id,
        total_duration=round(total_duration, 3),
        clips=clips,
        full_audio_path=str(full_path),
        full_audio_duration=round(full_dur, 3),
        srt_path=str(srt_path),
    )
    return resp
