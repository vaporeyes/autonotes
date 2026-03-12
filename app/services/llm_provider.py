# ABOUTME: Abstract LLM provider interface with Claude, OpenAI, and OpenRouter implementations.
# ABOUTME: Factory function selects provider based on LLM_PROVIDER config setting.

from abc import ABC, abstractmethod

import anthropic
import openai

from app.config import settings


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, system_prompt: str, user_message: str) -> tuple[str, int, int]:
        """Returns (response_text, prompt_tokens, completion_tokens)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass


class ClaudeProvider(LLMProvider):
    def __init__(self):
        self._client = anthropic.AsyncAnthropic(api_key=settings.llm_api_key)
        self._model = settings.llm_model or "claude-sonnet-4-20250514"

    async def complete(self, system_prompt: str, user_message: str) -> tuple[str, int, int]:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        text = response.content[0].text
        return text, response.usage.input_tokens, response.usage.output_tokens

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def model_name(self) -> str:
        return self._model


class OpenAICompatibleProvider(LLMProvider):
    """Works with OpenAI, OpenRouter, and any OpenAI-compatible API."""

    def __init__(self, provider: str, default_model: str, base_url: str | None = None):
        self._provider = provider
        self._model = settings.llm_model or default_model
        self._client = openai.AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=base_url or settings.llm_base_url or None,
        )

    async def complete(self, system_prompt: str, user_message: str) -> tuple[str, int, int]:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=4096,
        )
        text = response.choices[0].message.content or ""
        usage = response.usage
        return text, usage.prompt_tokens if usage else 0, usage.completion_tokens if usage else 0

    @property
    def provider_name(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model


def get_llm_provider() -> LLMProvider:
    provider = settings.llm_provider
    if provider == "claude":
        return ClaudeProvider()
    elif provider == "openai":
        return OpenAICompatibleProvider("openai", "gpt-4o")
    elif provider == "openrouter":
        return OpenAICompatibleProvider(
            "openrouter",
            "anthropic/claude-sonnet-4",
            base_url="https://openrouter.ai/api/v1",
        )
    raise ValueError(f"Unknown LLM provider: {provider}")
