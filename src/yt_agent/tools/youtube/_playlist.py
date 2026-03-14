"""YouTube playlist operations."""

from typing import Any

from rich.console import Console

from ._models import VideoDetails
from ._video import _parse_video_response

console = Console()

_VIDEO_PARTS = "snippet,statistics"


class YouTubePlaylistManager:
    """Handles playlist listing, video listing, and adding videos to playlists."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def list_playlists(self) -> list[dict[str, Any]]:
        """Return all playlists for the authenticated channel."""
        playlists: list[dict[str, Any]] = []
        page_token = None

        while True:
            response = (
                self._service.playlists()
                .list(
                    part="snippet,contentDetails",
                    mine=True,
                    maxResults=50,
                    pageToken=page_token,
                )
                .execute()
            )
            for item in response.get("items", []):
                playlists.append(
                    {
                        "id": item["id"],
                        "title": item["snippet"]["title"],
                        "description": item["snippet"].get("description", ""),
                        "video_count": item["contentDetails"].get("itemCount", 0),
                    }
                )
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return playlists

    def list_playlist_videos(self, playlist_id: str) -> list[VideoDetails]:
        """Return all videos in a playlist with full snippet and statistics."""
        videos: list[VideoDetails] = []
        page_token = None

        while True:
            response = (
                self._service.playlistItems()
                .list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=page_token,
                )
                .execute()
            )
            video_ids = [
                item["snippet"]["resourceId"]["videoId"] for item in response.get("items", [])
            ]
            if video_ids:
                videos_response = (
                    self._service.videos().list(part=_VIDEO_PARTS, id=",".join(video_ids)).execute()
                )
                for item in videos_response.get("items", []):
                    videos.append(_parse_video_response(item))

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return videos

    def add_to_playlist(self, video_id: str, playlist_id: str) -> bool:
        """Add a video to a playlist. Returns True on success."""
        try:
            self._service.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id},
                    }
                },
            ).execute()
            console.print("[green]Added to playlist.[/green]")
            return True
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not add to playlist: {e}")
            return False
