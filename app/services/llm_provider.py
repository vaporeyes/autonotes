# ABOUTME: Abstract LLM provider interface with Claude and OpenAI implementations.
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
        self._model = "claude-sonnet-4-20250514"

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


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self._client = openai.AsyncOpenAI(api_key=settings.llm_api_key)
        self._model = "gpt-4o"

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
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model


def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "claude":
        return ClaudeProvider()
    elif settings.llm_provider == "openai":
        return OpenAIProvider()
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
