"""YouTube tool — public interface.

All external code imports from here:
    from yt_agent.tools.youtube import YouTubeTool, VideoDetails, VideoUploadResult
"""

from datetime import datetime
from pathlib import Path

from googleapiclient.discovery import build
from rich.console import Console

from ...auth import OAuthManager
from ...config import get_credentials_dir
from ...exceptions import AuthError
from ..base import BaseTool, ToolResult
from ._channel import YouTubeChannelManager
from ._models import VideoDetails, VideoUploadResult
from ._playlist import YouTubePlaylistManager
from ._video import YouTubeVideoManager

console = Console()

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

__all__ = ["YouTubeTool", "VideoDetails", "VideoUploadResult"]


class YouTubeTool(BaseTool):
    """Facade that composes focused YouTube sub-managers into a single API."""

    def __init__(self) -> None:
        self._service = None
        self._oauth = OAuthManager(
            service_name="YouTube",
            scopes=SCOPES,
            token_filename="youtube_token.json",
            port=8080,
        )

    # ------------------------------------------------------------------
    # BaseTool interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "youtube"

    @property
    def description(self) -> str:
        return "Upload videos, set metadata, and schedule publishing on YouTube"

    def is_available(self) -> bool:
        return (get_credentials_dir() / "client_secrets.json").exists()

    def execute(self, **kwargs) -> ToolResult:
        operation = kwargs.get("operation")
        if operation == "upload":
            return self._upload_video(**kwargs)
        if operation == "update_metadata":
            return self._update_metadata(**kwargs)
        return ToolResult(success=False, error=f"Unknown operation: {operation}")

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def authenticate(self) -> bool:
        """Run the OAuth browser flow. Returns True on success."""
        try:
            self._oauth.authenticate()
            return True
        except AuthError as e:
            console.print(f"[bold red]Authentication failed:[/bold red] {e}")
            return False

    def _get_service(self):
        if self._service:
            return self._service
        creds = self._oauth.get_valid_credentials()
        self._service = build("youtube", "v3", credentials=creds)
        return self._service

    # ------------------------------------------------------------------
    # Video operations (delegated to YouTubeVideoManager)
    # ------------------------------------------------------------------

    def upload_video(
        self,
        video_path: str | Path,
        title: str,
        description: str,
        tags: list[str],
        publish_at: datetime | None = None,
        thumbnail_path: str | Path | None = None,
        playlist_id: str | None = None,
        category_id: str = "28",
        notify_subscribers: bool = True,
    ) -> VideoUploadResult:
        mgr = YouTubeVideoManager(self._get_service())
        result = mgr.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            publish_at=publish_at,
            category_id=category_id,
            notify_subscribers=notify_subscribers,
        )
        if thumbnail_path:
            mgr.set_thumbnail(result.video_id, thumbnail_path)
        if playlist_id:
            YouTubePlaylistManager(self._get_service()).add_to_playlist(
                result.video_id, playlist_id
            )
        return result

    def set_thumbnail(self, video_id: str, thumbnail_path: str | Path) -> bool:
        return YouTubeVideoManager(self._get_service()).set_thumbnail(
            video_id, thumbnail_path
        )

    def update_metadata(
        self,
        video_id: str,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        return YouTubeVideoManager(self._get_service()).update_metadata(
            video_id=video_id, title=title, description=description, tags=tags
        )

    def get_video_details(self, video_id: str) -> VideoDetails:
        return YouTubeVideoManager(self._get_service()).get_video_details(video_id)

    # ------------------------------------------------------------------
    # Playlist operations (delegated to YouTubePlaylistManager)
    # ------------------------------------------------------------------

    def list_playlists(self) -> list[dict]:
        return YouTubePlaylistManager(self._get_service()).list_playlists()

    def list_playlist_videos(self, playlist_id: str) -> list[VideoDetails]:
        return YouTubePlaylistManager(self._get_service()).list_playlist_videos(
            playlist_id
        )

    def add_to_playlist(self, video_id: str, playlist_id: str) -> bool:
        return YouTubePlaylistManager(self._get_service()).add_to_playlist(
            video_id, playlist_id
        )

    # ------------------------------------------------------------------
    # Channel operations (delegated to YouTubeChannelManager)
    # ------------------------------------------------------------------

    def get_channel_info(self) -> dict:
        return YouTubeChannelManager(self._get_service()).get_channel_info()

    def list_channel_videos(self, max_results: int = 50) -> list[VideoDetails]:
        return YouTubeChannelManager(self._get_service()).list_channel_videos(
            max_results
        )

    # ------------------------------------------------------------------
    # Internal execute() wrappers
    # ------------------------------------------------------------------

    def _upload_video(self, **kwargs) -> ToolResult:
        try:
            result = self.upload_video(
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

    def _update_metadata(self, **kwargs) -> ToolResult:
        try:
            success = self.update_metadata(
                video_id=kwargs["video_id"],
                title=kwargs.get("title"),
                description=kwargs.get("description"),
                tags=kwargs.get("tags"),
            )
            return ToolResult(success=success)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
