# GitHub Publish Checklist

Use this checklist before the first public push.

## 1) Remove Machine-Specific Values

Update hardcoded local paths:

- `core/config.js`
- `ai-video-factory/voice_service/main.py`
- `ai-video-factory/run_all.bat`

Prefer environment variables for:

- Whisper executable/model
- Piper model path
- service host/port overrides

## 2) Keep Repository Clean

Already handled by root `.gitignore`, but verify no large/generated files are staged:

- `node_modules/`
- `renderer/dist/`
- `ai-video-factory/.venv/`
- `output_clips/`, `videos/`
- `ai-video-factory/tmp/`, `subtitles/`, `downloads/`, `pics/`

## 3) Add Basic Project Metadata

- Add a root `LICENSE` file (MIT/Apache-2.0/etc.)
- Fill `author`, `description`, and repository links in `package.json`
- Optionally add badges to `README.md`

## 4) Stabilize Setup

Recommended:

- `ai-video-factory/requirements.txt` is in place; consider moving to `pyproject.toml` later
- `.env.example` templates are in place; optionally add automatic `.env` loading
- Add startup validation for external binaries (`ffmpeg`, `ollama`, `piper`, `whisper`)

## 5) Smoke Test Before Push

- Desktop app:
  - build renderer
  - run `npm start`
  - export one manual clip and one auto-split set
- AI pipeline:
  - run `py run_all.py`
  - call `POST /generate-video`
  - verify output video/audio/srt paths

## 6) Suggested First Commits

1. `docs: rewrite readmes and add publish checklist`
2. `chore: add root gitignore for generated media and env files`
3. `refactor: move hardcoded paths to env`
4. `build: add python dependency manifest`

## 7) Initial Push

Example flow:

```bash
git init
git add .
git commit -m "initial: clipper + ai video factory"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

If a repo already exists, skip `git init` and just add remote/commit/push as needed.
