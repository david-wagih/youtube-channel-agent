"""Main agent orchestrator — workflow coordination only.

This module is responsible for sequencing steps (download → transcribe →
optimise → review → upload).  Display is delegated to presenter.py and
data structures live in models.py.
"""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..config import ChannelProfile
from ..exceptions import DriveError
from ..llm.base import BaseLLM
from ..llm.factory import create_llm
from ..seo.optimizer import SEOOptimizer
from ..utils.scheduler import calculate_next_publish_time, format_publish_time
from . import presenter
from .models import EnhancePlan, PublishPlan, VideoEnhancement

console = Console()

_MSG_CANCELLED = "[red]Cancelled.[/red]"


class YouTubeAgent:
    """Orchestrates the publish and enhance workflows."""

    def __init__(
        self,
        llm: BaseLLM | None = None,
        profile: ChannelProfile | None = None,
    ) -> None:
        self.llm = llm or create_llm()
        self.profile = profile or ChannelProfile()
        self.seo_optimizer = SEOOptimizer(self.llm, self.profile)

    # ------------------------------------------------------------------
    # Publish workflow
    # ------------------------------------------------------------------

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
        """Build a PublishPlan from a video source and optional transcript."""
        is_drive_url = source.startswith("http") and "drive.google.com" in source
        is_local_file = Path(source).exists()

        if not is_drive_url and not is_local_file:
            raise ValueError(f"Video source not found: {source}")
        if not topic and not transcript:
            raise ValueError("Either topic or transcript must be provided")

        with console.status("[bold green]Generating SEO-optimized metadata..."):
            metadata = await self.seo_optimizer.optimize(
                topic=topic or "Based on transcript",
                transcript=transcript,
            )

        if chapters:
            metadata.chapters = chapters
            chapters_text = "\n\n⏱️ Chapters:\n" + metadata.format_chapters()
            if "━━━" in metadata.description:
                parts = metadata.description.rsplit("━━━", 1)
                metadata.description = parts[0] + chapters_text + "\n\n━━━" + parts[1]
            else:
                metadata.description += chapters_text

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
        """Show the plan and return the user's choice: approve / edit / cancel."""
        console.print("\n[bold]Review your publish plan:[/bold]")
        presenter.display_publish_plan(plan)
        console.print()
        return Prompt.ask(
            "[bold]What would you like to do?[/bold]",
            choices=["approve", "edit", "cancel"],
            default="approve",
        )

    def edit_plan(self, plan: PublishPlan) -> PublishPlan:
        """Interactive editor for title and tags."""
        console.print("\n[bold]Edit mode:[/bold] (press Enter to keep current value)")
        plan.metadata.title = Prompt.ask("Title", default=plan.metadata.title)
        new_tags_str = Prompt.ask(
            "Tags (comma-separated)", default=", ".join(plan.metadata.tags)
        )
        plan.metadata.tags = [t.strip() for t in new_tags_str.split(",")]
        return plan

    async def execute_plan(self, plan: PublishPlan) -> bool:
        """Upload and schedule the video. Returns True on success."""
        from ..tools.youtube import YouTubeTool

        youtube = YouTubeTool()
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

    async def run_publish_workflow(
        self,
        source: str,
        topic: str | None = None,
        auto_transcribe: bool = False,
        playlist_id: str | None = None,
        thumbnail_path: str | None = None,
    ) -> bool:
        """Run the full publish workflow end-to-end."""
        from ..seo.optimizer import Chapter

        video_path = source
        transcript: str | None = None
        chapters: list[Chapter] = []

        if self._is_drive_url(source):
            console.print("\n[bold]Detected Google Drive URL[/bold]")
            try:
                video_path = str(await self._download_from_drive(source))
            except Exception as e:
                console.print(f"[bold red]Failed to download from Drive:[/bold red] {e}")
                return False

        if auto_transcribe:
            transcript, chapters = await self._run_transcription(video_path)

        if not topic and not transcript:
            topic = Prompt.ask(
                "\n[bold]Describe your video topic[/bold] (for SEO optimization)"
            )

        plan = await self.process_video(
            source=video_path,
            topic=topic,
            transcript=transcript,
            chapters=chapters,
            playlist_id=playlist_id,
            thumbnail_path=thumbnail_path,
        )

        while True:
            decision = self.review_plan(plan)
            if decision == "approve":
                return await self.execute_plan(plan)
            if decision == "edit":
                plan = self.edit_plan(plan)
            else:
                console.print(_MSG_CANCELLED)
                return False

    async def _run_transcription(self, video_path: str) -> tuple[str | None, list]:
        """Transcribe a video and generate chapters. Returns (transcript, chapters)."""
        from ..seo.optimizer import Chapter
        from ..tools.transcribe import TranscriptionTool

        transcriber = TranscriptionTool()
        if not transcriber.is_available():
            console.print(
                "[yellow]Warning:[/yellow] Google Cloud credentials not configured.\n"
                "Set GOOGLE_APPLICATION_CREDENTIALS in .env to enable transcription.\n"
                "Falling back to manual topic input."
            )
            return None, []

        try:
            console.print("\n[bold]Transcribing video with timestamps...[/bold]")
            words = await transcriber.transcribe_with_timestamps(video_path, language="ar-EG")
            transcript = " ".join(w["word"] for w in words)
            video_duration = words[-1]["end_time"] if words else 0.0

            chapters: list[Chapter] = []
            if words and video_duration > 60:
                console.print("[dim]Generating chapters...[/dim]")
                try:
                    chapters = await self.seo_optimizer.generate_chapters(words, video_duration)
                    console.print(f"[green]Generated {len(chapters)} chapters[/green]")
                except Exception as e:
                    console.print(f"[yellow]Chapter generation failed:[/yellow] {e}")

            return transcript, chapters

        except Exception as e:
            console.print(f"[yellow]Transcription failed:[/yellow] {e}")
            console.print("Falling back to manual topic input.")
            return None, []

    # ------------------------------------------------------------------
    # Enhance workflow
    # ------------------------------------------------------------------

    async def run_enhance_workflow(
        self,
        video_id: str | None = None,
        playlist_id: str | None = None,
        recent_count: int | None = None,
        interactive_select: bool = False,
        dry_run: bool = False,
    ) -> bool:
        """Run the video metadata enhancement workflow end-to-end."""
        from ..tools.youtube import VideoDetails, YouTubeTool

        youtube = YouTubeTool()
        if not youtube.is_available():
            console.print("\n[bold red]YouTube not configured.[/bold red]")
            console.print("Run [cyan]yt-agent auth youtube[/cyan] first.")
            return False

        videos: list[VideoDetails] = await self._fetch_videos(
            youtube, video_id, playlist_id, recent_count
        )
        if videos is None:
            return False
        if not videos:
            console.print("[yellow]No videos found.[/yellow]")
            return False

        if interactive_select and len(videos) > 1:
            videos = self._select_videos_interactive(videos)
            if not videos:
                console.print("[red]No videos selected.[/red]")
                return False

        enhancements = await self._generate_enhancements(videos)
        if not enhancements:
            console.print("[red]No enhancements generated.[/red]")
            return False

        plan = EnhancePlan(enhancements=enhancements)
        console.print()
        if len(enhancements) == 1:
            presenter.display_enhancement_comparison(enhancements[0])
        else:
            presenter.display_enhance_plan_summary(plan)

        if dry_run:
            console.print("\n[yellow]Dry run mode - no changes applied.[/yellow]")
            return True

        approved = await self._get_enhancement_approval(enhancements)
        if approved is None:
            return False

        return await self._apply_enhancements(youtube, approved)

    async def _fetch_videos(self, youtube, video_id, playlist_id, recent_count):
        """Fetch the list of videos to enhance. Returns None on error."""

        try:
            if video_id:
                console.print("\n[bold]Fetching video details...[/bold]")
                return [await youtube.get_video_details(video_id)]
            if playlist_id:
                console.print("\n[bold]Fetching playlist videos...[/bold]")
                videos = await youtube.list_playlist_videos(playlist_id)
                console.print(f"Found {len(videos)} videos in playlist")
                return videos
            if recent_count:
                console.print("\n[bold]Fetching recent channel videos...[/bold]")
                videos = await youtube.list_channel_videos(max_results=recent_count)
                console.print(f"Found {len(videos)} videos")
                return videos
            console.print("[bold red]Error:[/bold red] Specify --video, --playlist, or --recent")
            return None
        except Exception as e:
            console.print(f"[bold red]Failed to fetch videos:[/bold red] {e}")
            return None

    async def _generate_enhancements(self, videos: list) -> list[VideoEnhancement]:
        """Run SEO enhancement for each video. Failures are skipped with a warning."""
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

        return enhancements

    async def _get_enhancement_approval(
        self, enhancements: list[VideoEnhancement]
    ) -> list[VideoEnhancement] | None:
        """Prompt the user to approve/edit/cancel. Returns approved list or None."""
        if len(enhancements) == 1:
            return await self._approve_single_enhancement(enhancements)
        return await self._approve_bulk_enhancements(enhancements)

    async def _approve_single_enhancement(
        self, enhancements: list[VideoEnhancement]
    ) -> list[VideoEnhancement] | None:
        choice = Prompt.ask(
            "\n[bold]What would you like to do?[/bold]",
            choices=["approve", "edit", "cancel"],
            default="approve",
        )
        if choice == "cancel":
            console.print(_MSG_CANCELLED)
            return None
        if choice == "edit":
            enhancements[0] = self._edit_enhancement(enhancements[0])
            presenter.display_enhancement_comparison(enhancements[0])
            if not Confirm.ask("\n[bold]Apply these changes?[/bold]"):
                console.print(_MSG_CANCELLED)
                return None
        return enhancements

    async def _approve_bulk_enhancements(
        self, enhancements: list[VideoEnhancement]
    ) -> list[VideoEnhancement] | None:
        choice = Prompt.ask(
            "\n[bold]Apply changes?[/bold]",
            choices=["yes", "review-each", "cancel"],
            default="yes",
        )
        if choice == "cancel":
            console.print(_MSG_CANCELLED)
            return None
        if choice == "review-each":
            approved = []
            for i, enhancement in enumerate(enhancements):
                console.print(f"\n[bold]Video {i + 1}/{len(enhancements)}[/bold]")
                presenter.display_enhancement_comparison(enhancement)
                if Confirm.ask("Apply this enhancement?", default=True):
                    approved.append(enhancement)
                else:
                    console.print("[dim]Skipped.[/dim]")
            if not approved:
                console.print("[yellow]No enhancements to apply.[/yellow]")
                return None
            return approved
        return enhancements

    async def _apply_enhancements(self, youtube, enhancements: list[VideoEnhancement]) -> bool:
        """Push metadata updates to YouTube. Returns True if at least one succeeded."""
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
                console.print(
                    f"  [green]✓[/green] {enhancement.enhanced_metadata.title[:50]}"
                )
                success_count += 1
            except Exception as e:
                console.print(f"  [red]✗[/red] {enhancement.original_title[:50]}: {e}")

        console.print(
            f"\n[bold green]Applied {success_count}/{len(enhancements)} enhancements."
            "[/bold green]"
        )
        return success_count > 0

    # ------------------------------------------------------------------
    # Interactive UI helpers
    # ------------------------------------------------------------------

    def _select_videos_interactive(self, videos: list) -> list:
        """Let the user pick a subset of videos to enhance."""
        table = Table(title="Available Videos")
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="white")
        table.add_column("Views", justify="right")
        table.add_column("Published", style="dim")

        for i, video in enumerate(videos, 1):
            published = video.published_at.strftime("%Y-%m-%d") if video.published_at else "N/A"
            title = video.title[:50] + "..." if len(video.title) > 50 else video.title
            table.add_row(str(i), title, f"{video.view_count:,}", published)

        console.print(table)
        selection = Prompt.ask(
            "\n[bold]Select videos[/bold] (e.g., 1,3,5 or 1-5 or 'all')",
            default="all",
        )

        if selection.lower() == "all":
            return videos

        selected: set[int] = set()
        for part in selection.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                selected.update(range(int(start), int(end) + 1))
            else:
                selected.add(int(part))

        return [videos[i - 1] for i in sorted(selected) if 1 <= i <= len(videos)]

    def _edit_enhancement(self, enhancement: VideoEnhancement) -> VideoEnhancement:
        """Interactive editor for a single enhancement's title and tags."""
        console.print("\n[bold]Edit mode:[/bold] (press Enter to keep current value)")
        enhancement.enhanced_metadata.title = Prompt.ask(
            "Title", default=enhancement.enhanced_metadata.title
        )
        new_tags_str = Prompt.ask(
            "Tags (comma-separated)",
            default=", ".join(enhancement.enhanced_metadata.tags),
        )
        enhancement.enhanced_metadata.tags = [t.strip() for t in new_tags_str.split(",")]
        return enhancement

    # ------------------------------------------------------------------
    # Drive helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_drive_url(source: str) -> bool:
        return source.startswith("http") and "drive.google.com" in source

    async def _download_from_drive(self, url: str) -> Path:
        from ..tools.drive import GoogleDriveTool

        drive = GoogleDriveTool()
        if not drive.is_available():
            raise DriveError("Google Drive not configured. Run 'yt-agent auth drive' first.")
        return await drive.download_video(url)
