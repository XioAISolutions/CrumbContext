from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Mapping

from .async_base import (
    AsyncProvider,
    StreamEvent,
    StreamResult,
    StreamingProvider,
    collect_stream,
    execute_provider_async,
)
from .base import Provider, ProviderRequest, ProviderResponse
from .mock import MockProvider
from .registry import get_provider
from .streaming_adapters import AnthropicStreamingProvider, OpenAIStreamingProvider


class MockStreamingProvider:
    """Deterministic offline stream for tests, examples, and UI integration."""

    name = "mock"

    def __init__(
        self,
        *,
        chunk_chars: int = 48,
        delay_seconds: float = 0.0,
    ) -> None:
        if chunk_chars < 1:
            raise ValueError("chunk_chars must be positive")
        if delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative")
        self.chunk_chars = chunk_chars
        self.delay_seconds = delay_seconds
        self._provider = MockProvider()
        self.model = self._provider.model

    async def stream(self, request: ProviderRequest) -> AsyncIterator[StreamEvent]:
        response = self._provider.run(request)
        yield StreamEvent(
            provider=self.name,
            event_type="response.created",
            input_tokens=response.input_tokens,
            model=response.model,
            response_id=f"mock-{request.sha256[:16]}",
            raw_usage=dict(response.raw_usage),
        )
        for start in range(0, len(response.text), self.chunk_chars):
            if self.delay_seconds:
                await asyncio.sleep(self.delay_seconds)
            yield StreamEvent(
                provider=self.name,
                event_type="response.output_text.delta",
                text_delta=response.text[start : start + self.chunk_chars],
            )
        yield StreamEvent(
            provider=self.name,
            event_type="response.completed",
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            model=response.model,
            response_id=f"mock-{request.sha256[:16]}",
            stop_reason="completed",
            complete=True,
            raw_usage=dict(response.raw_usage),
        )


async def execute_named_provider_async(
    request: ProviderRequest,
    provider: str | Provider | AsyncProvider = "mock",
    *,
    provider_options: Mapping[str, Any] | None = None,
) -> ProviderResponse:
    """Execute a provider without blocking the event loop.

    Existing synchronous adapters run in a worker thread. Injected async
    providers execute directly.
    """

    options = dict(provider_options or {})
    if isinstance(provider, str):
        resolved: Provider | AsyncProvider = get_provider(provider, **options)
    else:
        if options:
            raise ValueError(
                "provider_options cannot be used with an injected provider instance"
            )
        resolved = provider
    return await execute_provider_async(request, resolved)


def get_streaming_provider(name: str, **options: Any) -> StreamingProvider:
    normalized = name.strip().lower()
    if normalized == "mock":
        return MockStreamingProvider(**options)
    if normalized == "anthropic":
        return AnthropicStreamingProvider(**options)
    if normalized == "openai":
        return OpenAIStreamingProvider(**options)
    raise ValueError(
        f"unsupported streaming provider {name!r}; expected mock, anthropic, or openai"
    )


async def execute_provider_stream(
    request: ProviderRequest,
    provider: str | StreamingProvider = "mock",
    *,
    provider_options: Mapping[str, Any] | None = None,
    timeout_seconds: float | None = None,
    cancel_event: asyncio.Event | None = None,
    retain_events: bool = False,
    require_complete: bool = False,
) -> StreamResult:
    """Execute and collect a normalized provider stream."""

    options = dict(provider_options or {})
    if isinstance(provider, str):
        resolved = get_streaming_provider(provider, **options)
    else:
        if options:
            raise ValueError(
                "provider_options cannot be used with an injected streaming provider"
            )
        resolved = provider
    return await collect_stream(
        resolved,
        request,
        timeout_seconds=timeout_seconds,
        cancel_event=cancel_event,
        retain_events=retain_events,
        require_complete=require_complete,
    )


__all__ = [
    "MockStreamingProvider",
    "execute_named_provider_async",
    "execute_provider_stream",
    "get_streaming_provider",
]
