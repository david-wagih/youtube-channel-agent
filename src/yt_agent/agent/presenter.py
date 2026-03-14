"""Console presentation layer for publish and enhance workflows.

All rich console output related to displaying plans and comparisons lives
here. The orchestrator calls these functions; the data models know nothing
about display.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..utils.scheduler import format_publish_time
from .models import EnhancePlan, PublishPlan, VideoEnhancement

console = Console()


# ---------------------------------------------------------------------------
# Publish plan
# ---------------------------------------------------------------------------


def display_publish_plan(plan: PublishPlan) -> None:
    """Render a full publish plan to the console."""
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]{plan.metadata.title}[/bold cyan]",
            title="Title",
        )
    )
    console.print(Panel(plan.metadata.description, title="Description", expand=False))

    if plan.metadata.chapters:
        chapters_text = "\n".join(
            f"  {ch.time} - {ch.title}" for ch in plan.metadata.chapters
        )
        console.print(
            Panel(chapters_text, title=f"Chapters ({len(plan.metadata.chapters)})", style="cyan")
        )

    tags_table = Table(show_header=False, box=None)
    tags_table.add_column("Tags", style="green")
    tags_table.add_row(", ".join(plan.metadata.tags[:10]))
    if len(plan.metadata.tags) > 10:
        tags_table.add_row(f"... and {len(plan.metadata.tags) - 10} more")
    console.print(Panel(tags_table, title="Tags"))

    if plan.thumbnail_path:
        console.print(Panel(f"[green]{plan.thumbnail_path}[/green]", title="Thumbnail"))

    console.print(
        Panel(
            f"[bold yellow]{format_publish_time(plan.publish_time)}[/bold yellow]",
            title="Scheduled For",
        )
    )


# ---------------------------------------------------------------------------
# Enhancement comparison
# ---------------------------------------------------------------------------


def _format_changes_summary(changes: str | list[str]) -> str:
    if isinstance(changes, list):
        return "\n".join(f"• {item}" for item in changes)
    return changes


def display_enhancement_comparison(enhancement: VideoEnhancement) -> None:
    """Render a before/after comparison for a single video enhancement."""
    console.print(
        Panel(
            f"[dim]Original:[/dim] {enhancement.original_title}\n"
            f"[bold cyan]Enhanced:[/bold cyan] {enhancement.enhanced_metadata.title}",
            title="Title Comparison",
        )
    )

    orig_preview = (
        enhancement.original_description[:200] + "..."
        if len(enhancement.original_description) > 200
        else enhancement.original_description
    )
    new_preview = (
        enhancement.enhanced_metadata.description[:200] + "..."
        if len(enhancement.enhanced_metadata.description) > 200
        else enhancement.enhanced_metadata.description
    )
    console.print(
        Panel(
            f"[dim]Original:[/dim]\n{orig_preview}\n\n"
            f"[bold cyan]Enhanced:[/bold cyan]\n{new_preview}",
            title="Description Preview",
        )
    )

    orig_tags = ", ".join(enhancement.original_tags[:8]) if enhancement.original_tags else "None"
    new_tags = ", ".join(enhancement.enhanced_metadata.tags[:8])
    extra = len(enhancement.enhanced_metadata.tags) - 8
    if extra > 0:
        new_tags += f" ... (+{extra} more)"

    console.print(
        Panel(
            f"[dim]Original ({len(enhancement.original_tags)}):[/dim] {orig_tags}\n"
            f"[bold cyan]Enhanced ({len(enhancement.enhanced_metadata.tags)}):[/bold cyan]"
            f" {new_tags}",
            title="Tags Comparison",
        )
    )

    console.print(
        Panel(
            _format_changes_summary(enhancement.changes_summary),
            title="Changes Made",
            style="green",
        )
    )


# ---------------------------------------------------------------------------
# Enhance plan summary table
# ---------------------------------------------------------------------------


def display_enhance_plan_summary(plan: EnhancePlan) -> None:
    """Render a summary table for all enhancements in a plan."""
    table = Table(title=f"Enhancement Plan ({len(plan.enhancements)} videos)")
    table.add_column("#", style="dim", width=4)
    table.add_column("Original Title", style="white")
    table.add_column("Enhanced Title", style="cyan")
    table.add_column("Views", justify="right")

    for i, e in enumerate(plan.enhancements, 1):
        orig = e.original_title[:40] + "..." if len(e.original_title) > 40 else e.original_title
        new = (
            e.enhanced_metadata.title[:40] + "..."
            if len(e.enhanced_metadata.title) > 40
            else e.enhanced_metadata.title
        )
        table.add_row(str(i), orig, new, f"{e.view_count:,}")

    console.print(table)
