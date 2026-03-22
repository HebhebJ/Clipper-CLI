# Clipper CLI

Local-first toolkit for short-form video production.

This repo contains two connected systems:

- `clipper-cli` desktop app (Electron + React + FFmpeg): cut clips, auto-split long videos, apply 9:16 presets, add text overlays, generate and burn subtitles with local Whisper.
- `ai-video-factory` microservice pipeline (FastAPI): generate script -> synthesize voice -> render vertical video with subtitles (and optional slideshow images).

## Current Repo Layout

```text
.
+- core/                    # Node services for clipping + subtitles
+- electron/                # Electron main/preload
+- renderer/                # React UI used by Electron
+- ai-video-factory/        # Python microservices pipeline
+- clipper.js               # CLI clipper script (JSON-config driven)
+- output_clips/            # generated clips (ignored in git)
+- videos/                  # local input videos (ignored in git)
```

## What Works Today

### Desktop clipper

- Load local video and preview timeline
- Manual clip export (`start/end`)
- Auto-split into equal chunks
- Aspect presets: original or TikTok vertical (`9:16`)
- Optional text overlay with position/style controls
- Local subtitles pipeline:
  - extract WAV via FFmpeg
  - transcribe with local `whisper.cpp`
  - burn SRT into output video

### AI video factory

- `script_service`: generates narration + scene structure + visual tags using local Ollama (`llama3`)
- `voice_service`: runs Piper TTS per scene, concatenates audio, builds aligned SRT
- `render_service`: creates black-background or slideshow-based vertical video and burns captions
- `orchestrator`: single `/generate-video` endpoint that chains script -> voice -> render

## Prerequisites

### Shared

- `ffmpeg` and `ffprobe` available on `PATH`

### Desktop clipper

- Node.js 18+
- npm
- Electron dependencies (`npm install`)
- Local Whisper setup (paths configured in [`core/config.js`](core/config.js)):
  - `whisper-cli.exe`
  - model file (for example `ggml-base.en.bin`)

### AI video factory

- Python 3.10+
- pip
- FastAPI stack (`fastapi`, `uvicorn`, `httpx`, `pydantic`)
- Piper CLI + local voice model (`PIPER_MODEL_PATH` env variable)
- Ollama + `llama3` pulled locally
- Optional for visual generation helpers: `torch`, `diffusers`, `Pillow`
- Configure environment values from [`.env.example`](.env.example)

## Quick Start

### 1) Run desktop app

```bash
# from repo root
npm install

# build renderer once
cd renderer
npm install
npm run build

# back to root and run electron
cd ..
npm start
```

### 2) Run AI video factory

```bash
cd ai-video-factory
pip install -r requirements.txt
py run_all.py
```

That starts:

- script service: `http://127.0.0.1:8001`
- voice service: `http://127.0.0.1:8002`
- render service: `http://127.0.0.1:8003`
- orchestrator: `http://127.0.0.1:8000`

Example request to orchestrator:

```bash
curl -X POST http://127.0.0.1:8000/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "How AI is changing sports training",
    "duration_seconds": 45,
    "tone": "dramatic",
    "language": "en",
    "image_folder": "C:/path/to/images"
  }'
```

## CLI Clipper (JSON config mode)

`clipper.js` supports a config-driven FFmpeg clipping flow.

```bash
node clipper.js path/to/project.json
```

Config supports either manual `clips` or `autoSplit` by duration.

## Documentation Added For This Repo

- [`ai-video-factory/README.md`](ai-video-factory/README.md)
- [`renderer/README.md`](renderer/README.md)
- [`docs/github-publish-checklist.md`](docs/github-publish-checklist.md)

## Notes Before Publishing

- Generated media, caches, and local datasets are now ignored via [`.gitignore`](.gitignore).
- Set machine-specific paths via environment variables (see [`.env.example`](.env.example)).

## License

Choose and add a license file before publishing (for example `MIT`).
