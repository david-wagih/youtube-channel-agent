"""SEO optimization for YouTube videos."""

from dataclasses import dataclass, field

from ..config import ChannelProfile
from ..llm.base import BaseLLM
from ..utils.prompts import (
    CHAPTER_GENERATION_PROMPT,
    SEO_ENHANCEMENT_PROMPT,
    SEO_OPTIMIZATION_PROMPT,
    SEO_SYSTEM_PROMPT,
)


@dataclass
class Chapter:
    """A video chapter/timestamp."""

    time: str  # Format: "MM:SS" or "HH:MM:SS"
    title: str

    def __str__(self) -> str:
        return f"{self.time} {self.title}"


@dataclass
class VideoMetadata:
    """Optimized video metadata."""

    title: str
    description: str
    tags: list[str]
    hashtags: list[str] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)

    def format_chapters(self) -> str:
        """Format chapters for YouTube description."""
        if not self.chapters:
            return ""
        return "\n".join(str(ch) for ch in self.chapters)

    def __str__(self) -> str:
        chapters_str = f"\nChapters:\n{self.format_chapters()}\n" if self.chapters else ""
        return f"""Title: {self.title}

Description:
{self.description}
{chapters_str}
Tags: {", ".join(self.tags)}

Hashtags: {" ".join(self.hashtags)}"""


class SEOOptimizer:
    """Optimize video metadata for YouTube SEO."""

    def __init__(self, llm: BaseLLM, profile: ChannelProfile | None = None):
        self.llm = llm
        self.profile = profile or ChannelProfile()

    async def optimize(
        self,
        topic: str,
        transcript: str | None = None,
        additional_context: str | None = None,
    ) -> VideoMetadata:
        """Generate SEO-optimized metadata for a video.

        Args:
            topic: Brief description of the video topic.
            transcript: Optional video transcript for deeper analysis.
            additional_context: Any additional context about the video.

        Returns:
            VideoMetadata with optimized title, description, tags.
        """
        # Build the prompt
        prompt = SEO_OPTIMIZATION_PROMPT.format(
            topic=topic,
            transcript=transcript or "Not provided",
            additional_context=additional_context or "None",
            channel_name=self.profile.channel_name or "Unknown",
            social_links=self._format_social_links(),
            business_email=self.profile.business_email or "",
            default_hashtags=" ".join(self.profile.default_hashtags),
        )

        # Get LLM response
        response = await self.llm.generate_json(
            prompt=prompt,
            system=SEO_SYSTEM_PROMPT,
            temperature=0.7,
        )

        return VideoMetadata(
            title=response["title"],
            description=response["description"],
            tags=response["tags"],
            hashtags=response.get("hashtags", self.profile.default_hashtags),
        )

    async def enhance(
        self,
        current_title: str,
        current_description: str,
        current_tags: list[str],
        view_count: int = 0,
        additional_context: str | None = None,
    ) -> tuple[VideoMetadata, str]:
        """Enhance existing video metadata for better SEO.

        Args:
            current_title: Current video title.
            current_description: Current video description.
            current_tags: Current video tags.
            view_count: Current view count (for context).
            additional_context: Any additional context about the video.

        Returns:
            Tuple of (enhanced VideoMetadata, changes summary).
        """
        # Build the prompt
        prompt = SEO_ENHANCEMENT_PROMPT.format(
            current_title=current_title,
            current_description=current_description,
            current_tags=", ".join(current_tags) if current_tags else "None",
            view_count=view_count,
            additional_context=additional_context or "None",
            channel_name=self.profile.channel_name or "Unknown",
            social_links=self._format_social_links(),
            business_email=self.profile.business_email or "",
            default_hashtags=" ".join(self.profile.default_hashtags),
        )

        # Get LLM response
        response = await self.llm.generate_json(
            prompt=prompt,
            system=SEO_SYSTEM_PROMPT,
            temperature=0.7,
        )

        metadata = VideoMetadata(
            title=response["title"],
            description=response["description"],
            tags=response["tags"],
            hashtags=response.get("hashtags", self.profile.default_hashtags),
        )

        changes_summary = response.get("changes_summary", "No summary provided")

        return metadata, changes_summary

    async def generate_chapters(
        self,
        transcript_with_timestamps: list[dict],
        video_duration: float,
    ) -> list[Chapter]:
        """Generate video chapters from timestamped transcript.

        Args:
            transcript_with_timestamps: List of dicts with 'word', 'start_time', 'end_time'.
            video_duration: Total video duration in seconds.

        Returns:
            List of Chapter objects with timestamps and titles.
        """
        # Format transcript with timestamps for the LLM
        # Group words into segments for easier processing
        formatted_transcript = self._format_timestamped_transcript(transcript_with_timestamps)

        prompt = CHAPTER_GENERATION_PROMPT.format(
            transcript=formatted_transcript,
            video_duration=self._format_duration(video_duration),
        )

        response = await self.llm.generate_json(
            prompt=prompt,
            system="You are an expert at analyzing video content and creating clear, descriptive YouTube chapters. Always respond with valid JSON.",  # noqa: E501
            temperature=0.5,
        )

        chapters = []
        for ch in response.get("chapters", []):
            chapters.append(
                Chapter(
                    time=ch["time"],
                    title=ch["title"],
                )
            )

        return chapters

    def _format_timestamped_transcript(self, words: list[dict]) -> str:
        """Format word-level timestamps into readable segments.

        Groups words into ~30 second segments with timestamps.
        """
        if not words:
            return "No transcript available"

        segments = []
        current_segment = []
        segment_start = 0.0

        for word in words:
            current_segment.append(word["word"])

            # Create a new segment every ~30 seconds
            if word["end_time"] - segment_start >= 30:
                timestamp = self._format_duration(segment_start)
                text = " ".join(current_segment)
                segments.append(f"[{timestamp}] {text}")

                segment_start = word["end_time"]
                current_segment = []

        # Add remaining words
        if current_segment:
            timestamp = self._format_duration(segment_start)
            text = " ".join(current_segment)
            segments.append(f"[{timestamp}] {text}")

        return "\n\n".join(segments)

    def _format_duration(self, seconds: float) -> str:
        """Format seconds as MM:SS or HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def _format_social_links(self) -> str:
        """Format social links for the prompt."""
        if not self.profile.social_links:
            return "Not configured"

        lines = []
        for platform, url in self.profile.social_links.items():
            lines.append(f"- {platform.title()}: {url}")
        return "\n".join(lines)
