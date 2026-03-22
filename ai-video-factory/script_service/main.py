from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import json
import textwrap
import logging
import re
from typing import List, Dict
import math
from pathlib import Path   
import time              
from pathlib import Path
import uuid
import json
import os

app = FastAPI()

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

OLLAMA_BIN = os.environ.get("OLLAMA_BIN", "ollama")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")


class ScriptRequest(BaseModel):
    topic: str
    duration_seconds: int = 30
    tone: str = "neutral"
    language: str = "en"

class CustomScriptRequest(BaseModel):
    """
    Request model when the user provides their own paragraph, instead of a topic.
    We still:
    - split the text into scenes
    - estimate timings from word count
    - enrich scenes with visual_tags / on_screen_text
    """
    text: str
    duration_seconds: int = 30
    tone: str = "neutral"
    language: str = "en"
    topic: str | None = None  # optional label, used for logs/visuals

MAX_RETRIES = 3

TARGET_WPS = 2.5        # target speaking speed (words per second)
SCENE_CHUNK_SECONDS = 8 # desired scene length in seconds (we'll group ~8s of speech per scene)

# Folder where SRT files will be written
BASE_SUBTITLES_DIR = Path("../subtitles")
BASE_SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)
BASE_DIR = Path("..")
SCRIPTS_DIR = BASE_DIR / "scripts"
SCRIPTS_DIR.mkdir(exist_ok=True, parents=True)

RAW_TEXT_DIR = SCRIPTS_DIR / "raw_text"
RAW_TEXT_DIR.mkdir(exist_ok=True, parents=True)

JSON_DIR = SCRIPTS_DIR / "json"
JSON_DIR.mkdir(exist_ok=True, parents=True)

# ------------- OLLAMA HELPERS -------------

def call_ollama_for_text(prompt: str) -> str:
    """
    Call ollama with llama3 and return raw text (no JSON).
    """
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        logger.info(f"[call_ollama_for_text] Calling Ollama, attempt {attempt}")
        result = subprocess.run(
            [OLLAMA_BIN, "run", OLLAMA_MODEL],
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout = result.stdout.decode("utf-8").strip()
        stderr = result.stderr.decode("utf-8").strip()

        if stderr:
            logger.warning(f"Ollama stderr (attempt {attempt}): {stderr}")

        if stdout:
            return stdout

        last_err = "Empty stdout from ollama"

    raise RuntimeError(f"Ollama failed after {MAX_RETRIES} attempts: {last_err}")


def call_ollama_for_json(prompt: str) -> dict:
    """
    Call ollama expecting JSON output. Cleans code fences and parses JSON.
    """
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        logger.info(f"[call_ollama_for_json] Calling Ollama, attempt {attempt}")
        result = subprocess.run(
            [OLLAMA_BIN, "run", OLLAMA_MODEL],
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        raw_output = result.stdout.decode("utf-8").strip()
        stderr = result.stderr.decode("utf-8").strip()

        if stderr:
            logger.warning(f"Ollama stderr (attempt {attempt}): {stderr}")

        # Strip fences if present
        if "```" in raw_output:
            start = raw_output.find("{")
            end = raw_output.rfind("}")
            if start != -1 and end != -1:
                raw_output = raw_output[start:end + 1]

        try:
            data = json.loads(raw_output)
            return data
        except json.JSONDecodeError as e:
            last_error = e
            logger.error(f"[call_ollama_for_json] JSON parse failed, attempt {attempt}: {e}")
            logger.error("RAW OUTPUT:\n" + raw_output)

    raise RuntimeError(f"Model did not return valid JSON after {MAX_RETRIES} attempts: {last_error}")


# ------------- TEXT → SCENES -------------

def split_text_into_sentences(text: str) -> List[str]:
    """
    Rough sentence splitter based on punctuation.
    """
    text = text.strip()
    if not text:
        return []

    # Split on ., ?, ! followed by space/newline
    sentences = re.split(r'(?<=[.!?])\s+', text)
    # Remove empty bits
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def build_scenes_from_text(
    body: str,
    requested_duration: float,
    target_wps: float = TARGET_WPS,
    scene_chunk_seconds: float = SCENE_CHUNK_SECONDS,
) -> List[Dict]:
    """
    Turn a long text into scenes:
    - Compute target words per scene based on chunk_seconds * wps
    - Group sentences into scenes around that size
    - Compute start/end from words and target_wps
    """
    sentences = split_text_into_sentences(body)
    if not sentences:
        return []

    # Prepare sentence-level word counts
    sentence_words = [(s, len(s.split())) for s in sentences]
    total_words = sum(w for _, w in sentence_words)
    logger.info(f"Total words in body: {total_words}")

    if total_words == 0:
        return []

    target_words_per_scene = scene_chunk_seconds * target_wps
    logger.info(
        f"Target ~{target_words_per_scene:.1f} words per scene "
        f"({scene_chunk_seconds}s @ {target_wps} wps)"
    )

    # 1) Group sentences into scene texts
    scenes_texts: List[str] = []
    current_text = ""
    current_words = 0

    for s, wc in sentence_words:
        # If adding this sentence would make it way too big, start a new scene
        if current_words > 0 and current_words + wc > target_words_per_scene * 1.3:
            scenes_texts.append(current_text.strip())
            current_text = s
            current_words = wc
        else:
            if current_text:
                current_text += " " + s
            else:
                current_text = s
            current_words += wc

    # Add last scene
    if current_text.strip():
        scenes_texts.append(current_text.strip())

    logger.info(f"Built {len(scenes_texts)} scene texts from body")

    # 2) Compute duration per scene from word count & target_wps
    scene_word_counts = [len(t.split()) for t in scenes_texts]
    scene_durations = [w / target_wps for w in scene_word_counts]
    total_duration = sum(scene_durations)

    logger.info(
        f"Total duration from text @ {target_wps} wps: {total_duration:.2f}s "
        f"(requested: {requested_duration:.2f}s)"
    )

    # Option: we let total_duration float based on word count;
    # if you want to force it to requested_duration, you can scale here.

    # 3) Assign start/end
    scenes: List[Dict] = []
    current_start = 0.0
    for idx, (text_scene, dur, wc) in enumerate(
        zip(scenes_texts, scene_durations, scene_word_counts), start=1
    ):
        start = current_start
        end = current_start + dur
        current_start = end

        scenes.append(
            {
                "id": idx,
                "start": round(start, 3),
                "end": round(end, 3),
                "voice_text": text_scene,
                "visual_tags": [],       # will be filled later
                "on_screen_text": "",    # will be filled later
                "_word_count": wc,       # internal/debug field
            }
        )

    return scenes

def _format_srt_timestamp(seconds: float) -> str:
    """
    Convert seconds (float) -> 'HH:MM:SS,mmm' for SRT.
    """
    if seconds < 0:
        seconds = 0.0

    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000

    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60

    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def split_subtitle_lines(text: str, max_words=5):
    """
    Split a long sentence into short subtitle-friendly chunks.
    - max_words: how many words per chunk
    """
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i+max_words])
        chunks.append(chunk)
    
    return chunks


def build_srt_from_scenes(scenes: List[Dict]) -> str:
    """
    Build an SRT where each scene is further split into short subtitle chunks.
    Each chunk gets a proportional share of the scene duration.
    """
    srt_lines = []
    cue_index = 1

    for scene in scenes:
        start = float(scene["start"])
        end = float(scene["end"])
        text = scene["voice_text"].strip()

        # Break into 5-word chunks
        chunks = split_subtitle_lines(text, max_words=9)

        scene_duration = end - start
        chunk_duration = scene_duration / len(chunks)

        for i, chunk in enumerate(chunks):
            chunk_start = start + i * chunk_duration
            chunk_end = chunk_start + chunk_duration

            srt_lines.append(str(cue_index))
            srt_lines.append(
                f"{_format_srt_timestamp(chunk_start)} --> {_format_srt_timestamp(chunk_end)}"
            )
            srt_lines.append(chunk)
            srt_lines.append("")

            cue_index += 1

    return "\n".join(srt_lines)
    """
    Build an SRT string from your scenes list.
    """
    srt_lines: List[str] = []

    for idx, scene in enumerate(scenes, start=1):
        start_sec = float(scene.get("start", 0.0))
        end_sec = float(scene.get("end", 0.0))
        text = (scene.get("voice_text") or "").strip()

        if not text:
            continue

        start_ts = _format_srt_timestamp(start_sec)
        end_ts = _format_srt_timestamp(end_sec)

        srt_lines.append(str(idx))
        srt_lines.append(f"{start_ts} --> {end_ts}")
        srt_lines.append(text)
        srt_lines.append("")  # blank line

    return "\n".join(srt_lines)

def slugify_topic(topic: str) -> str:
    """
    Simple slugify for filenames from topic.
    """
    topic = topic.lower().strip()
    topic = re.sub(r"[^a-z0-9]+", "-", topic)
    topic = re.sub(r"-+", "-", topic).strip("-")
    return topic or "script"

# ------------- VISUAL TAGS + ON-SCREEN TEXT -------------

def generate_visuals_for_scenes(
    scenes: List[Dict],
    topic: str,
    language: str = "en",
) -> None:
    """
    Use Llama to generate visual_tags and on_screen_text for each scene.
    Modifies scenes in-place.
    """
    if not scenes:
        return

    # Build a compact representation to send to the model
    scene_summaries = [
        {"id": s["id"], "voice_text": s.get("voice_text", "")}
        for s in scenes
    ]

    system_prompt = """
You are an assistant that helps create short-form vertical videos.

Your task:
- For each scene's voice_text, propose:
  - visual_tags: 2 to 4 SHORT phrases of what visuals could be shown
    (examples: "city skyline at night", "person typing on laptop", "data centers", "animated graph").
  - on_screen_text: a short 3–8 word caption that can be displayed on screen
    (punchy, not a full sentence).

Respond with VALID JSON ONLY, no explanations, no code fences.

Expected JSON structure:
{
  "scenes": [
    {
      "id": 1,
      "visual_tags": ["...", "..."],
      "on_screen_text": "..."
    }
  ]
}
"""

    user_prompt = f"""
Topic: {topic}
Language: {language}

Here are the scenes (id + voice_text):

{json.dumps(scene_summaries, indent=2, ensure_ascii=False)}

Return JSON with a "scenes" array, where each element has:
- id: same as input
- visual_tags: list of 2-4 short phrases
- on_screen_text: short caption (3-8 words)
"""

    full_prompt = textwrap.dedent(system_prompt + "\n" + user_prompt)

    try:
        visuals_json = call_ollama_for_json(full_prompt)
    except Exception as e:
        logger.error(f"Error generating visuals for scenes: {e}")
        # If it fails, keep scenes with empty tags/text
        return

    visuals_list = visuals_json.get("scenes", [])
    # Build a lookup by id
    visuals_by_id = {item.get("id"): item for item in visuals_list}

    for scene in scenes:
        sid = scene.get("id")
        v = visuals_by_id.get(sid)
        if not v:
            continue

        tags = v.get("visual_tags", [])
        on_text = v.get("on_screen_text", "")

        # Basic sanitization
        if not isinstance(tags, list):
            tags = []
        tags = [str(t).strip() for t in tags if str(t).strip()]

        scene["visual_tags"] = tags
        scene["on_screen_text"] = str(on_text).strip()

    logger.info("Visual tags and on_screen_text filled for scenes.")


# ------------- VERIFICATION -------------

def verify_script_timing(script: dict) -> None:
    """
    Verify and log words-per-second for each scene.
    """
    scenes = script.get("scenes", [])
    total_script_duration = script.get("duration_seconds", None)

    logger.info("=== Verifying script timing ===")
    logger.info(f"Topic: {script.get('topic')}")
    logger.info(f"Total duration (from text): {total_script_duration}")

    sum_scene_durations = 0.0

    for scene in scenes:
        scene_id = scene.get("id")
        start = float(scene.get("start", 0.0))
        end = float(scene.get("end", 0.0))
        duration = max(0.0, end - start)

        voice_text = scene.get("voice_text", "") or ""
        words = len(voice_text.split())
        wps = (words / duration) if duration > 0 else 0.0

        sum_scene_durations += duration

        logger.info(
            f"Scene {scene_id}: duration={duration:.2f}s, "
            f"words={words}, wps={wps:.2f}"
        )

        if duration > 0 and (wps < 2.0 or wps > 3.5):
            logger.warning(
                f"Scene {scene_id} OUT OF RANGE: wps={wps:.2f} "
                f"(target ~{TARGET_WPS})"
            )

        logger.info(
            f"Scene {scene_id} visuals: tags={scene.get('visual_tags')}, "
            f"on_screen_text='{scene.get('on_screen_text')}'"
        )

    logger.info(f"Sum of scene durations: {sum_scene_durations:.2f}s")
    logger.info("=== End verification ===")


# ------------- MAIN ENDPOINT -------------

@app.post("/generate-script")
def generate_script(req: ScriptRequest):
    """
    Topic-based mode:
    - Ask Ollama to generate a narration about the topic
    - Split it into scenes with estimated timings
    - Enrich scenes with visual_tags and on_screen_text
    - NO SRT generation here (that will be done after TTS in the voice service)
    """
    # 1) Decide how many words we want total
    target_total_words = int(req.duration_seconds * TARGET_WPS)
    logger.info(
        f"Generating script for topic={req.topic!r} "
        f"~{target_total_words} words (duration ~{req.duration_seconds}s)"
    )

    system_prompt = """
You are a YouTube Shorts / TikTok scriptwriter.
Write a SINGLE continuous narration text about the given topic.
Do NOT format as JSON, list, bullet points, or code.
Just plain paragraphs of text.
"""

    user_prompt = f"""
Topic: {req.topic}
Tone: {req.tone}
Language: {req.language}

Write approximately {target_total_words} words.
Make it suitable for a spoken short vertical video.
Avoid long introductions; hook the viewer early and stay focused.
Do NOT include section titles or numbers. Just narration.
"""

    full_prompt = textwrap.dedent(system_prompt + "\n" + user_prompt)

    try:
        body = call_ollama_for_text(full_prompt)
    except Exception as e:
        logger.error(f"Error calling Ollama for narration: {e}")
        raise HTTPException(status_code=500, detail=f"Ollama error: {e}")

    # 2) Build scenes from the raw text (estimate timings from word counts)
    scenes = build_scenes_from_text(
        body=body,
        requested_duration=float(req.duration_seconds),
        target_wps=TARGET_WPS,
        scene_chunk_seconds=SCENE_CHUNK_SECONDS,
    )

    if not scenes:
        raise HTTPException(status_code=500, detail="No scenes could be generated from text.")

    total_duration = scenes[-1]["end"] if scenes else 0.0

    # 3) Fill visual_tags + on_screen_text using another LLM call
    generate_visuals_for_scenes(
        scenes=scenes,
        topic=req.topic,
        language=req.language,
    )

    # Clean up internal fields (_word_count) before returning
    for scene in scenes:
        scene.pop("_word_count", None)

    script = {
        "topic": req.topic,
        "duration_seconds": round(total_duration, 3),
        "tone": req.tone,
        "language": req.language,
        "title": "",  # can be generated later
        "hook": "",   # can be generated later
        "scenes": scenes,
        # NOTE: no SRT path here – subtitles will be generated AFTER TTS
    }
    # 3bis) Persist raw paragraph + script JSON
    script_id = uuid.uuid4().hex

    raw_text_path = RAW_TEXT_DIR / f"{script_id}_body.txt"
    json_path = JSON_DIR / f"{script_id}_script.json"

    try:
        raw_text_path.write_text(body, encoding="utf-8")
        json_path.write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(
            f"[SCRIPT] Saved narration + script "
            f"raw={raw_text_path.name}, json={json_path.name}"
        )
    except Exception as e:
        logger.error(f"[SCRIPT] Failed to save script files: {e}")

    # optionally include script_id + paths in response
    script["script_id"] = script_id
    script["raw_text_path"] = str(raw_text_path)
    script["json_path"] = str(json_path)

    # 4) Log verification
    verify_script_timing(script)

    return script


@app.post("/generate-script-from-text")
def generate_script_from_text(req: CustomScriptRequest):
    """
    Custom paragraph mode:
    - Use the provided `text` directly (no LLM call for narration)
    - Split it into scenes with estimated timings
    - Enrich scenes with visual_tags and on_screen_text
    """
    topic_label = req.topic or "Custom paragraph"

    logger.info(
        f"Generating script from custom text for topic={topic_label!r} "
        f"(requested duration ~{req.duration_seconds}s)"
    )

    # 1) Build scenes from the raw text
    scenes = build_scenes_from_text(
        body=req.text,
        requested_duration=float(req.duration_seconds),
        target_wps=TARGET_WPS,
        scene_chunk_seconds=SCENE_CHUNK_SECONDS,
    )

    if not scenes:
        raise HTTPException(
            status_code=400,
            detail="Provided text is empty or too short to build scenes.",
        )

    total_duration = scenes[-1]["end"] if scenes else 0.0

    # 2) Fill visual_tags + on_screen_text
    generate_visuals_for_scenes(
        scenes=scenes,
        topic=topic_label,
        language=req.language,
    )

    # Clean up internal fields (_word_count) before returning
    for scene in scenes:
        scene.pop("_word_count", None)

    script = {
        "topic": topic_label,
        "duration_seconds": round(total_duration, 3),
        "tone": req.tone,
        "language": req.language,
        "title": "",
        "hook": "",
        "scenes": scenes,
    }
    # 2bis) Persist provided text + script JSON
    script_id = uuid.uuid4().hex

    raw_text_path = RAW_TEXT_DIR / f"{script_id}_body.txt"
    json_path = JSON_DIR / f"{script_id}_script.json"

    try:
        raw_text_path.write_text(req.text, encoding="utf-8")
        json_path.write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(
            f"[SCRIPT] Saved custom text + script "
            f"raw={raw_text_path.name}, json={json_path.name}"
        )
    except Exception as e:
        logger.error(f"[SCRIPT] Failed to save custom script files: {e}")

    script["script_id"] = script_id
    script["raw_text_path"] = str(raw_text_path)
    script["json_path"] = str(json_path)

    verify_script_timing(script)

    return script
