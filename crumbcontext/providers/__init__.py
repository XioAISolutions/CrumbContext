from __future__ import annotations

from typing import Any

from .anthropic import (
    DEFAULT_ANTHROPIC_MODEL,
    AnthropicProvider,
    AnthropicRefusalError,
    build_anthropic_payload,
)
from .base import Provider, ProviderRequest, ProviderResponse
from .mock import MockProvider
from .openai import OpenAIProvider, build_openai_payload


def get_provider(name: str, **options: Any) -> Provider:
    normalized = name.strip().lower()
    if normalized == "mock":
        if options:
            unsupported = ", ".join(sorted(options))
            raise ValueError(f"mock provider does not accept options: {unsupported}")
        return MockProvider()
    if normalized == "anthropic":
        return AnthropicProvider(**options)
    if normalized == "openai":
        return OpenAIProvider(**options)
    raise ValueError(
        f"unknown provider {name!r}; available providers: mock, anthropic, openai"
    )


__all__ = [
    "AnthropicProvider",
    "AnthropicRefusalError",
    "DEFAULT_ANTHROPIC_MODEL",
    "MockProvider",
    "OpenAIProvider",
    "Provider",
    "ProviderRequest",
    "ProviderResponse",
    "build_anthropic_payload",
    "build_openai_payload",
    "get_provider",
]
