# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install in editable mode
pip install -e .

# Run the CLI
yt-agent --help

# Run a specific command
yt-agent publish ./video.mp4
yt-agent publish ./video.mp4 --thumbnail ./thumb.jpg --playlist PLxxxxxxxx

# Run tests
pytest
pytest tests/test_agent.py          # single file
pytest -k "test_name"               # single test

# Linting
ruff check src/
ruff format src/
```

## Architecture

The project is a CLI tool (`yt-agent`) that orchestrates a full YouTube publish workflow. The entry point is `src/yt_agent/cli.py` (typer), which delegates to `agent.py` for orchestration.

### Publish Flow

```
cli.py publish command
  → YouTubeAgent.run_publish_workflow()
      → GoogleDriveTool.download_video()       [if Drive URL]
      → TranscriptionTool.transcribe_with_timestamps()   [ar-EG by default]
      → SEOOptimizer.generate_chapters()       [from word timestamps]
      → SEOOptimizer.optimize()                [title, description, tags]
      → chapters inserted into description
      → PublishPlan displayed for review
      → YouTubeAgent.execute_plan()
          → YouTubeTool.upload_video()
          → YouTubeTool.set_thumbnail()        [if thumbnail_path]
          → YouTubeTool.add_to_playlist()      [if playlist_id]
```

### Key Data Structures

- **`PublishPlan`** (`agent.py`): Holds video_source, metadata, publish_time, playlist_id, thumbnail_path
- **`VideoMetadata`** (`seo/optimizer.py`): title, description, tags, hashtags, chapters (list of `Chapter`)
- **`Chapter`** (`seo/optimizer.py`): time (MM:SS), title — formatted into YouTube description for chapter markers

### LLM Layer

`llm/base.py` defines `BaseLLM` with `generate()` and `generate_json()`. Both `ClaudeLLM` and `OpenAILLM` implement it. `generate_json()` strips markdown code fences and parses JSON — all SEO generation goes through this. `llm/factory.py` creates the right provider from settings.

### Transcription

For videos > 55 seconds, audio is uploaded to GCS (`GCS_BUCKET` env var) and processed via `long_running_recognize()`. For short audio, inline `recognize()` is used. The transcription language defaults to `ar-EG` in the publish workflow.

### SEO Prompts

All prompts are in `utils/prompts.py`:

- `SEO_OPTIMIZATION_PROMPT` — used for new videos, Arabic Egyptian audience, technical terms stay in English
- `SEO_ENHANCEMENT_PROMPT` — used for updating existing video metadata
- `CHAPTER_GENERATION_PROMPT` — generates YouTube chapter timestamps from word-level transcript

The enhancement prompt is hardcoded for "DevOps with David" channel specifics (Arabic Egyptian, Saturday 7PM Cairo). The optimization prompt follows the same language rules.

### OAuth Credentials

Stored in `~/.config/yt-agent/credentials/`:

- `client_secrets.json` — downloaded from Google Cloud Console
- `youtube_token.json` — auto-created after `yt-agent auth youtube`
- `drive_token.json` — auto-created after `yt-agent auth drive`

Channel profile (channel name, social links, hashtags) saved to `~/.config/yt-agent/profile.yaml`.

## Environment Variables

```bash
ANTHROPIC_API_KEY=         # Required for Claude (default LLM)
OPENAI_API_KEY=            # Required for OpenAI
GOOGLE_APPLICATION_CREDENTIALS=  # Service account JSON for Speech-to-Text
GCS_BUCKET=                # Required for transcribing videos > 1 minute
```

## Important Conventions

- **Default schedule**: Every Saturday at 19:00 Cairo time (`Africa/Cairo`), calculated in `utils/scheduler.py`
- **YouTube category**: `28` (Science & Technology) — set in `upload_video()`
- **Transcription language**: `ar-EG` in the publish workflow; `ar-EG` default in the standalone `transcribe` CLI command
- **Chapters**: Only generated for videos longer than 60 seconds; first chapter must be `0:00`
- **Tags total character limit**: 500 chars (YouTube enforces); hashtags max 5 (more than 15 = YouTube ignores all)
