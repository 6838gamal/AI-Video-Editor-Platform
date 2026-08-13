# Video Editor

A lightweight MVP web application to upload, edit, and process videos with FFmpeg. Built with FastAPI, Jinja2, and vanilla JavaScript.

## Quick Start

```bash
docker compose up --build
```

Open: http://localhost:8000

## Default Configuration

The app works out of the box with sensible defaults — no `.env` file required.

- **App**: `Video Editor`, debug on, development mode
- **Storage**: `/app/storage`
- **Max upload**: 500 MB
- **Max duration**: 3600 seconds (1 hour)
- **Tools**: `ffmpeg`, `ffprobe`, `yt-dlp` (installed in the image)
- **Fallback user**: enabled (`demo@example.com`)

## Database

PostgreSQL is used **only** for users (authentication). The `users` table stores `email`, `password_hash`, and timestamps.

- Host: `db:5432`
- Database: `video_editor`
- User / password: `postgres` / `postgres`

## Degraded Mode

If PostgreSQL is unavailable, FastAPI keeps running. Upload, YouTube download, FFmpeg processing, preview, and download all continue to work. A fallback runtime user (`demo@example.com`) is used for file ownership, and a warning banner is shown:

> Database unavailable — running in degraded mode.

## Video Storage

Videos are stored on the filesystem, not in the database:

```
storage/users/{user_id}/
├── videos/{video_id}/original.mp4
├── outputs/
├── temp/
└── projects/
```

## YouTube

Paste a YouTube URL to download a video with `yt-dlp`. The downloaded file appears in your dashboard like an uploaded video.

## FFmpeg

All processing uses FFmpeg via safe `subprocess` calls (no `shell=True`, no raw user commands). Supported operations:

- Trim, Cut, Remove segment
- Replace audio, Add background music, Volume
- Speed, Resize, Crop, Rotate
- Text overlay, Fade, Compress

## Optional AI

AI is optional. Without an API key, the editor works fully in manual mode and shows:

> AI is not configured. Manual editing is available.

When configured, you can type natural-language instructions (including Arabic, e.g. "احذف أول 5 ثواني وأضف موسيقى هادئة") and the AI converts them into a structured editing plan. The AI never generates shell or FFmpeg commands — only an editing plan.

## Core Flow

```
Upload / YouTube → Video → FFprobe → Editing Plan → FFmpeg → Result → Preview → Download
```
