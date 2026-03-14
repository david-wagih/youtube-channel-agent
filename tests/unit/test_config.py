"""Tests for config.py."""

from yt_agent.config import ChannelProfile


def _make_profile(data: dict) -> ChannelProfile:
    """Create a ChannelProfile without touching the filesystem."""
    profile = ChannelProfile.__new__(ChannelProfile)
    profile._data = data
    return profile


def test_not_configured_when_empty():
    profile = _make_profile({})
    assert not profile.is_configured()


def test_configured_when_channel_name_set():
    profile = _make_profile({"channel_name": "DevOps with David"})
    assert profile.is_configured()


def test_social_links_default_empty_dict():
    profile = _make_profile({})
    assert profile.social_links == {}


def test_social_links_returns_stored_value():
    profile = _make_profile({"social_links": {"github": "https://github.com/dave"}})
    assert profile.social_links["github"] == "https://github.com/dave"


def test_default_hashtags_empty_list():
    profile = _make_profile({})
    assert profile.default_hashtags == []


def test_channel_name_none_when_not_set():
    profile = _make_profile({})
    assert profile.channel_name is None


def test_business_email_none_when_not_set():
    profile = _make_profile({})
    assert profile.business_email is None


def test_channel_name_setter():
    profile = _make_profile({})
    profile.channel_name = "Test Channel"
    assert profile.channel_name == "Test Channel"


def test_default_hashtags_setter():
    profile = _make_profile({})
    profile.default_hashtags = ["#devops", "#linux"]
    assert profile.default_hashtags == ["#devops", "#linux"]
