# youtube-channel-agent

An AI-powered CLI tool that automates the full YouTube video publishing workflow: it transcribes a video using Google Speech-to-Text, generates SEO-optimized titles, descriptions, tags, and chapter timestamps via Claude or OpenAI, then uploads the video to YouTube and schedules it — all from a single command.

## Getting started

**Prerequisites:** Python 3.11+, a Google Cloud project with YouTube Data API v3 enabled, and at least one LLM API key.

```bash
# Install
pip install -e .

# Set environment variables (copy and edit .env.example)
cp .env.example .env

# Authenticate with YouTube (opens browser for OAuth)
yt-agent auth youtube

# Optional: authenticate with Google Drive
yt-agent auth drive

# Configure your channel profile (name, social links, hashtags)
yt-agent config profile

# Publish a video
yt-agent publish ./video.mp4 --topic "Your video topic"
```

## Architecture

The CLI entry point is `src/yt_agent/cli.py` (Typer). It delegates to `YouTubeAgent` in `agent.py` for orchestration.

**Publish flow:**

```
yt-agent publish
  → GoogleDriveTool.download_video()              [if Drive URL]
  → TranscriptionTool.transcribe_with_timestamps() [if --transcribe]
  → SEOOptimizer.generate_chapters()              [from word timestamps]
  → SEOOptimizer.optimize()                       [title, description, tags]
  → PublishPlan shown for review
  → YouTubeTool.upload_video()
  → YouTubeTool.set_thumbnail()                   [if --thumbnail]
  → YouTubeTool.add_to_playlist()                 [if --playlist]
```

**Key modules:**

| Path | Purpose |
|---|---|
| `src/yt_agent/cli.py` | Typer CLI commands |
| `src/yt_agent/agent.py` | Main orchestrator (`YouTubeAgent`) |
| `src/yt_agent/llm/` | LLM providers: `ClaudeLLM`, `OpenAILLM`, factory |
| `src/yt_agent/tools/youtube.py` | YouTube Data API v3 upload & scheduling |
| `src/yt_agent/tools/drive.py` | Google Drive download |
| `src/yt_agent/tools/transcribe.py` | Google Speech-to-Text (sync and long-running) |
| `src/yt_agent/seo/optimizer.py` | SEO generation via LLM (`VideoMetadata`, `Chapter`) |
| `src/yt_agent/utils/prompts.py` | All LLM prompt templates |
| `src/yt_agent/utils/scheduler.py` | Next-publish-time calculation |
| `src/yt_agent/config.py` | Settings via pydantic-settings |

**Transcription:** Videos longer than 55 seconds have their audio uploaded to a GCS bucket and processed via `long_running_recognize()`. Shorter videos use inline `recognize()`. Default language: `ar-EG`.

**LLM layer:** `BaseLLM` defines `generate()` and `generate_json()`. `generate_json()` strips markdown fences and parses JSON. The active provider is selected via `LLMFactory` based on settings.

## Configuration

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes (or OpenAI) | Claude API key |
| `OPENAI_API_KEY` | Yes (or Anthropic) | OpenAI API key |
| `GOOGLE_APPLICATION_CREDENTIALS` | For transcription | Path to GCP service account JSON |
| `GCS_BUCKET` | For videos > 1 min | GCS bucket name for audio upload |

### OAuth credentials

Stored in `~/.config/yt-agent/credentials/`:

- `client_secrets.json` — downloaded from Google Cloud Console (OAuth Desktop app)
- `youtube_token.json` — auto-created after `yt-agent auth youtube`
- `drive_token.json` — auto-created after `yt-agent auth drive`

### Channel profile

Saved to `~/.config/yt-agent/profile.yaml` via `yt-agent config profile`. Contains channel name, social links, and default hashtags used in every video description.

## CLI commands

```bash
# Publish a video (full workflow)
yt-agent publish <file-or-drive-url> [--topic TEXT] [--transcribe] [--thumbnail PATH] [--playlist PLAYLIST_ID] [--provider claude|openai]

# Generate SEO metadata only (no upload)
yt-agent optimize <topic> [--transcript FILE]

# Show next scheduled publish time
yt-agent schedule [--day DAY] [--time HH:MM]

# OAuth authentication
yt-agent auth youtube
yt-agent auth drive

# Configuration
yt-agent config show
yt-agent config profile
```

**Defaults:**
- Schedule: every Saturday at 19:00 Cairo time (`Africa/Cairo`)
- YouTube category: `28` (Science & Technology)
- Transcription language: `ar-EG`
- Chapters: only generated for videos longer than 60 seconds; first chapter must be `0:00`
- Tags: capped at 500 characters total; hashtags capped at 5
