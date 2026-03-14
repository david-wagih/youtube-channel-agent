"""Data models for YouTube API responses."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class VideoDetails:
    """Details of an existing YouTube video."""

    video_id: str
    title: str
    description: str
    tags: list[str]
    published_at: datetime | None
    view_count: int
    like_count: int
    thumbnail_url: str | None

    @property
    def url(self) -> str:
        return f"https://youtube.com/watch?v={self.video_id}"

    @property
    def studio_url(self) -> str:
        return f"https://studio.youtube.com/video/{self.video_id}/edit"


@dataclass
class VideoUploadResult:
    """Result of a video upload operation."""

    video_id: str
    title: str
    publish_at: datetime | None
    url: str

    @property
    def studio_url(self) -> str:
        return f"https://studio.youtube.com/video/{self.video_id}/edit"
