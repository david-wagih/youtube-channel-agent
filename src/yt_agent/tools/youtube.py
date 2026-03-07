"""YouTube API integration tool."""

import os
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from rich.console import Console

from ..config import get_credentials_dir
from .base import BaseTool, ToolResult


console = Console()

# YouTube API scopes
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

# Privacy status options
PRIVACY_PUBLIC = "public"
PRIVACY_PRIVATE = "private"
PRIVACY_UNLISTED = "unlisted"


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
        """URL to watch the video."""
        return f"https://youtube.com/watch?v={self.video_id}"

    @property
    def studio_url(self) -> str:
        """URL to YouTube Studio for this video."""
        return f"https://studio.youtube.com/video/{self.video_id}/edit"


@dataclass
class VideoUploadResult:
    """Result of a video upload."""

    video_id: str
    title: str
    publish_at: datetime | None
    url: str

    @property
    def studio_url(self) -> str:
        """URL to YouTube Studio for this video."""
        return f"https://studio.youtube.com/video/{self.video_id}/edit"


class YouTubeTool(BaseTool):
    """Tool for interacting with YouTube API."""

    def __init__(self):
        self._service = None
        self._credentials = None

    @property
    def name(self) -> str:
        return "youtube"

    @property
    def description(self) -> str:
        return "Upload videos, set metadata, and schedule publishing on YouTube"

    def is_available(self) -> bool:
        """Check if YouTube credentials are configured."""
        creds_dir = get_credentials_dir()
        client_secrets = creds_dir / "client_secrets.json"
        return client_secrets.exists()

    def _get_credentials_path(self) -> Path:
        """Get path to stored OAuth token."""
        return get_credentials_dir() / "youtube_token.json"

    def _get_client_secrets_path(self) -> Path:
        """Get path to client secrets file."""
        return get_credentials_dir() / "client_secrets.json"

    def _load_credentials(self) -> Credentials | None:
        """Load credentials from stored token file."""
        token_path = self._get_credentials_path()

        if not token_path.exists():
            return None

        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._save_credentials(creds)

        return creds

    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to token file."""
        token_path = self._get_credentials_path()
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    def authenticate(self) -> bool:
        """Run OAuth flow to authenticate with YouTube.

        Returns:
            True if authentication successful.
        """
        client_secrets = self._get_client_secrets_path()

        if not client_secrets.exists():
            console.print(
                "[bold red]Error:[/bold red] client_secrets.json not found.\n"
                f"Please download it from Google Cloud Console and save to:\n"
                f"  {client_secrets}"
            )
            return False

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets),
                SCOPES,
            )

            console.print("[bold]Opening browser for YouTube authentication...[/bold]")
            creds = flow.run_local_server(port=8080)

            self._save_credentials(creds)
            self._credentials = creds
            console.print("[bold green]Authentication successful![/bold green]")
            return True

        except Exception as e:
            console.print(f"[bold red]Authentication failed:[/bold red] {e}")
            return False

    def _get_service(self):
        """Get authenticated YouTube API service."""
        if self._service:
            return self._service

        # Try to load existing credentials
        creds = self._load_credentials()

        if not creds or not creds.valid:
            # Need to authenticate
            if not self.authenticate():
                raise RuntimeError("YouTube authentication required")
            creds = self._credentials

        self._service = build("youtube", "v3", credentials=creds)
        return self._service

    async def execute(self, **kwargs) -> ToolResult:
        """Execute a YouTube operation.

        Supported operations:
        - upload: Upload a video
        - update_metadata: Update video metadata
        """
        operation = kwargs.get("operation")

        if operation == "upload":
            return await self._upload_video(**kwargs)
        elif operation == "update_metadata":
            return await self._update_metadata(**kwargs)
        else:
            return ToolResult(
                success=False,
                error=f"Unknown operation: {operation}",
            )

    async def upload_video(
        self,
        video_path: str | Path,
        title: str,
        description: str,
        tags: list[str],
        publish_at: datetime | None = None,
        thumbnail_path: str | Path | None = None,
        playlist_id: str | None = None,
        category_id: str = "28",  # 28 = Science & Technology
        notify_subscribers: bool = True,
    ) -> VideoUploadResult:
        """Upload a video to YouTube.

        Args:
            video_path: Path to the video file.
            title: Video title.
            description: Video description.
            tags: List of tags.
            publish_at: When to publish (None = immediately as private).
            thumbnail_path: Optional path to thumbnail image.
            playlist_id: Optional playlist ID to add the video to.
            category_id: YouTube category ID (default: Science & Technology).
            notify_subscribers: Whether to notify subscribers.

        Returns:
            VideoUploadResult with video details.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        service = self._get_service()

        # Determine privacy status and scheduling
        if publish_at:
            # Schedule for future - must be private until then
            privacy_status = PRIVACY_PRIVATE
            publish_at_str = publish_at.isoformat()
        else:
            # No scheduling - upload as private (user can publish manually)
            privacy_status = PRIVACY_PRIVATE
            publish_at_str = None

        # Build request body
        body = {
            "snippet": {
                "title": title[:100],  # YouTube limit
                "description": description[:5000],  # YouTube limit
                "tags": tags[:500],  # YouTube limit
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        # Add publish time if scheduling
        if publish_at_str:
            body["status"]["publishAt"] = publish_at_str

        # Create media upload
        media = MediaFileUpload(
            str(video_path),
            mimetype="video/*",
            resumable=True,
            chunksize=256 * 1024,  # 256KB chunks
        )

        # Execute upload
        console.print(f"[bold]Uploading:[/bold] {video_path.name}")

        request = service.videos().insert(
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

        console.print(f"  Upload progress: 100%")

        video_id = response["id"]

        # Upload thumbnail if provided
        if thumbnail_path:
            await self.set_thumbnail(video_id, thumbnail_path)

        # Add to playlist if provided
        if playlist_id:
            await self.add_to_playlist(video_id, playlist_id)

        return VideoUploadResult(
            video_id=video_id,
            title=title,
            publish_at=publish_at,
            url=f"https://youtube.com/watch?v={video_id}",
        )

    async def set_thumbnail(
        self,
        video_id: str,
        thumbnail_path: str | Path,
    ) -> bool:
        """Set a custom thumbnail for a video.

        Args:
            video_id: YouTube video ID.
            thumbnail_path: Path to thumbnail image.

        Returns:
            True if successful.
        """
        thumbnail_path = Path(thumbnail_path)
        if not thumbnail_path.exists():
            console.print(f"[yellow]Warning:[/yellow] Thumbnail not found: {thumbnail_path}")
            return False

        service = self._get_service()

        media = MediaFileUpload(
            str(thumbnail_path),
            mimetype="image/jpeg",
        )

        try:
            service.thumbnails().set(
                videoId=video_id,
                media_body=media,
            ).execute()
            console.print("[green]Thumbnail uploaded.[/green]")
            return True
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not set thumbnail: {e}")
            return False

    async def update_metadata(
        self,
        video_id: str,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        """Update metadata for an existing video.

        Args:
            video_id: YouTube video ID.
            title: New title (optional).
            description: New description (optional).
            tags: New tags (optional).

        Returns:
            True if successful.
        """
        service = self._get_service()

        # Get current video details
        video = service.videos().list(
            part="snippet",
            id=video_id,
        ).execute()

        if not video.get("items"):
            raise ValueError(f"Video not found: {video_id}")

        snippet = video["items"][0]["snippet"]

        # Update only provided fields
        if title:
            snippet["title"] = title[:100]
        if description:
            snippet["description"] = description[:5000]
        if tags:
            # Enforce YouTube's 500 total character limit across all tags
            limited_tags = []
            total_chars = 0
            for tag in tags:
                if total_chars + len(tag) + 1 > 500:
                    break
                limited_tags.append(tag)
                total_chars += len(tag) + 1
            snippet["tags"] = limited_tags

        # Update video
        response = service.videos().update(
            part="snippet",
            body={
                "id": video_id,
                "snippet": snippet,
            },
        ).execute()

        console.print(f"[dim]Updated: {response.get('snippet', {}).get('title', video_id)}[/dim]")
        return True

    async def get_channel_info(self) -> dict:
        """Get information about the authenticated channel.

        Returns:
            Dictionary with channel info.
        """
        service = self._get_service()

        response = service.channels().list(
            part="snippet,statistics",
            mine=True,
        ).execute()

        if not response.get("items"):
            return {}

        channel = response["items"][0]
        return {
            "id": channel["id"],
            "title": channel["snippet"]["title"],
            "description": channel["snippet"].get("description", ""),
            "subscriber_count": channel["statistics"].get("subscriberCount", "0"),
            "video_count": channel["statistics"].get("videoCount", "0"),
        }

    async def _upload_video(self, **kwargs) -> ToolResult:
        """Internal upload wrapper for execute()."""
        try:
            result = await self.upload_video(
                video_path=kwargs["video_path"],
                title=kwargs["title"],
                description=kwargs["description"],
                tags=kwargs.get("tags", []),
                publish_at=kwargs.get("publish_at"),
                thumbnail_path=kwargs.get("thumbnail_path"),
            )
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _update_metadata(self, **kwargs) -> ToolResult:
        """Internal update wrapper for execute()."""
        try:
            success = await self.update_metadata(
                video_id=kwargs["video_id"],
                title=kwargs.get("title"),
                description=kwargs.get("description"),
                tags=kwargs.get("tags"),
            )
            return ToolResult(success=success)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _parse_video_response(self, item: dict) -> VideoDetails:
        """Parse a video API response into VideoDetails."""
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})

        # Parse published date
        published_at = None
        if snippet.get("publishedAt"):
            try:
                published_at = datetime.fromisoformat(
                    snippet["publishedAt"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # Get best thumbnail
        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = None
        for quality in ["maxres", "high", "medium", "default"]:
            if quality in thumbnails:
                thumbnail_url = thumbnails[quality].get("url")
                break

        return VideoDetails(
            video_id=item["id"] if isinstance(item["id"], str) else item["id"].get("videoId", ""),
            title=snippet.get("title", ""),
            description=snippet.get("description", ""),
            tags=snippet.get("tags", []),
            published_at=published_at,
            view_count=int(statistics.get("viewCount", 0)),
            like_count=int(statistics.get("likeCount", 0)),
            thumbnail_url=thumbnail_url,
        )

    async def get_video_details(self, video_id: str) -> VideoDetails:
        """Fetch details for a single video.

        Args:
            video_id: YouTube video ID.

        Returns:
            VideoDetails with metadata and statistics.
        """
        service = self._get_service()

        response = service.videos().list(
            part="snippet,statistics",
            id=video_id,
        ).execute()

        if not response.get("items"):
            raise ValueError(f"Video not found: {video_id}")

        return self._parse_video_response(response["items"][0])

    async def list_playlist_videos(self, playlist_id: str) -> list[VideoDetails]:
        """List all videos in a playlist.

        Args:
            playlist_id: YouTube playlist ID.

        Returns:
            List of VideoDetails for each video in the playlist.
        """
        service = self._get_service()
        videos = []
        page_token = None

        while True:
            response = service.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=page_token,
            ).execute()

            # Get video IDs from playlist items
            video_ids = [
                item["snippet"]["resourceId"]["videoId"]
                for item in response.get("items", [])
            ]

            if video_ids:
                # Fetch full video details including statistics
                videos_response = service.videos().list(
                    part="snippet,statistics",
                    id=",".join(video_ids),
                ).execute()

                for item in videos_response.get("items", []):
                    videos.append(self._parse_video_response(item))

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return videos

    async def list_channel_videos(self, max_results: int = 50) -> list[VideoDetails]:
        """List recent videos from the authenticated channel.

        Args:
            max_results: Maximum number of videos to return.

        Returns:
            List of VideoDetails sorted by publish date (newest first).
        """
        service = self._get_service()

        # Get the uploads playlist for the channel
        channel_response = service.channels().list(
            part="contentDetails",
            mine=True,
        ).execute()

        if not channel_response.get("items"):
            return []

        uploads_playlist_id = (
            channel_response["items"][0]["contentDetails"]
            ["relatedPlaylists"]["uploads"]
        )

        # Get videos from uploads playlist
        videos = []
        page_token = None

        while len(videos) < max_results:
            response = service.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=min(50, max_results - len(videos)),
                pageToken=page_token,
            ).execute()

            video_ids = [
                item["snippet"]["resourceId"]["videoId"]
                for item in response.get("items", [])
            ]

            if video_ids:
                videos_response = service.videos().list(
                    part="snippet,statistics",
                    id=",".join(video_ids),
                ).execute()

                for item in videos_response.get("items", []):
                    videos.append(self._parse_video_response(item))

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return videos[:max_results]

    async def list_playlists(self) -> list[dict]:
        """List all playlists for the authenticated channel.

        Returns:
            List of dicts with 'id', 'title', 'video_count'.
        """
        service = self._get_service()
        playlists = []
        page_token = None

        while True:
            response = service.playlists().list(
                part="snippet,contentDetails",
                mine=True,
                maxResults=50,
                pageToken=page_token,
            ).execute()

            for item in response.get("items", []):
                playlists.append({
                    "id": item["id"],
                    "title": item["snippet"]["title"],
                    "description": item["snippet"].get("description", ""),
                    "video_count": item["contentDetails"].get("itemCount", 0),
                })

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return playlists

    async def add_to_playlist(self, video_id: str, playlist_id: str) -> bool:
        """Add a video to a playlist.

        Args:
            video_id: YouTube video ID.
            playlist_id: YouTube playlist ID.

        Returns:
            True if successful.
        """
        service = self._get_service()

        try:
            service.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id,
                        },
                    },
                },
            ).execute()

            console.print(f"[green]Added to playlist.[/green]")
            return True

        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not add to playlist: {e}")
            return False
