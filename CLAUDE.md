# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install in editable mode
pip install -e ".[dev]"

# Run the CLI
yt-agent --help

# Run a specific command
yt-agent publish ./video.mp4
yt-agent publish ./video.mp4 --thumbnail ./thumb.jpg --playlist PLxxxxxxxx

# Enhance (update metadata of an already-published video)
yt-agent enhance --recent 1                  # most recently uploaded video
yt-agent enhance <VIDEO_ID>                  # specific video by ID
yt-agent enhance --recent 1 --dry-run        # preview without applying

# Run tests
pytest
pytest tests/unit/test_scheduler.py          # single file
pytest -k "test_name"                        # single test

# Linting
ruff check src/
ruff format src/
```

## Architecture

The project is a CLI tool (`yt-agent`) that orchestrates a full YouTube publish workflow. The entry point is `src/yt_agent/cli.py` (typer), which delegates to `agent/orchestrator.py` for workflow coordination.

### Package Layout

```
src/yt_agent/
├── auth/oauth.py            # Shared OAuthManager (YouTube + Drive use this)
├── exceptions.py            # YTAgentError hierarchy
├── cli.py                   # Typer CLI entry point
├── config.py                # Settings (pydantic-settings) + ChannelProfile
├── agent/
│   ├── models.py            # Data-only: PublishPlan, EnhancePlan, VideoEnhancement
│   ├── presenter.py         # All console display functions (display_publish_plan, etc.)
│   └── orchestrator.py      # YouTubeAgent — workflow coordination only
├── tools/
│   ├── base.py              # BaseTool, ToolResult
│   ├── drive.py             # GoogleDriveTool (uses OAuthManager)
│   ├── transcribe.py        # TranscriptionTool (Google Speech-to-Text + GCS)
│   └── youtube/
│       ├── __init__.py      # YouTubeTool facade (backwards-compatible public API)
│       ├── _models.py       # VideoDetails, VideoUploadResult
│       ├── _video.py        # YouTubeVideoManager (upload, thumbnail, metadata, details)
│       ├── _playlist.py     # YouTubePlaylistManager (list playlists, add/list videos)
│       └── _channel.py      # YouTubeChannelManager (channel info, channel video list)
├── llm/
│   ├── base.py              # BaseLLM abstract class
│   ├── factory.py           # create_llm() factory
│   ├── claude.py            # ClaudeLLM
│   └── openai.py            # OpenAILLM
├── seo/
│   └── optimizer.py         # SEOOptimizer, VideoMetadata, Chapter
└── utils/
    ├── prompts.py            # All LLM prompt templates
    └── scheduler.py          # calculate_next_publish_time()
tests/
└── unit/
    ├── test_config.py
    ├── test_llm_factory.py
    ├── test_scheduler.py
    └── test_seo_optimizer.py
```

### Enhance Flow

Use `yt-agent enhance` to update metadata of an already-published video without re-uploading.

```
cli.py enhance command
  → YouTubeAgent.run_enhance_workflow()        [agent/orchestrator.py]
      → YouTubeTool.get_video_details()        [tools/youtube/__init__.py]
        / list_channel_videos()
        / list_playlist_videos()
      → SEOOptimizer.enhance()                 [via SEO_ENHANCEMENT_PROMPT]
      → presenter.display_enhancement_comparison()   [agent/presenter.py]
      → YouTubeTool.update_metadata()          [patches snippet, no re-upload]
```

### Publish Flow

```
cli.py publish command
  → YouTubeAgent.run_publish_workflow()        [agent/orchestrator.py]
      → GoogleDriveTool.download_video()       [if Drive URL]
      → TranscriptionTool.transcribe_with_timestamps()   [ar-EG by default]
      → SEOOptimizer.generate_chapters()       [from word timestamps]
      → SEOOptimizer.optimize()                [title, description, tags]
      → chapters inserted into description
      → presenter.display_publish_plan()       [agent/presenter.py]
      → YouTubeAgent.execute_plan()
          → YouTubeVideoManager.upload_video() [tools/youtube/_video.py]
          → YouTubeVideoManager.set_thumbnail()
          → YouTubePlaylistManager.add_to_playlist()
```

### Key Data Structures

- **`PublishPlan`** (`agent/models.py`): Holds video_source, metadata, publish_time, playlist_id, thumbnail_path
- **`VideoEnhancement`** (`agent/models.py`): Holds original + enhanced metadata for one video
- **`EnhancePlan`** (`agent/models.py`): A list of `VideoEnhancement` objects
- **`VideoMetadata`** (`seo/optimizer.py`): title, description, tags, hashtags, chapters (list of `Chapter`)
- **`Chapter`** (`seo/optimizer.py`): time (MM:SS), title — formatted into YouTube description

### Exception Hierarchy

All exceptions inherit from `YTAgentError` (`exceptions.py`). Catch `YTAgentError` in `cli.py` for clean user-facing messages.

```
YTAgentError
├── AuthError           — OAuth failures, missing credentials
├── UploadError         — YouTube upload failures
├── ConfigurationError  — invalid settings (e.g., bad time format in scheduler)
├── DriveError          — Google Drive operation failures
└── TranscriptionError
    └── GCSError        — GCS upload/download failures
```

### Auth Layer

`auth/oauth.py` provides a shared `OAuthManager` used by both `YouTubeTool` and `GoogleDriveTool`. Eliminates ~100 lines of duplicated credential management code.

```python
OAuthManager(service_name, scopes, token_filename, port)
  .load_credentials()       # loads + auto-refreshes stored token
  .authenticate()           # runs browser OAuth flow, raises AuthError on failure
  .get_valid_credentials()  # load or authenticate, always returns valid Credentials
```

### YouTubeTool Structure

`tools/youtube/__init__.py` is a thin facade that composes four focused managers:

| Manager | File | Responsibility |
| --- | --- | --- |
| `YouTubeVideoManager` | `_video.py` | upload, thumbnail, metadata update, video details |
| `YouTubePlaylistManager` | `_playlist.py` | list playlists, add to playlist, list playlist videos |
| `YouTubeChannelManager` | `_channel.py` | channel info, channel video listing |
| models | `_models.py` | `VideoDetails`, `VideoUploadResult` dataclasses |

All external imports (`from yt_agent.tools.youtube import YouTubeTool, VideoDetails`) continue to work unchanged through `__init__.py`.

### Agent Layer

`agent/` is split into three files with clear separation:

| File | Responsibility |
| --- | --- |
| `models.py` | Pure data classes — no display logic |
| `presenter.py` | All `console.print` / rich display functions |
| `orchestrator.py` | `YouTubeAgent` — workflow sequencing, calls presenter and tools |

### LLM Layer

`llm/base.py` defines `BaseLLM` with `generate()` and `generate_json()`. Both `ClaudeLLM` and `OpenAILLM` implement it. `generate_json()` strips markdown code fences and parses JSON — all SEO generation goes through this. `llm/factory.py` creates the right provider from settings.

### Transcription

For videos > 55 seconds, audio is uploaded to GCS (`GCS_BUCKET` env var) and processed via `long_running_recognize()`. For short audio, inline `recognize()` is used. The transcription language defaults to `ar-EG` in the publish workflow. Both paths validate that the extracted audio duration is > 0 before proceeding.

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
- **Tags total character limit**: 500 chars (YouTube enforces); user is warned when tags are dropped — they are not silently truncated
- **Time format validation**: `scheduler.py` raises `ConfigurationError` (not bare ValueError) for malformed `HH:MM` strings
- **Audio validation**: `transcribe.py` raises `TranscriptionError` if extracted audio duration is ≤ 0
