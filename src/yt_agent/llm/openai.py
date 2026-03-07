"""OpenAI GPT LLM implementation."""

from openai import AsyncOpenAI

from ..config import settings
from .base import BaseLLM, LLMResponse


class OpenAILLM(BaseLLM):
    """OpenAI GPT LLM provider."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o"):
        self.api_key = api_key or settings.openai_api_key
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        self.model = model
        self.client = AsyncOpenAI(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a response using OpenAI GPT."""
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        )
