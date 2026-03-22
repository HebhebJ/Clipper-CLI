# AI Video Factory

Local FastAPI pipeline that turns a topic (or custom paragraph) into a narrated short-form video.

Pipeline:

1. `script_service` builds scene-based script JSON
2. `voice_service` generates scene WAVs + merged audio + aligned SRT
3. `render_service` produces vertical MP4 (solid background or slideshow) with burned captions
4. `orchestrator` coordinates all services via a single API call

## Services

- `orchestrator/main.py` (port `8000`)
  - endpoint: `POST /generate-video`
  - calls script, voice, render services in sequence

- `script_service/main.py` (port `8001`)
  - `POST /generate-script`
  - `POST /generate-script-from-text`
  - uses Ollama (`llama3`) for narration and per-scene visual metadata

- `voice_service/main.py` (port `8002`)
  - `POST /generate-voice`
  - uses Piper for TTS
  - recalculates true scene timings from generated audio
  - builds timeline-aligned SRT

- `render_service/main.py` (port `8003`)
  - `POST /render-video`
  - builds base video:
    - black color background, or
    - slideshow from `image_folder`
  - burns subtitles using style presets (`word_box`, `bottom_black_box`, etc.)

## Directory Notes

```text
ai-video-factory/
+- orchestrator/
+- script_service/
+- voice_service/
+- render_service/
+- visual_service/        # experimental image/video generation utilities
+- scripts/               # saved script outputs (raw + json)
+- subtitles/             # generated srt files (ignored)
+- tmp/                   # generated audio/video intermediates (ignored)
+- downloads/             # downloader outputs (ignored)
+- run_all.py
+- run_all.bat
```

## Requirements

- Python `3.10+`
- `ffmpeg` + `ffprobe` on `PATH`
- Ollama installed with `llama3` pulled
- Piper CLI installed and model available

Python packages used across services include:

- `fastapi`
- `uvicorn`
- `httpx`
- `pydantic`
- `Pillow`
- optional/experimental: `torch`, `diffusers`, `yt-dlp`

## Configure Environment

Use [`.env.example`](.env.example) as a template, then export values in your shell.

Important variables:

- `OLLAMA_BIN`, `OLLAMA_MODEL`
- `PIPER_BIN`, `PIPER_MODEL_PATH`
- `SCRIPT_SERVICE_URL`, `VOICE_SERVICE_URL`, `RENDER_SERVICE_URL`

## Running

### Option A: one command launcher

```bash
cd ai-video-factory
pip install -r requirements.txt
py run_all.py
```

### Option B: run each service manually

```bash
# terminal 1
cd ai-video-factory/script_service
py -m uvicorn main:app --host 0.0.0.0 --port 8001

# terminal 2
cd ai-video-factory/voice_service
py -m uvicorn main:app --host 0.0.0.0 --port 8002

# terminal 3
cd ai-video-factory/render_service
py -m uvicorn main:app --host 0.0.0.0 --port 8003

# terminal 4
cd ai-video-factory/orchestrator
py -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## API: End-to-End Generation

`POST http://127.0.0.1:8000/generate-video`

Request body:

```json
{
  "topic": "How AI is changing sports training",
  "duration_seconds": 50,
  "tone": "dramatic",
  "language": "en",
  "image_folder": "C:/path/to/local/images"
}
```

You can also use `custom_text` instead of `topic`.

Response includes:

- `video_id`
- `video_path`
- `audio_path`
- `srt_path`
- timing metadata + nested service outputs in `extra`

## Legal Notice

`youtube_downloader.py` is intended only for downloading content you are authorized to use.

- Follow applicable copyright laws.
- Follow platform terms of service.
- Do not use this project to redistribute copyrighted material without permission.

## Known Constraints

- Services read environment variables directly and do not auto-load `.env` yet.
- No centralized config file yet; values are embedded in service modules.
- `docs/script_schema.json` contains a baseline schema and should evolve with script changes.
- This repo stores many generated artifacts locally; keep them out of Git history.

## Suggested Next Refactor

1. Auto-load `.env` values at startup (`python-dotenv`) for easier local setup.
2. Add health endpoints and startup checks per service.
3. Add integration tests for orchestrator pipeline.
4. Split optional heavy ML dependencies into a separate extras file.
