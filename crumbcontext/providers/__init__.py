from .base import Provider, ProviderRequest, ProviderResponse
from .mock import MockProvider


def get_provider(name: str) -> Provider:
    normalized = name.strip().lower()
    if normalized == "mock":
        return MockProvider()
    raise ValueError(
        f"unknown provider {name!r}; available providers: mock. "
        "Anthropic and OpenAI adapters are tracked on the public roadmap."
    )


__all__ = [
    "MockProvider",
    "Provider",
    "ProviderRequest",
    "ProviderResponse",
    "get_provider",
]
