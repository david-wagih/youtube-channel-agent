"""Pure data models for the publish and enhance workflows.

No display logic lives here — see presenter.py for all console output.
"""

from dataclasses import dataclass, field
from datetime import datetime

from ..seo.optimizer import VideoMetadata


@dataclass
class PublishPlan:
    """Plan for publishing a single video."""

    video_source: str
    metadata: VideoMetadata
    publish_time: datetime
    is_transcribed: bool = False
    playlist_id: str | None = None
    thumbnail_path: str | None = None


@dataclass
class VideoEnhancement:
    """Enhancement proposal for a single existing video."""

    video_id: str
    original_title: str
    original_description: str
    original_tags: list[str]
    view_count: int
    enhanced_metadata: VideoMetadata
    changes_summary: str | list[str]


@dataclass
class EnhancePlan:
    """Collection of enhancement proposals for multiple videos."""

    enhancements: list[VideoEnhancement] = field(default_factory=list)
