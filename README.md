# YouTube Channel Agent

AI-powered CLI tool for YouTube channel management. Automates video scheduling, SEO optimization, and metadata generation.

## Features

- **SEO Optimization**: Generate optimized titles, descriptions, and tags using AI (Claude or OpenAI)
- **Smart Scheduling**: Automatically schedule videos (default: Saturday 7PM Cairo time)
- **Video Transcription**: Auto-transcribe videos using Google Speech-to-Text for better SEO
- **Google Drive Support**: Download videos directly from Drive links
- **Multi-LLM Support**: Works with Claude or OpenAI (configurable)
- **Review Workflow**: Always shows you the plan before uploading

## Installation

```bash
pip install -e .
```

## Setup

### 1. Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# LLM Provider (at least one required)
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx

# Optional: For video transcription
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### 2. Google Cloud Setup (for YouTube upload)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable these APIs:
   - YouTube Data API v3
   - Google Drive API (if using Drive links)
   - Cloud Speech-to-Text API (if using transcription)
4. Create OAuth credentials:
   - Go to Credentials → Create Credentials → OAuth client ID
   - Select "Desktop app"
   - Download the JSON file
   - Save as: `~/.config/yt-agent/credentials/client_secrets.json`

### 3. Authenticate

```bash
# Required: YouTube authentication
yt-agent auth youtube

# Optional: Google Drive authentication
yt-agent auth drive
```

### 4. Configure Your Profile

```bash
yt-agent config profile
```

This saves your channel name, social links, and default hashtags for consistent descriptions.

## Usage

### Publish a Video

```bash
# From local file with topic description
yt-agent publish ./video.mp4 --topic "Python tips for beginners"

# From Google Drive
yt-agent publish "https://drive.google.com/file/d/xxx/view" --topic "React tutorial"

# With auto-transcription (analyzes video content)
yt-agent publish ./video.mp4 --transcribe

# Using specific LLM provider
yt-agent publish ./video.mp4 --topic "..." --provider openai
```

### Generate SEO Metadata Only

```bash
# Just get title, description, tags without uploading
yt-agent optimize "Building a REST API with FastAPI"

# With existing transcript file
yt-agent optimize "FastAPI tutorial" --transcript transcript.txt
```

### Check Schedule

```bash
# Show next publish time
yt-agent schedule

# Custom schedule
yt-agent schedule --day Sunday --time 18:00
```

### Configuration

```bash
# Show all settings
yt-agent config show

# Setup/edit channel profile
yt-agent config profile
```

## Workflow

When you run `yt-agent publish`, the agent:

1. **Downloads** video (if Google Drive URL)
2. **Transcribes** video (if `--transcribe` flag)
3. **Generates** SEO-optimized title, description, and tags
4. **Shows** you the plan for review
5. **Uploads** to YouTube after your approval
6. **Schedules** for your preferred time (default: Saturday 7PM Cairo)

You can edit or cancel at the review step.

## Project Structure

```
src/yt_agent/
├── cli.py           # CLI commands
├── agent.py         # Main orchestrator
├── config.py        # Settings management
├── llm/             # LLM providers (Claude, OpenAI)
├── tools/           # API integrations
│   ├── youtube.py   # YouTube upload & scheduling
│   ├── drive.py     # Google Drive download
│   └── transcribe.py # Speech-to-Text
├── seo/             # SEO optimization
└── utils/           # Scheduling, prompts
```

## Project Status

- [x] Phase 1: Foundation (CLI, LLM integration, SEO optimization)
- [x] Phase 2: Core Tools (YouTube API, Drive, Transcription)
- [x] Phase 3: Agent Logic (Full orchestration)
- [ ] Phase 4: Polish (Error handling, tests)
- [ ] Phase 5: Extensions (LinkedIn integration, thumbnails)

## License

MIT
