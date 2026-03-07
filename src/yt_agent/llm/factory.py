"""LLM factory for creating provider instances."""

from typing import Literal

from ..config import settings
from .base import BaseLLM
from .claude import ClaudeLLM
from .openai import OpenAILLM


def create_llm(provider: Literal["claude", "openai"] | None = None) -> BaseLLM:
    """Create an LLM instance based on provider name.

    Args:
        provider: The provider to use. If None, uses default from settings.

    Returns:
        An LLM instance.

    Raises:
        ValueError: If provider is unknown or API key is missing.
    """
    provider = provider or settings.default_llm_provider

    if provider == "claude":
        return ClaudeLLM()
    elif provider == "openai":
        return OpenAILLM()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
