# Renderer (React UI)

Frontend for the Electron desktop clipper.

This app does not talk to backend HTTP APIs directly. It communicates with Electron through `window.clipperApi` exposed by `electron/preload.js`.

## Features Exposed In UI

- Browse/select local input video
- Preview video and read live playhead time
- Set manual clip `start`/`end` from playhead
- Export manual clip with:
  - aspect preset (`original` or `tiktok-9-16`)
  - optional text overlay styling
  - optional local subtitle generation and burn-in
- Auto-split full video into equal chunks with optional part labels
- Real-time log panel (FFmpeg / Whisper / service logs)

## Key Files

- `src/App.tsx`: main layout and shared state
- `src/components/VideoPreview.tsx`: input picker + video element + playhead tracking
- `src/components/ManualClipPanel.tsx`: manual export flow + subtitle toggles
- `src/components/AutoSplitPanel.tsx`: chunking workflow
- `src/hooks/useClipperApi.ts`: log subscription + IPC wrapper hook
- `src/types/global.d.ts`: type definitions for `window.clipperApi`

## Development

```bash
cd renderer
npm install
npm run dev
```

## Production Build For Electron

Electron loads `renderer/dist/index.html`, so build before launching desktop app:

```bash
cd renderer
npm run build
```

Then from repo root:

```bash
npm start
```

## Notes

- UI style is currently minimal and dark.
- `src/App.css` still contains default Vite styles and can be cleaned up further.
- If IPC contracts change in `electron/preload.js`, update `src/types/global.d.ts` and panel payloads together.
