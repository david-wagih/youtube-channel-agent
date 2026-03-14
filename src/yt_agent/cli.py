"""CLI interface for YouTube Agent."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .agent import YouTubeAgent
from .config import ChannelProfile, settings
from .llm.factory import create_llm
from .utils.scheduler import calculate_next_publish_time, format_publish_time

app = typer.Typer(
    name="yt-agent",
    help="AI-powered YouTube channel management agent",
    no_args_is_help=True,
)
console = Console()


# ============================================================================
# Main Commands
# ============================================================================


@app.command()
def publish(
    source: str = typer.Argument(
        ...,
        help="Video file path or Google Drive URL",
    ),
    topic: Optional[str] = typer.Option(
        None,
        "--topic",
        "-t",
        help="Brief description of the video topic (skips transcription)",
    ),
    thumbnail: Optional[Path] = typer.Option(
        None,
        "--thumbnail",
        "-i",
        help="Path to thumbnail image (JPG/PNG)",
    ),
    playlist: Optional[str] = typer.Option(
        None,
        "--playlist",
        "-l",
        help="Playlist ID to add the video to",
    ),
    no_transcribe: bool = typer.Option(
        False,
        "--no-transcribe",
        help="Skip transcription and prompt for topic instead",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="LLM provider to use (claude/openai)",
    ),
):
    """Process and schedule a video for publishing.

    By default, the video is transcribed (Arabic Egyptian) to generate SEO-optimized metadata.

    Example:
        yt-agent publish ./video.mp4
        yt-agent publish ./video.mp4 --thumbnail ./thumb.jpg
        yt-agent publish ./video.mp4 --playlist PLxxxxxxxx
        yt-agent publish ./video.mp4 --topic "Python tips"  # Skip transcription
    """
    try:
        llm = create_llm(provider) if provider else create_llm()
        agent = YouTubeAgent(llm=llm)

        # Transcribe by default unless --no-transcribe or --topic is provided
        should_transcribe = not no_transcribe and not topic

        success = asyncio.run(
            agent.run_publish_workflow(
                source=source,
                topic=topic,
                auto_transcribe=should_transcribe,
                playlist_id=playlist,
                thumbnail_path=str(thumbnail) if thumbnail else None,
            )
        )

        if success:
            console.print("[bold green]Video scheduled successfully![/bold green]")
        else:
            raise typer.Exit(1)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def optimize(
    topic: str = typer.Argument(
        ...,
        help="Video topic to optimize for",
    ),
    transcript_file: Optional[Path] = typer.Option(
        None,
        "--transcript",
        "-f",
        help="Path to transcript file",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="LLM provider to use (claude/openai)",
    ),
):
    """Generate SEO-optimized metadata without uploading.

    Example:
        yt-agent optimize "Python tips for beginners"
        yt-agent optimize "Advanced React" --transcript transcript.txt
    """
    from .seo.optimizer import SEOOptimizer

    try:
        llm = create_llm(provider) if provider else create_llm()

        transcript = None
        if transcript_file and transcript_file.exists():
            transcript = transcript_file.read_text()

        optimizer = SEOOptimizer(llm)

        with console.status("[bold green]Generating SEO-optimized metadata..."):
            metadata = asyncio.run(optimizer.optimize(topic=topic, transcript=transcript))

        console.print("\n[bold]Generated Metadata:[/bold]\n")
        console.print(
            Panel.fit(
                f"[bold cyan]{metadata.title}[/bold cyan]",
                title="Title",
            )
        )
        console.print(
            Panel(
                metadata.description,
                title="Description",
            )
        )
        console.print(
            Panel(
                ", ".join(metadata.tags),
                title="Tags",
            )
        )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def schedule(
    day: Optional[str] = typer.Option(
        None,
        "--day",
        "-d",
        help="Day of week (e.g., Saturday)",
    ),
    time: Optional[str] = typer.Option(
        None,
        "--time",
        "-t",
        help="Time in HH:MM format (e.g., 19:00)",
    ),
):
    """Show the next scheduled publish time.

    Example:
        yt-agent schedule
        yt-agent schedule --day Sunday --time 18:00
    """
    try:
        next_time = calculate_next_publish_time(
            target_day=day,
            target_time=time,
        )
        console.print(
            f"\nNext publish time: [bold green]{format_publish_time(next_time)}[/bold green]"
        )

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def enhance(
    video_id: Optional[str] = typer.Argument(
        None,
        help="Video ID to enhance (optional if using --playlist or --recent)",
    ),
    playlist: Optional[str] = typer.Option(
        None,
        "--playlist",
        "-p",
        help="Playlist ID to enhance all videos from",
    ),
    recent: Optional[int] = typer.Option(
        None,
        "--recent",
        "-r",
        help="Enhance N most recent channel videos",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Interactively select which videos to enhance",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show changes without applying them",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        help="LLM provider to use (claude/openai)",
    ),
):
    """Enhance existing video SEO metadata.

    Improve titles, descriptions, and tags for better discoverability.

    Examples:
        yt-agent enhance dQw4w9WgXcQ                    # Single video
        yt-agent enhance --playlist PLxxxxxxxx          # All playlist videos
        yt-agent enhance --playlist PLxxxxxxxx -i       # Select from playlist
        yt-agent enhance --recent 5                     # Recent 5 videos
        yt-agent enhance dQw4w9WgXcQ --dry-run         # Preview changes
    """
    try:
        # Validate input
        if not video_id and not playlist and not recent:
            console.print("[bold red]Error:[/bold red] Specify a video ID, --playlist, or --recent")
            raise typer.Exit(1)

        llm = create_llm(provider) if provider else create_llm()
        agent = YouTubeAgent(llm=llm)

        success = asyncio.run(
            agent.run_enhance_workflow(
                video_id=video_id,
                playlist_id=playlist,
                recent_count=recent,
                interactive_select=interactive,
                dry_run=dry_run,
            )
        )

        if not success:
            raise typer.Exit(1)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        raise typer.Exit(1)


# ============================================================================
# Config Commands
# ============================================================================


config_app = typer.Typer(help="Manage configuration")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show():
    """Show current configuration."""
    table = Table(title="Current Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("LLM Provider", settings.default_llm_provider)
    table.add_row("Timezone", settings.default_timezone)
    table.add_row("Schedule Day", settings.default_schedule_day)
    table.add_row("Schedule Time", settings.default_schedule_time)
    table.add_row(
        "Anthropic API Key",
        "****" + settings.anthropic_api_key[-4:] if settings.anthropic_api_key else "Not set",
    )
    table.add_row(
        "OpenAI API Key",
        "****" + settings.openai_api_key[-4:] if settings.openai_api_key else "Not set",
    )

    console.print(table)


@config_app.command("profile")
def config_profile():
    """Show or edit channel profile."""
    profile = ChannelProfile()

    if not profile.is_configured():
        console.print("[yellow]Profile not configured. Let's set it up:[/yellow]\n")

        from rich.prompt import Prompt

        profile.channel_name = Prompt.ask("Channel name")
        profile.business_email = Prompt.ask("Business email (optional)", default="")

        # Social links
        console.print("\n[bold]Social links[/bold] (press Enter to skip):")
        links = {}
        for platform in ["linkedin", "twitter", "github", "instagram"]:
            url = Prompt.ask(f"  {platform.title()}", default="")
            if url:
                links[platform] = url
        profile.social_links = links

        # Default hashtags
        hashtags_str = Prompt.ask("\nDefault hashtags (comma-separated)", default="")
        if hashtags_str:
            profile.default_hashtags = [
                f"#{h.strip().lstrip('#')}" for h in hashtags_str.split(",")
            ]

        profile.save()
        console.print("\n[bold green]Profile saved![/bold green]")
    else:
        table = Table(title="Channel Profile")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Channel Name", profile.channel_name or "")
        table.add_row("Business Email", profile.business_email or "")
        table.add_row(
            "Social Links",
            "\n".join(f"{k}: {v}" for k, v in profile.social_links.items()) or "None",
        )
        table.add_row("Default Hashtags", " ".join(profile.default_hashtags) or "None")

        console.print(table)


# ============================================================================
# Auth Commands
# ============================================================================


auth_app = typer.Typer(help="Manage API authentication")
app.add_typer(auth_app, name="auth")


@auth_app.command("youtube")
def auth_youtube():
    """Authenticate with YouTube API.

    Before running this, you need to:
    1. Create a project in Google Cloud Console
    2. Enable YouTube Data API v3
    3. Create OAuth 2.0 credentials (Desktop app)
    4. Download client_secrets.json
    5. Save it to: ~/.config/yt-agent/credentials/client_secrets.json
    """
    from .config import get_credentials_dir
    from .tools.youtube import YouTubeTool

    creds_dir = get_credentials_dir()
    client_secrets = creds_dir / "client_secrets.json"

    if not client_secrets.exists():
        console.print("[bold red]Error:[/bold red] client_secrets.json not found.\n")
        console.print("To set up YouTube authentication:\n")
        console.print("1. Go to [link=https://console.cloud.google.com]Google Cloud Console[/link]")
        console.print("2. Create a new project (or select existing)")
        console.print("3. Enable 'YouTube Data API v3'")
        console.print("4. Go to 'Credentials' → 'Create Credentials' → 'OAuth client ID'")
        console.print("5. Select 'Desktop app' as application type")
        console.print("6. Download the JSON file")
        console.print(f"7. Save it as: [cyan]{client_secrets}[/cyan]")
        raise typer.Exit(1)

    youtube = YouTubeTool()
    if youtube.authenticate():
        # Show channel info
        import asyncio

        try:
            info = asyncio.run(youtube.get_channel_info())
            if info:
                console.print(
                    f"\n[bold]Connected to channel:[/bold] {info.get('title', 'Unknown')}"
                )
                console.print(f"Subscribers: {info.get('subscriber_count', '0')}")
                console.print(f"Videos: {info.get('video_count', '0')}")
        except Exception:
            pass  # Channel info is optional
    else:
        raise typer.Exit(1)


@auth_app.command("drive")
def auth_drive():
    """Authenticate with Google Drive API.

    Uses the same client_secrets.json as YouTube authentication.
    Make sure you've also enabled "Google Drive API" in your Cloud project.
    """
    from .config import get_credentials_dir
    from .tools.drive import GoogleDriveTool

    creds_dir = get_credentials_dir()
    client_secrets = creds_dir / "client_secrets.json"

    if not client_secrets.exists():
        console.print("[bold red]Error:[/bold red] client_secrets.json not found.\n")
        console.print("Use the same credentials file as YouTube.")
        console.print("Make sure 'Google Drive API' is enabled in your Cloud project.")
        console.print(f"\nExpected location: [cyan]{client_secrets}[/cyan]")
        raise typer.Exit(1)

    drive = GoogleDriveTool()
    if drive.authenticate():
        console.print("\n[bold green]Google Drive ready![/bold green]")
        console.print("You can now use Drive URLs with [cyan]yt-agent publish[/cyan]")
    else:
        raise typer.Exit(1)


# ============================================================================
# Utility
# ============================================================================


@app.command()
def transcribe(
    video_path: Path = typer.Argument(
        ...,
        help="Path to video file to transcribe",
    ),
    language: str = typer.Option(
        "ar-EG",
        "--language",
        "-l",
        help="Language code (ar-EG for Arabic, en-US for English)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Save transcript to file",
    ),
):
    """Transcribe a video file using Google Speech-to-Text.

    Requires GOOGLE_APPLICATION_CREDENTIALS environment variable.

    Example:
        yt-agent transcribe ./video.mp4
        yt-agent transcribe ./video.mp4 --language ar-EG
        yt-agent transcribe ./video.mp4 -o transcript.txt
    """
    from .tools.transcribe import TranscriptionTool

    transcriber = TranscriptionTool()

    if not transcriber.is_available():
        console.print("[bold red]Error:[/bold red] Google Cloud credentials not configured.\n")
        console.print("To set up transcription:")
        console.print("1. Create a Google Cloud project")
        console.print("2. Enable 'Cloud Speech-to-Text API'")
        console.print("3. Create a service account and download JSON key")
        console.print("4. Set environment variable:")
        console.print("   [cyan]export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json[/cyan]")
        raise typer.Exit(1)

    if not video_path.exists():
        console.print(f"[bold red]Error:[/bold red] Video not found: {video_path}")
        raise typer.Exit(1)

    try:
        console.print(f"\n[bold]Transcribing:[/bold] {video_path.name}")
        console.print(f"[dim]Language: {language}[/dim]\n")

        transcript = asyncio.run(
            transcriber.transcribe_video(
                video_path=str(video_path),
                language=language,
            )
        )

        if output:
            output.write_text(transcript, encoding="utf-8")
            console.print(f"\n[green]Saved to:[/green] {output}")
        else:
            console.print("\n[bold]Transcript:[/bold]")
            console.print(Panel(transcript, expand=False))

    except Exception as e:
        console.print(f"[bold red]Transcription failed:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def playlists():
    """List your YouTube playlists.

    Shows playlist IDs that you can use with --playlist option.

    Example:
        yt-agent playlists
        yt-agent publish ./video.mp4 --playlist PLxxxxxxxx
    """
    from .tools.youtube import YouTubeTool

    youtube = YouTubeTool()

    if not youtube.is_available():
        console.print("[bold red]Error:[/bold red] YouTube not configured.")
        console.print("Run [cyan]yt-agent auth youtube[/cyan] first.")
        raise typer.Exit(1)

    try:
        playlists_list = asyncio.run(youtube.list_playlists())

        if not playlists_list:
            console.print("[yellow]No playlists found.[/yellow]")
            return

        table = Table(title="Your Playlists")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Videos", justify="right")

        for pl in playlists_list:
            table.add_row(pl["id"], pl["title"], str(pl["video_count"]))

        console.print(table)
        console.print("\n[dim]Use: yt-agent publish ./video.mp4 --playlist <ID>[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    console.print(f"yt-agent version [bold]{__version__}[/bold]")


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
