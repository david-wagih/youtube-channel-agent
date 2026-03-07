"""FastAPI web application for YouTube Agent."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..agent import YouTubeAgent
from ..llm.factory import create_llm
from ..tools.youtube import VideoDetails, YouTubeTool


class EnhanceRequest(BaseModel):
    """Request to enhance video(s)."""

    video_id: str | None = None
    playlist_id: str | None = None
    recent_count: int | None = None


class VideoInfo(BaseModel):
    """Video information for API response."""

    video_id: str
    title: str
    description: str
    tags: list[str]
    view_count: int
    thumbnail_url: str | None


class EnhancementResult(BaseModel):
    """Enhancement result for a single video."""

    video_id: str
    original_title: str
    original_description: str
    original_tags: list[str]
    view_count: int
    enhanced_title: str
    enhanced_description: str
    enhanced_tags: list[str]
    enhanced_hashtags: list[str]
    changes_summary: str | list[str]


class ApplyRequest(BaseModel):
    """Request to apply enhancement."""

    video_id: str
    title: str
    description: str
    tags: list[str]


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="YouTube Agent",
        description="AI-powered YouTube SEO enhancement",
        version="0.1.0",
    )

    templates_dir = Path(__file__).parent / "templates"

    @app.get("/", response_class=HTMLResponse)
    async def index():
        """Serve the main UI."""
        html_file = templates_dir / "index.html"
        return html_file.read_text(encoding="utf-8")

    @app.get("/api/videos", response_model=list[VideoInfo])
    async def list_videos(
        video_id: str | None = None,
        playlist_id: str | None = None,
        recent: int | None = None,
    ):
        """List videos to enhance."""
        youtube = YouTubeTool()

        if not youtube.is_available():
            raise HTTPException(
                status_code=400, detail="YouTube not configured. Run 'yt-agent auth youtube' first."
            )

        videos: list[VideoDetails] = []

        try:
            if video_id:
                video = await youtube.get_video_details(video_id)
                videos = [video]
            elif playlist_id:
                videos = await youtube.list_playlist_videos(playlist_id)
            elif recent:
                videos = await youtube.list_channel_videos(max_results=recent)
            else:
                # Default: get recent 10 videos
                videos = await youtube.list_channel_videos(max_results=10)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        return [
            VideoInfo(
                video_id=v.video_id,
                title=v.title,
                description=v.description,
                tags=v.tags,
                view_count=v.view_count,
                thumbnail_url=v.thumbnail_url,
            )
            for v in videos
        ]

    @app.post("/api/enhance", response_model=EnhancementResult)
    async def enhance_video(video_id: str):
        """Generate enhancement for a video."""
        youtube = YouTubeTool()

        if not youtube.is_available():
            raise HTTPException(status_code=400, detail="YouTube not configured")

        try:
            # Get video details
            video = await youtube.get_video_details(video_id)

            # Create agent and generate enhancement
            llm = create_llm()
            agent = YouTubeAgent(llm=llm)

            enhanced_metadata, changes_summary = await agent.seo_optimizer.enhance(
                current_title=video.title,
                current_description=video.description,
                current_tags=video.tags,
                view_count=video.view_count,
            )

            return EnhancementResult(
                video_id=video.video_id,
                original_title=video.title,
                original_description=video.description,
                original_tags=video.tags,
                view_count=video.view_count,
                enhanced_title=enhanced_metadata.title,
                enhanced_description=enhanced_metadata.description,
                enhanced_tags=enhanced_metadata.tags,
                enhanced_hashtags=enhanced_metadata.hashtags,
                changes_summary=changes_summary,
            )

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/apply")
    async def apply_enhancement(request: ApplyRequest):
        """Apply enhancement to a video."""
        youtube = YouTubeTool()

        if not youtube.is_available():
            raise HTTPException(status_code=400, detail="YouTube not configured")

        try:
            await youtube.update_metadata(
                video_id=request.video_id,
                title=request.title,
                description=request.description,
                tags=request.tags,
            )
            return {"success": True, "message": "Enhancement applied successfully"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/channel")
    async def get_channel_info():
        """Get channel information."""
        youtube = YouTubeTool()

        if not youtube.is_available():
            raise HTTPException(status_code=400, detail="YouTube not configured")

        try:
            info = await youtube.get_channel_info()
            return info
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return app
