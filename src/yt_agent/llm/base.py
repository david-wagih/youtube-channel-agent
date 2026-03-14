"""Base LLM interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from an LLM."""

    content: str
    model: str
    usage: dict | None = None


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'claude', 'openai')."""
        ...

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt/message.
            system: Optional system prompt.
            temperature: Sampling temperature (0.0-1.0).
            max_tokens: Maximum tokens in response.

        Returns:
            LLMResponse with the generated content.
        """
        ...

    async def generate_json(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> dict:
        """Generate a JSON response from the LLM.

        Args:
            prompt: The user prompt requesting JSON output.
            system: Optional system prompt.
            temperature: Lower temperature for more deterministic JSON.

        Returns:
            Parsed JSON dictionary.
        """
        import json

        response = await self.generate(
            prompt=prompt,
            system=system,
            temperature=temperature,
        )

        # Extract JSON from response (handle markdown code blocks)
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        return json.loads(content.strip())
