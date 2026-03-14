"""YouTube channel information and video listing."""

from typing import Any

from ._models import VideoDetails
from ._video import _parse_video_response

_VIDEO_PARTS = "snippet,statistics"


class YouTubeChannelManager:
    """Handles channel information retrieval and channel video listing."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def get_channel_info(self) -> dict[str, Any]:
        """Return basic info about the authenticated channel."""
        response = self._service.channels().list(part="snippet,statistics", mine=True).execute()
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

    def list_channel_videos(self, max_results: int = 50) -> list[VideoDetails]:
        """Return recent videos from the authenticated channel (newest first)."""
        channel_response = self._service.channels().list(part="contentDetails", mine=True).execute()
        if not channel_response.get("items"):
            return []

        uploads_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        videos: list[VideoDetails] = []
        page_token = None

        while len(videos) < max_results:
            response = (
                self._service.playlistItems()
                .list(
                    part="snippet",
                    playlistId=uploads_id,
                    maxResults=min(50, max_results - len(videos)),
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

        return videos[:max_results]
