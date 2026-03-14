"""Configuration management for YouTube Agent."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Provider Keys
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # Google Cloud
    google_application_credentials: str | None = None
    gcs_bucket: str | None = None  # GCS bucket for temporary audio uploads

    # Defaults
    default_llm_provider: Literal["claude", "openai"] = "claude"
    default_timezone: str = "Africa/Cairo"
    default_schedule_day: str = "Saturday"
    default_schedule_time: str = "19:00"


class ChannelProfile:
    """User's channel profile configuration."""

    def __init__(self, profile_path: Path | None = None):
        self.profile_path = profile_path or self._default_profile_path()
        self._data: dict = {}
        self._load()

    @staticmethod
    def _default_profile_path() -> Path:
        """Get default profile path (~/.config/yt-agent/profile.yaml)."""
        config_dir = Path.home() / ".config" / "yt-agent"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "profile.yaml"

    def _load(self) -> None:
        """Load profile from YAML file."""
        if self.profile_path.exists():
            with open(self.profile_path) as f:
                self._data = yaml.safe_load(f) or {}

    def save(self) -> None:
        """Save profile to YAML file."""
        with open(self.profile_path, "w") as f:
            yaml.dump(self._data, f, default_flow_style=False)

    @property
    def channel_name(self) -> str | None:
        return self._data.get("channel_name")

    @channel_name.setter
    def channel_name(self, value: str) -> None:
        self._data["channel_name"] = value

    @property
    def social_links(self) -> dict[str, str]:
        return self._data.get("social_links", {})

    @social_links.setter
    def social_links(self, value: dict[str, str]) -> None:
        self._data["social_links"] = value

    @property
    def business_email(self) -> str | None:
        return self._data.get("business_email")

    @business_email.setter
    def business_email(self, value: str) -> None:
        self._data["business_email"] = value

    @property
    def default_hashtags(self) -> list[str]:
        return self._data.get("default_hashtags", [])

    @default_hashtags.setter
    def default_hashtags(self, value: list[str]) -> None:
        self._data["default_hashtags"] = value

    def is_configured(self) -> bool:
        """Check if profile has the minimum required configuration (channel name)."""
        return bool(self.channel_name and self.channel_name.strip())


# Global settings instance
settings = Settings()


def get_credentials_dir() -> Path:
    """Get the directory for storing OAuth credentials."""
    creds_dir = Path.home() / ".config" / "yt-agent" / "credentials"
    creds_dir.mkdir(parents=True, exist_ok=True)
    return creds_dir
