# Async and streaming execution

CrumbContext provides a separate async surface so applications can adopt non-blocking or streamed provider execution without changing the existing synchronous API.

```python
from crumbcontext.async_api import (
    execute_named_provider_async,
    execute_provider_stream,
)
```

The implementation uses the Python standard library and adds no mandatory async HTTP dependency. Existing synchronous providers run through `asyncio.to_thread`; native streams use Server-Sent Events with an injectable transport.

## Safety contract

Async and streaming execution does not change the routing contract:

- system and developer authority remains native provider instruction content;
- exact values remain native text and exact sidecars;
- historical images remain non-authoritative;
- OpenAI requests retain `store: false`;
- API keys are read from explicit arguments or environment variables and are never written to stream results;
- thinking, signature, tool-input, and reasoning deltas are not accumulated as user-visible answer text;
- incomplete, failed, timed-out, and cancelled streams are never marked complete.

## Async execution of the existing providers

`execute_named_provider_async` accepts the same canonical `ProviderRequest` used by the synchronous API.

```python
import asyncio

from crumbcontext import build_baseline_request
from crumbcontext.async_api import execute_named_provider_async

request = build_baseline_request(
    "Return JSON containing the exact ID.",
    [
        {
            "id": "system",
            "role": "system",
            "kind": "instruction",
            "content": "Return JSON and preserve exact values.",
            "authoritative": True,
        },
        {
            "id": "current",
            "role": "user",
            "kind": "message",
            "content": "The exact ID is ABC-42.",
        },
    ],
)

response = asyncio.run(execute_named_provider_async(request, "mock"))
print(response.to_dict())
```

Named Anthropic and OpenAI execution accepts the same provider options as the synchronous adapters. Existing synchronous provider implementations are executed in a worker thread so they do not block the caller's event loop.

## Collect a deterministic offline stream

```python
import asyncio

from crumbcontext.async_api import execute_provider_stream

result = asyncio.run(
    execute_provider_stream(
        request,
        "mock",
        provider_options={"chunk_chars": 24},
        retain_events=True,
        require_complete=True,
    )
)

print(result.text)
print(result.input_tokens, result.output_tokens)
print(result.text_sha256)
```

The mock stream requires no network or provider key. It is intended for UI integration, deterministic tests, and cancellation handling.

## Anthropic Messages streaming

```python
import asyncio
import os

from crumbcontext.async_api import AnthropicStreamingProvider, execute_provider_stream

provider = AnthropicStreamingProvider(
    model="EXACT_ANTHROPIC_MODEL_ID",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    artifact_root="routed-context",
    max_tokens=1024,
)

result = asyncio.run(
    execute_provider_stream(
        request,
        provider,
        timeout_seconds=180,
        require_complete=True,
    )
)
```

The adapter normalizes message-start, content-block, message-delta, message-stop, and error events. Text deltas are assembled in order. Thinking and signature deltas remain metadata and are not added to the answer text.

Provider-reported cache creation and cache-read usage is retained when Anthropic returns it.

## OpenAI Responses streaming

```python
import asyncio
import os

from crumbcontext.async_api import OpenAIStreamingProvider, execute_provider_stream

provider = OpenAIStreamingProvider(
    model="EXACT_OPENAI_MODEL_ID",
    api_key=os.environ["OPENAI_API_KEY"],
    artifact_root="routed-context",
    max_tokens=1024,
)

result = asyncio.run(
    execute_provider_stream(
        request,
        provider,
        timeout_seconds=180,
        require_complete=True,
    )
)
```

The adapter normalizes response lifecycle events, output-text and refusal deltas, completed snapshots, incomplete responses, failures, and errors. OpenAI request construction continues to set `store: false`.

Cached-input and reasoning-token details are retained when OpenAI returns them.

## Stream result

`StreamResult` records:

```text
provider
model
assembled text
text SHA-256
input/output/total tokens
latency
usage kind
complete
cancelled
timed_out
stop reason
response ID
error
raw usage
events, when explicitly retained
```

The schema identifier is:

```text
crumbcontext.provider-stream-result.v1
```

Convert a completed or partial stream into the existing provider response model with:

```python
response = result.to_provider_response()
```

Stream completion metadata is preserved in `response.raw_usage`.

## Timeouts

```python
result = asyncio.run(
    execute_provider_stream(
        request,
        provider,
        timeout_seconds=15,
    )
)

if result.timed_out:
    print(result.text)  # partial text, when any was received
```

Timeouts return an explicit partial result by default. The result has:

```text
complete = false
timed_out = true
usage_kind = provider_stream_partial
```

Set `require_complete=True` to raise `ProviderStreamError`. The exception carries the partial result in `exc.result`.

## Cooperative cancellation

```python
cancel = asyncio.Event()

result = await execute_provider_stream(
    request,
    provider,
    cancel_event=cancel,
)
```

Set the event when the application wants to stop after the current normalized event. The returned result is explicit:

```text
complete = false
cancelled = true
```

## Native task cancellation

Cancelling the `asyncio.Task` raises `ProviderStreamCancelled`, a subclass of `asyncio.CancelledError`. It carries the partial result:

```python
from crumbcontext.async_api import ProviderStreamCancelled

try:
    await task
except ProviderStreamCancelled as exc:
    partial = exc.result
    raise
```

Applications should preserve cancellation semantics by re-raising after recording the partial state.

## Response-body redaction

```python
saved = result.to_dict(redact_text=True)
```

Redaction removes the assembled response text from the serialized document while preserving:

- text SHA-256;
- usage and latency;
- completion, cancellation, and timeout state;
- provider/model and response ID;
- stop reason and error;
- provider usage details.

Redaction is a storage policy. The text exists in process memory while the stream is assembled.

## Injected transports

Both provider stream adapters accept an `event_source` implementing `AsyncSSESource`. This supports:

- deterministic tests;
- application-owned HTTP clients;
- proxies and internal gateways;
- custom telemetry and retry boundaries.

The source receives the final URL, headers, encoded request body, and timeout. It must yield raw SSE bytes and must not log authorization headers or request bodies containing sensitive context.

## Retries

CrumbContext does not automatically retry a partially consumed stream. Retrying after output begins can duplicate side effects or text.

Applications may safely retry only when their provider and task semantics allow it. Record each attempt separately with its own request/response IDs, latency, hashes, and completion state.

## Runnable examples

```bash
python examples/python/run_async_provider.py
python examples/python/stream_mock_provider.py
```

Both examples run without a provider key or paid request.
