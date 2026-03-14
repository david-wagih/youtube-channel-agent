"""Tests for seo/optimizer.py — pure logic, no LLM calls."""

from unittest.mock import MagicMock

import pytest

from yt_agent.seo.optimizer import Chapter, SEOOptimizer, VideoMetadata


@pytest.fixture
def optimizer():
    mock_llm = MagicMock()
    mock_profile = MagicMock()
    mock_profile.channel_name = "Test Channel"
    mock_profile.social_links = {}
    mock_profile.business_email = None
    mock_profile.default_hashtags = []
    return SEOOptimizer(llm=mock_llm, profile=mock_profile)


# --- _format_duration ---


def test_format_duration_under_one_minute(optimizer):
    assert optimizer._format_duration(45.0) == "0:45"


def test_format_duration_exactly_one_minute(optimizer):
    assert optimizer._format_duration(60.0) == "1:00"


def test_format_duration_minutes_and_seconds(optimizer):
    assert optimizer._format_duration(90.5) == "1:30"


def test_format_duration_hours(optimizer):
    assert optimizer._format_duration(3661.0) == "1:01:01"


def test_format_duration_zero(optimizer):
    assert optimizer._format_duration(0.0) == "0:00"


# --- _format_timestamped_transcript ---


def test_format_transcript_empty_returns_fallback(optimizer):
    result = optimizer._format_timestamped_transcript([])
    assert result == "No transcript available"


def test_format_transcript_single_segment(optimizer):
    words = [
        {"word": "hello", "start_time": 0.0, "end_time": 1.0},
        {"word": "world", "start_time": 1.0, "end_time": 2.0},
    ]
    result = optimizer._format_timestamped_transcript(words)
    assert "hello" in result
    assert "world" in result


def test_format_transcript_splits_at_30s_boundary(optimizer):
    # Build words spanning 65 seconds — should create 2 segments
    words = [
        {"word": f"word{i}", "start_time": float(i), "end_time": float(i + 1)}
        for i in range(65)
    ]
    result = optimizer._format_timestamped_transcript(words)
    assert "\n\n" in result  # Multiple segments produced


# --- Chapter ---


def test_chapter_str_format():
    ch = Chapter(time="1:30", title="Introduction")
    assert str(ch) == "1:30 Introduction"


# --- VideoMetadata ---


def test_video_metadata_format_chapters_empty():
    meta = VideoMetadata(title="T", description="D", tags=["a"])
    assert meta.format_chapters() == ""


def test_video_metadata_format_chapters():
    meta = VideoMetadata(
        title="T",
        description="D",
        tags=["a"],
        chapters=[Chapter("0:00", "Intro"), Chapter("1:30", "Main")],
    )
    formatted = meta.format_chapters()
    assert "0:00 Intro" in formatted
    assert "1:30 Main" in formatted
