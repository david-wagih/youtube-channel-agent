"""Main agent orchestrator."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .config import ChannelProfile
from .llm.base import BaseLLM
from .llm.factory import create_llm
from .seo.optimizer import SEOOptimizer, VideoMetadata
from .utils.scheduler import calculate_next_publish_time, format_publish_time

console = Console()


@dataclass
class VideoEnhancement:
    """Enhancement plan for a single video."""

    video_id: str
    original_title: str
    original_description: str
    original_tags: list[str]
    view_count: int
    enhanced_metadata: VideoMetadata
    changes_summary: str | list[str]

    def _format_changes_summary(self) -> str:
        """Format changes summary as a string."""
        if isinstance(self.changes_summary, list):
            return "\n".join(f"• {item}" for item in self.changes_summary)
        return self.changes_summary

    def display_comparison(self) -> None:
        """Display before/after comparison."""
        # Title comparison
        console.print(
            Panel(
                f"[dim]Original:[/dim] {self.original_title}\n"
                f"[bold cyan]Enhanced:[/bold cyan] {self.enhanced_metadata.title}",
                title="Title Comparison",
            )
        )

        # Description preview (first 200 chars)
        orig_preview = (
            self.original_description[:200] + "..."
            if len(self.original_description) > 200
            else self.original_description
        )
        new_preview = (
            self.enhanced_metadata.description[:200] + "..."
            if len(self.enhanced_metadata.description) > 200
            else self.enhanced_metadata.description
        )

        console.print(
            Panel(
                f"[dim]Original:[/dim]\n{orig_preview}\n\n"
                f"[bold cyan]Enhanced:[/bold cyan]\n{new_preview}",
                title="Description Preview",
            )
        )

        # Tags comparison
        orig_tags = ", ".join(self.original_tags[:8]) if self.original_tags else "None"
        new_tags = ", ".join(self.enhanced_metadata.tags[:8])
        if len(self.enhanced_metadata.tags) > 8:
            new_tags += f" ... (+{len(self.enhanced_metadata.tags) - 8} more)"

        console.print(
            Panel(
                f"[dim]Original ({len(self.original_tags)}):[/dim] {orig_tags}\n"
                f"[bold cyan]Enhanced ({len(self.enhanced_metadata.tags)}):[/bold cyan] {new_tags}",
                title="Tags Comparison",
            )
        )

        # Changes summary
        console.print(
            Panel(
                self._format_changes_summary(),
                title="Changes Made",
                style="green",
            )
        )


@dataclass
class EnhancePlan:
    """Plan for enhancing multiple videos."""

    enhancements: list[VideoEnhancement]

    def display_summary(self) -> None:
        """Display summary of all enhancements."""
        table = Table(title=f"Enhancement Plan ({len(self.enhancements)} videos)")
        table.add_column("#", style="dim", width=4)
        table.add_column("Original Title", style="white")
        table.add_column("Enhanced Title", style="cyan")
        table.add_column("Views", justify="right")

        for i, enhancement in enumerate(self.enhancements, 1):
            orig_title = (
                enhancement.original_title[:40] + "..."
                if len(enhancement.original_title) > 40
                else enhancement.original_title
            )
            new_title = (
                enhancement.enhanced_metadata.title[:40] + "..."
                if len(enhancement.enhanced_metadata.title) > 40
                else enhancement.enhanced_metadata.title
            )

            table.add_row(
                str(i),
                orig_title,
                new_title,
                f"{enhancement.view_count:,}",
            )

        console.print(table)

    def display_video(self, index: int) -> None:
        """Display enhancement details for a specific video."""
        if 0 <= index < len(self.enhancements):
            self.enhancements[index].display_comparison()


@dataclass
class PublishPlan:
    """Plan for publishing a video."""

    video_source: str
    metadata: VideoMetadata
    publish_time: datetime
    is_transcribed: bool = False
    playlist_id: str | None = None
    thumbnail_path: str | None = None

    def display(self) -> None:
        """Display the publish plan to the user."""
        console.print()
        console.print(
            Panel.fit(
                f"[bold cyan]{self.metadata.title}[/bold cyan]",
                title="Title",
            )
        )

        console.print(
            Panel(
                self.metadata.description,
                title="Description",
                expand=False,
            )
        )

        # Chapters (if available)
        if self.metadata.chapters:
            chapters_text = "\n".join(f"  {ch.time} - {ch.title}" for ch in self.metadata.chapters)
            console.print(
                Panel(
                    chapters_text,
                    title=f"Chapters ({len(self.metadata.chapters)})",
                    style="cyan",
                )
            )

        # Tags table
        tags_table = Table(show_header=False, box=None)
        tags_table.add_column("Tags", style="green")
        tags_table.add_row(", ".join(self.metadata.tags[:10]))
        if len(self.metadata.tags) > 10:
            tags_table.add_row(f"... and {len(self.metadata.tags) - 10} more")
        console.print(Panel(tags_table, title="Tags"))

        # Thumbnail (if provided)
        if self.thumbnail_path:
            console.print(
                Panel(
                    f"[green]{self.thumbnail_path}[/green]",
                    title="Thumbnail",
                )
            )

        # Schedule
        console.print(
            Panel(
                f"[bold yellow]{format_publish_time(self.publish_time)}[/bold yellow]",
                title="Scheduled For",
            )
        )


class YouTubeAgent:
    """Main agent for YouTube channel management."""

    def __init__(
        self,
        llm: BaseLLM | None = None,
        profile: ChannelProfile | None = None,
    ):
        self.llm = llm or create_llm()
        self.profile = profile or ChannelProfile()
        self.seo_optimizer = SEOOptimizer(self.llm, self.profile)

    async def process_video(
        self,
        source: str,
        topic: str | None = None,
        transcript: str | None = None,
        chapters: list | None = None,
        playlist_id: str | None = None,
        thumbnail_path: str | None = None,
        schedule_day: str | None = None,
        schedule_time: str | None = None,
    ) -> PublishPlan:
        """Process a video and create a publish plan.

        Args:
            source: Path to video file or Google Drive URL.
            topic: Optional topic description (required if no transcript).
            transcript: Optional video transcript.
            chapters: Optional list of Chapter objects for video timestamps.
            playlist_id: Optional playlist ID to add the video to.
            thumbnail_path: Optional path to thumbnail image.
            schedule_day: Day to publish (e.g., "Saturday").
            schedule_time: Time to publish (e.g., "19:00").

        Returns:
            PublishPlan ready for review.
        """
        # Determine video source type
        is_drive_url = source.startswith("http") and "drive.google.com" in source
        is_local_file = Path(source).exists()

        if not is_drive_url and not is_local_file:
            raise ValueError(f"Video source not found: {source}")

        # If no topic provided, we need either transcript or to ask user
        if not topic and not transcript:
            raise ValueError("Either topic or transcript must be provided")

        # Generate SEO-optimized metadata
        with console.status("[bold green]Generating SEO-optimized metadata..."):
            metadata = await self.seo_optimizer.optimize(
                topic=topic or "Based on transcript",
                transcript=transcript,
            )

        # Add chapters to metadata
        if chapters:
            metadata.chapters = chapters
            # Insert chapters into description
            chapters_text = "\n\n⏱️ Chapters:\n" + metadata.format_chapters()
            # Insert before the social links section or at the end
            if "━━━" in metadata.description:
                # Insert before the last divider section
                parts = metadata.description.rsplit("━━━", 1)
                metadata.description = parts[0] + chapters_text + "\n\n━━━" + parts[1]
            else:
                metadata.description += chapters_text

        # Calculate publish time
        publish_time = calculate_next_publish_time(
            target_day=schedule_day,
            target_time=schedule_time,
        )

        return PublishPlan(
            video_source=source,
            metadata=metadata,
            publish_time=publish_time,
            is_transcribed=transcript is not None,
            playlist_id=playlist_id,
            thumbnail_path=thumbnail_path,
        )

    def review_plan(self, plan: PublishPlan) -> str:
        """Present plan to user and get their decision.

        Returns:
            "approve", "edit", or "cancel"
        """
        console.print("\n[bold]Review your publish plan:[/bold]")
        plan.display()

        console.print()
        choice = Prompt.ask(
            "[bold]What would you like to do?[/bold]",
            choices=["approve", "edit", "cancel"],
            default="approve",
        )
        return choice

    def edit_plan(self, plan: PublishPlan) -> PublishPlan:
        """Allow user to edit parts of the plan."""
        console.print("\n[bold]Edit mode:[/bold] (press Enter to keep current value)")

        # Edit title
        new_title = Prompt.ask(
            "Title",
            default=plan.metadata.title,
        )

        # Edit tags
        current_tags = ", ".join(plan.metadata.tags)
        new_tags_str = Prompt.ask(
            "Tags (comma-separated)",
            default=current_tags,
        )
        new_tags = [t.strip() for t in new_tags_str.split(",")]

        # Update metadata
        plan.metadata.title = new_title
        plan.metadata.tags = new_tags

        return plan

    async def execute_plan(self, plan: PublishPlan) -> bool:
        """Execute the publish plan (upload and schedule).

        Returns:
            True if successful.
        """
        from .tools.youtube import YouTubeTool

        youtube = YouTubeTool()

        # Check if YouTube is configured
        if not youtube.is_available():
            console.print("\n[bold red]YouTube not configured.[/bold red]")
            console.print("Run [cyan]yt-agent auth youtube[/cyan] first.")
            return False

        try:
            console.print("\n[bold]Uploading to YouTube...[/bold]")

            result = await youtube.upload_video(
                video_path=plan.video_source,
                title=plan.metadata.title,
                description=plan.metadata.description,
                tags=plan.metadata.tags,
                publish_at=plan.publish_time,
                thumbnail_path=plan.thumbnail_path,
                playlist_id=plan.playlist_id,
            )

            console.print()
            console.print(
                Panel(
                    f"[bold green]Video uploaded successfully![/bold green]\n\n"
                    f"Title: {result.title}\n"
                    f"Video URL: [link={result.url}]{result.url}[/link]\n"
                    f"Studio URL: [link={result.studio_url}]{result.studio_url}[/link]\n\n"
                    f"Scheduled for: {format_publish_time(plan.publish_time)}",
                    title="Upload Complete",
                )
            )

            return True

        except Exception as e:
            console.print(f"\n[bold red]Upload failed:[/bold red] {e}")
            return False

    def _is_drive_url(self, source: str) -> bool:
        """Check if source is a Google Drive URL."""
        return source.startswith("http") and "drive.google.com" in source

    async def _download_from_drive(self, url: str) -> Path:
        """Download video from Google Drive.

        Args:
            url: Google Drive URL.

        Returns:
            Path to downloaded file.
        """
        from .tools.drive import GoogleDriveTool

        drive = GoogleDriveTool()

        if not drive.is_available():
            raise RuntimeError("Google Drive not configured. Run 'yt-agent auth drive' first.")

        return await drive.download_video(url)

    async def run_publish_workflow(
        self,
        source: str,
        topic: str | None = None,
        auto_transcribe: bool = False,
        playlist_id: str | None = None,
        thumbnail_path: str | None = None,
    ) -> bool:
        """Run the full publish workflow.

        Args:
            source: Video source (file path or Drive URL).
            topic: Optional topic description.
            auto_transcribe: Whether to transcribe the video.
            playlist_id: Optional playlist ID to add the video to.
            thumbnail_path: Optional path to thumbnail image.

        Returns:
            True if video was successfully scheduled.
        """
        from .seo.optimizer import Chapter

        video_path = source
        transcript = None
        chapters: list[Chapter] = []
        video_duration = 0.0

        # If source is a Drive URL, download it first
        if self._is_drive_url(source):
            console.print("\n[bold]Detected Google Drive URL[/bold]")
            try:
                video_path = str(await self._download_from_drive(source))
            except Exception as e:
                console.print(f"[bold red]Failed to download from Drive:[/bold red] {e}")
                return False

        # If auto_transcribe is requested, do that first
        if auto_transcribe:
            from .tools.transcribe import TranscriptionTool

            transcriber = TranscriptionTool()

            if not transcriber.is_available():
                console.print(
                    "[yellow]Warning:[/yellow] Google Cloud credentials not configured.\n"
                    "Set GOOGLE_APPLICATION_CREDENTIALS in .env to enable transcription.\n"
                    "Falling back to manual topic input."
                )
            else:
                try:
                    console.print("\n[bold]Transcribing video with timestamps...[/bold]")
                    # Get transcript with timestamps for chapter generation
                    # Default to Arabic Egyptian with English technical terms
                    words_with_timestamps = await transcriber.transcribe_with_timestamps(
                        video_path,
                        language="ar-EG",
                    )

                    # Build plain transcript from words
                    transcript = " ".join(w["word"] for w in words_with_timestamps)

                    # Get video duration from last word's end time
                    if words_with_timestamps:
                        video_duration = words_with_timestamps[-1]["end_time"]

                    # Generate chapters
                    if words_with_timestamps and video_duration > 60:
                        console.print("[dim]Generating chapters...[/dim]")
                        try:
                            chapters = await self.seo_optimizer.generate_chapters(
                                words_with_timestamps,
                                video_duration,
                            )
                            console.print(f"[green]Generated {len(chapters)} chapters[/green]")
                        except Exception as e:
                            console.print(f"[yellow]Chapter generation failed:[/yellow] {e}")

                except Exception as e:
                    console.print(f"[yellow]Transcription failed:[/yellow] {e}")
                    console.print("Falling back to manual topic input.")

        # If no topic and no transcript, ask user
        if not topic and not transcript:
            topic = Prompt.ask("\n[bold]Describe your video topic[/bold] (for SEO optimization)")

        # Generate plan
        plan = await self.process_video(
            source=video_path,
            topic=topic,
            transcript=transcript,
            chapters=chapters,
            playlist_id=playlist_id,
            thumbnail_path=thumbnail_path,
        )

        # Review loop
        while True:
            decision = self.review_plan(plan)

            if decision == "approve":
                return await self.execute_plan(plan)
            elif decision == "edit":
                plan = self.edit_plan(plan)
            else:  # cancel
                console.print("[red]Cancelled.[/red]")
                return False

    async def run_enhance_workflow(
        self,
        video_id: str | None = None,
        playlist_id: str | None = None,
        recent_count: int | None = None,
        interactive_select: bool = False,
        dry_run: bool = False,
    ) -> bool:
        """Run the video enhancement workflow.

        Args:
            video_id: Single video ID to enhance.
            playlist_id: Playlist ID to enhance all videos from.
            recent_count: Number of recent channel videos to enhance.
            interactive_select: Whether to let user select videos interactively.
            dry_run: Show changes without applying them.

        Returns:
            True if enhancements were successfully applied.
        """
        from .tools.youtube import VideoDetails, YouTubeTool

        youtube = YouTubeTool()

        if not youtube.is_available():
            console.print("\n[bold red]YouTube not configured.[/bold red]")
            console.print("Run [cyan]yt-agent auth youtube[/cyan] first.")
            return False

        # Fetch videos to enhance
        videos: list[VideoDetails] = []

        try:
            if video_id:
                console.print("\n[bold]Fetching video details...[/bold]")
                video = await youtube.get_video_details(video_id)
                videos = [video]

            elif playlist_id:
                console.print("\n[bold]Fetching playlist videos...[/bold]")
                videos = await youtube.list_playlist_videos(playlist_id)
                console.print(f"Found {len(videos)} videos in playlist")

            elif recent_count:
                console.print("\n[bold]Fetching recent channel videos...[/bold]")
                videos = await youtube.list_channel_videos(max_results=recent_count)
                console.print(f"Found {len(videos)} videos")

            else:
                console.print(
                    "[bold red]Error:[/bold red] Specify --video, --playlist, or --recent"
                )
                return False

        except Exception as e:
            console.print(f"[bold red]Failed to fetch videos:[/bold red] {e}")
            return False

        if not videos:
            console.print("[yellow]No videos found.[/yellow]")
            return False

        # Interactive selection
        if interactive_select and len(videos) > 1:
            videos = self._select_videos_interactive(videos)
            if not videos:
                console.print("[red]No videos selected.[/red]")
                return False

        # Generate enhancements
        enhancements: list[VideoEnhancement] = []

        console.print("\n[bold]Generating enhancements...[/bold]")

        for i, video in enumerate(videos, 1):
            console.print(f"  Video {i}/{len(videos)}: {video.title[:50]}...", end="")

            try:
                enhanced_metadata, changes_summary = await self.seo_optimizer.enhance(
                    current_title=video.title,
                    current_description=video.description,
                    current_tags=video.tags,
                    view_count=video.view_count,
                )

                enhancements.append(
                    VideoEnhancement(
                        video_id=video.video_id,
                        original_title=video.title,
                        original_description=video.description,
                        original_tags=video.tags,
                        view_count=video.view_count,
                        enhanced_metadata=enhanced_metadata,
                        changes_summary=changes_summary,
                    )
                )
                console.print(" [green]✓[/green]")

            except Exception as e:
                console.print(f" [red]✗[/red] ({e})")

        if not enhancements:
            console.print("[red]No enhancements generated.[/red]")
            return False

        # Create plan
        plan = EnhancePlan(enhancements=enhancements)

        # Display and review
        if len(enhancements) == 1:
            # Single video - show detailed comparison
            console.print()
            enhancements[0].display_comparison()
        else:
            # Multiple videos - show summary table
            console.print()
            plan.display_summary()

        if dry_run:
            console.print("\n[yellow]Dry run mode - no changes applied.[/yellow]")
            return True

        # Get user decision
        if len(enhancements) == 1:
            choice = Prompt.ask(
                "\n[bold]What would you like to do?[/bold]",
                choices=["approve", "edit", "cancel"],
                default="approve",
            )

            if choice == "cancel":
                console.print("[red]Cancelled.[/red]")
                return False
            elif choice == "edit":
                enhancements[0] = self._edit_enhancement(enhancements[0])
                enhancements[0].display_comparison()

                if not Confirm.ask("\n[bold]Apply these changes?[/bold]"):
                    console.print("[red]Cancelled.[/red]")
                    return False

        else:
            choice = Prompt.ask(
                "\n[bold]Apply changes?[/bold]",
                choices=["yes", "review-each", "cancel"],
                default="yes",
            )

            if choice == "cancel":
                console.print("[red]Cancelled.[/red]")
                return False
            elif choice == "review-each":
                approved_enhancements = []
                for i, enhancement in enumerate(enhancements):
                    console.print(f"\n[bold]Video {i + 1}/{len(enhancements)}[/bold]")
                    enhancement.display_comparison()

                    if Confirm.ask("Apply this enhancement?", default=True):
                        approved_enhancements.append(enhancement)
                    else:
                        console.print("[dim]Skipped.[/dim]")

                enhancements = approved_enhancements
                if not enhancements:
                    console.print("[yellow]No enhancements to apply.[/yellow]")
                    return False

        # Apply enhancements
        console.print(f"\n[bold]Applying {len(enhancements)} enhancement(s)...[/bold]")

        success_count = 0
        for enhancement in enhancements:
            try:
                await youtube.update_metadata(
                    video_id=enhancement.video_id,
                    title=enhancement.enhanced_metadata.title,
                    description=enhancement.enhanced_metadata.description,
                    tags=enhancement.enhanced_metadata.tags,
                )
                console.print(f"  [green]✓[/green] {enhancement.enhanced_metadata.title[:50]}")
                success_count += 1
            except Exception as e:
                console.print(f"  [red]✗[/red] {enhancement.original_title[:50]}: {e}")

        console.print(
            f"\n[bold green]Applied {success_count}/{len(enhancements)} enhancements.[/bold green]"
        )
        return success_count > 0

    def _select_videos_interactive(self, videos: list) -> list:
        """Let user select which videos to enhance."""

        # Display available videos
        table = Table(title="Available Videos")
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="white")
        table.add_column("Views", justify="right")
        table.add_column("Published", style="dim")

        for i, video in enumerate(videos, 1):
            published = video.published_at.strftime("%Y-%m-%d") if video.published_at else "N/A"
            table.add_row(
                str(i),
                video.title[:50] + "..." if len(video.title) > 50 else video.title,
                f"{video.view_count:,}",
                published,
            )

        console.print(table)

        # Get selection
        selection = Prompt.ask(
            "\n[bold]Select videos[/bold] (e.g., 1,3,5 or 1-5 or 'all')",
            default="all",
        )

        if selection.lower() == "all":
            return videos

        # Parse selection
        selected_indices = set()
        for part in selection.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                for i in range(int(start), int(end) + 1):
                    selected_indices.add(i)
            else:
                selected_indices.add(int(part))

        return [videos[i - 1] for i in sorted(selected_indices) if 1 <= i <= len(videos)]

    def _edit_enhancement(self, enhancement: VideoEnhancement) -> VideoEnhancement:
        """Allow user to edit an enhancement."""
        console.print("\n[bold]Edit mode:[/bold] (press Enter to keep current value)")

        # Edit title
        new_title = Prompt.ask(
            "Title",
            default=enhancement.enhanced_metadata.title,
        )

        # Edit tags
        current_tags = ", ".join(enhancement.enhanced_metadata.tags)
        new_tags_str = Prompt.ask(
            "Tags (comma-separated)",
            default=current_tags,
        )
        new_tags = [t.strip() for t in new_tags_str.split(",")]

        # Update metadata
        enhancement.enhanced_metadata.title = new_title
        enhancement.enhanced_metadata.tags = new_tags

        return enhancement
