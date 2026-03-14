"""Custom exception hierarchy for yt-agent.

All exceptions inherit from YTAgentError so callers can catch either the
base class (for a blanket handler) or specific subclasses (for targeted
handling).  CLI entry points catch YTAgentError and print a clean message
without a traceback.
"""


class YTAgentError(Exception):
    """Base exception for all yt-agent errors."""


class AuthError(YTAgentError):
    """Raised when authentication fails or credentials are missing."""


class UploadError(YTAgentError):
    """Raised when a video or thumbnail upload fails."""


class TranscriptionError(YTAgentError):
    """Raised when audio transcription fails."""


class GCSError(TranscriptionError):
    """Raised when a Google Cloud Storage operation fails during transcription."""


class DriveError(YTAgentError):
    """Raised when a Google Drive operation fails."""


class ConfigurationError(YTAgentError):
    """Raised when required configuration is missing or invalid."""
