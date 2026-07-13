"""Supported async and streaming integration surface for CrumbContext."""

from .providers.async_base import (
    AsyncProvider,
    PROVIDER_STREAM_RESULT_SCHEMA,
    ProviderStreamCancelled,
    ProviderStreamError,
    StreamEvent,
    StreamResult,
    StreamingProvider,
    SyncProviderAdapter,
    collect_stream,
    execute_provider_async,
)
from .providers.async_registry import (
    MockStreamingProvider,
    execute_named_provider_async,
    execute_provider_stream,
    get_streaming_provider,
)
from .providers.sse import (
    AsyncSSESource,
    HTTPStreamError,
    SSEMessage,
    decode_sse,
    urllib_sse_source,
)
from .providers.streaming_adapters import (
    AnthropicStreamingProvider,
    OpenAIStreamingProvider,
)

__all__ = [
    "ANTHROPIC_MESSAGES_URL",
    "AsyncProvider",
    "AsyncSSESource",
    "AnthropicStreamingProvider",
    "HTTPStreamError",
    "MockStreamingProvider",
    "OPENAI_RESPONSES_URL",
    "OpenAIStreamingProvider",
    "PROVIDER_STREAM_RESULT_SCHEMA",
    "ProviderStreamCancelled",
    "ProviderStreamError",
    "SSEMessage",
    "StreamEvent",
    "StreamResult",
    "StreamingProvider",
    "SyncProviderAdapter",
    "collect_stream",
    "decode_sse",
    "execute_named_provider_async",
    "execute_provider_async",
    "execute_provider_stream",
    "get_streaming_provider",
    "urllib_sse_source",
]

# Re-export endpoint constants without forcing callers into implementation modules.
from .providers.streaming_adapters import (  # noqa: E402
    ANTHROPIC_MESSAGES_URL,
    OPENAI_RESPONSES_URL,
)
