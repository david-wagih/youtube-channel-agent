"""YouTube video operations: upload, thumbnail, metadata, details."""

from datetime import datetime
from pathlib import Path
from typing import Any

from googleapiclient.http import MediaFileUpload
from rich.console import Console

from ._models import VideoDetails, VideoUploadResult

console = Console()

_VIDEO_PARTS = "snippet,statistics"
_PRIVACY_PRIVATE = "private"


def _parse_video_response(item: dict[str, Any]) -> VideoDetails:
    """Parse a raw YouTube API video item into a VideoDetails dataclass."""
    snippet = item.get("snippet", {})
    statistics = item.get("statistics", {})

    published_at = None
    if snippet.get("publishedAt"):
        try:
            published_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    thumbnails = snippet.get("thumbnails", {})
    thumbnail_url = None
    for quality in ["maxres", "high", "medium", "default"]:
        if quality in thumbnails:
            thumbnail_url = thumbnails[quality].get("url")
            break

    raw_id = item["id"]
    video_id = raw_id if isinstance(raw_id, str) else raw_id.get("videoId", "")

    return VideoDetails(
        video_id=video_id,
        title=snippet.get("title", ""),
        description=snippet.get("description", ""),
        tags=snippet.get("tags", []),
        published_at=published_at,
        view_count=int(statistics.get("viewCount", 0)),
        like_count=int(statistics.get("likeCount", 0)),
        thumbnail_url=thumbnail_url,
    )


class YouTubeVideoManager:
    """Handles video upload, thumbnail, metadata update, and detail retrieval."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def upload_video(
        self,
        video_path: str | Path,
        title: str,
        description: str,
        tags: list[str],
        publish_at: datetime | None = None,
        category_id: str = "28",
        notify_subscribers: bool = True,
    ) -> VideoUploadResult:
        """Upload a video to YouTube and return upload details."""
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        publish_at_str = publish_at.isoformat() if publish_at else None

        body: dict[str, Any] = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:500],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": _PRIVACY_PRIVATE,
                "selfDeclaredMadeForKids": False,
            },
        }

        if publish_at_str:
            body["status"]["publishAt"] = publish_at_str

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/*",
            resumable=True,
            chunksize=256 * 1024,
        )

        console.print(f"[bold]Uploading:[/bold] {video_path.name}")
        request = self._service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
            notifySubscribers=notify_subscribers,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                console.print(f"  Upload progress: {progress}%", end="\r")

        console.print("  Upload progress: 100%")
        return VideoUploadResult(
            video_id=response["id"],
            title=title,
            publish_at=publish_at,
            url=f"https://youtube.com/watch?v={response['id']}",
        )

    def set_thumbnail(self, video_id: str, thumbnail_path: str | Path) -> bool:
        """Set a custom thumbnail for a video. Returns True on success."""
        thumbnail_path = Path(thumbnail_path)
        if not thumbnail_path.exists():
            console.print(f"[yellow]Warning:[/yellow] Thumbnail not found: {thumbnail_path}")
            return False

        media = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")
        try:
            self._service.thumbnails().set(videoId=video_id, media_body=media).execute()
            console.print("[green]Thumbnail uploaded.[/green]")
            return True
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not set thumbnail: {e}")
            return False

    def update_metadata(
        self,
        video_id: str,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        """Update snippet fields for an existing video. Returns True on success."""
        video = self._service.videos().list(part="snippet", id=video_id).execute()

        if not video.get("items"):
            raise ValueError(f"Video not found: {video_id}")

        snippet = video["items"][0]["snippet"]

        if title:
            snippet["title"] = title[:100]
        if description:
            snippet["description"] = description[:5000]
        if tags is not None:
            limited_tags: list[str] = []
            total_chars = 0
            dropped = 0
            for tag in tags:
                if total_chars + len(tag) + 1 > 500:
                    dropped += 1
                    continue
                limited_tags.append(tag)
                total_chars += len(tag) + 1
            if dropped:
                console.print(
                    f"[yellow]Warning:[/yellow] {dropped} tag(s) dropped — "
                    "total tag length exceeds YouTube's 500-character limit."
                )
            snippet["tags"] = limited_tags

        response = (
            self._service.videos()
            .update(part="snippet", body={"id": video_id, "snippet": snippet})
            .execute()
        )
        console.print(f"[dim]Updated: {response.get('snippet', {}).get('title', video_id)}[/dim]")
        return True

    def get_video_details(self, video_id: str) -> VideoDetails:
        """Fetch full details for a single video by ID."""
        response = self._service.videos().list(part=_VIDEO_PARTS, id=video_id).execute()
        if not response.get("items"):
            raise ValueError(f"Video not found: {video_id}")
        return _parse_video_response(response["items"][0])
