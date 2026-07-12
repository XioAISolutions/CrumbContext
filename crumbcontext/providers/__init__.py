from __future__ import annotations

from typing import Any

from .anthropic import AnthropicProvider, build_anthropic_payload
from .base import Provider, ProviderRequest, ProviderResponse
from .mock import MockProvider


def get_provider(name: str, **options: Any) -> Provider:
    normalized = name.strip().lower()
    if normalized == "mock":
        if options:
            unsupported = ", ".join(sorted(options))
            raise ValueError(f"mock provider does not accept options: {unsupported}")
        return MockProvider()
    if normalized == "anthropic":
        return AnthropicProvider(**options)
    raise ValueError(
        f"unknown provider {name!r}; available providers: mock, anthropic. "
        "The OpenAI adapter is tracked on the public roadmap."
    )


__all__ = [
    "AnthropicProvider",
    "MockProvider",
    "Provider",
    "ProviderRequest",
    "ProviderResponse",
    "build_anthropic_payload",
    "get_provider",
]
