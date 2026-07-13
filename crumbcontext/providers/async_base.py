from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, AsyncIterator, Mapping, Protocol

from .base import Provider, ProviderRequest, ProviderResponse

PROVIDER_STREAM_RESULT_SCHEMA = "crumbcontext.provider-stream-result.v1"


@dataclass(frozen=True)
class StreamEvent:
    provider: str
    event_type: str
    text_delta: str = ""
    text_snapshot: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    model: str | None = None
    response_id: str | None = None
    stop_reason: str | None = None
    complete: bool = False
    error: str | None = None
    raw_usage: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, include_raw: bool = False) -> dict[str, Any]:
        value = asdict(self)
        if not include_raw:
            value.pop("raw", None)
        return value


@dataclass(frozen=True)
class StreamResult:
    provider: str
    model: str
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    usage_kind: str
    complete: bool
    cancelled: bool = False
    timed_out: bool = False
    stop_reason: str | None = None
    response_id: str | None = None
    error: str | None = None
    raw_usage: dict[str, Any] = field(default_factory=dict)
    events: tuple[StreamEvent, ...] = ()

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def text_sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def to_provider_response(self) -> ProviderResponse:
        usage = dict(self.raw_usage)
        usage.update(
            {
                "stream_complete": self.complete,
                "stream_cancelled": self.cancelled,
                "stream_timed_out": self.timed_out,
                "stream_stop_reason": self.stop_reason,
                "stream_response_id": self.response_id,
                "stream_error": self.error,
                "stream_text_sha256": self.text_sha256,
            }
        )
        return ProviderResponse(
            provider=self.provider,
            model=self.model,
            text=self.text,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            latency_ms=self.latency_ms,
            usage_kind=self.usage_kind,
            raw_usage=usage,
        )

    def to_dict(
        self,
        *,
        redact_text: bool = False,
        include_events: bool = False,
        include_raw_events: bool = False,
    ) -> dict[str, Any]:
        value = {
            "schema_version": PROVIDER_STREAM_RESULT_SCHEMA,
            "provider": self.provider,
            "model": self.model,
            "text": (
                "[REDACTED: streamed response body omitted by policy]"
                if redact_text
                else self.text
            ),
            "text_redacted": bool(redact_text),
            "text_sha256": self.text_sha256,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "usage_kind": self.usage_kind,
            "complete": self.complete,
            "cancelled": self.cancelled,
            "timed_out": self.timed_out,
            "stop_reason": self.stop_reason,
            "response_id": self.response_id,
            "error": self.error,
            "raw_usage": self.raw_usage,
        }
        if include_events:
            value["events"] = [
                event.to_dict(include_raw=include_raw_events)
                for event in self.events
            ]
        return value

    def canonical_json(self, *, redact_text: bool = False) -> str:
        return json.dumps(
            self.to_dict(redact_text=redact_text),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )


class AsyncProvider(Protocol):
    name: str
    model: str

    async def run_async(self, request: ProviderRequest) -> ProviderResponse:
        """Execute one request without blocking the caller's event loop."""


class StreamingProvider(Protocol):
    name: str
    model: str

    def stream(self, request: ProviderRequest) -> AsyncIterator[StreamEvent]:
        """Yield normalized stream events for one request."""


class ProviderStreamError(RuntimeError):
    def __init__(self, result: StreamResult):
        self.result = result
        message = result.error or (
            "provider stream did not complete"
            if not result.complete
            else "provider stream failed"
        )
        super().__init__(message)


class ProviderStreamCancelled(RuntimeError):
    def __init__(self, result: StreamResult):
        self.result = result
        super().__init__("provider stream was cancelled")


class SyncProviderAdapter:
    """Run an existing synchronous provider in a worker thread."""

    def __init__(self, provider: Provider):
        self.provider = provider
        self.name = provider.name
        self.model = provider.model

    async def run_async(self, request: ProviderRequest) -> ProviderResponse:
        return await asyncio.to_thread(self.provider.run, request)


async def execute_provider_async(
    request: ProviderRequest,
    provider: Provider | AsyncProvider,
) -> ProviderResponse:
    runner = getattr(provider, "run_async", None)
    if runner is not None:
        return await runner(request)
    return await SyncProviderAdapter(provider).run_async(request)  # type: ignore[arg-type]


def _merge_usage(target: dict[str, Any], update: Mapping[str, Any]) -> None:
    for key, value in update.items():
        if value is None:
            continue
        target[key] = value


async def collect_stream(
    provider: StreamingProvider,
    request: ProviderRequest,
    *,
    timeout_seconds: float | None = None,
    cancel_event: asyncio.Event | None = None,
    retain_events: bool = False,
    require_complete: bool = False,
) -> StreamResult:
    """Collect a normalized provider stream into one explicit result.

    Timeouts and cooperative cancellation return partial results. Native task
    cancellation raises ``ProviderStreamCancelled`` carrying the partial result.
    ``require_complete`` converts any incomplete result into
    ``ProviderStreamError``.
    """

    started = time.perf_counter()
    text_parts: list[str] = []
    text_snapshot: str | None = None
    input_tokens = 0
    output_tokens = 0
    model = provider.model
    response_id: str | None = None
    stop_reason: str | None = None
    raw_usage: dict[str, Any] = {}
    events: list[StreamEvent] = []
    complete = False
    cancelled = False
    timed_out = False
    error: str | None = None
    iterator = provider.stream(request)

    async def consume() -> None:
        nonlocal input_tokens, output_tokens, model, response_id
        nonlocal stop_reason, complete, cancelled, error, text_snapshot
        async for event in iterator:
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break
            if retain_events:
                events.append(event)
            if event.text_delta:
                text_parts.append(event.text_delta)
            if event.text_snapshot is not None:
                text_snapshot = event.text_snapshot
            if event.input_tokens is not None:
                input_tokens = max(0, int(event.input_tokens))
            if event.output_tokens is not None:
                output_tokens = max(0, int(event.output_tokens))
            if event.model:
                model = event.model
            if event.response_id:
                response_id = event.response_id
            if event.stop_reason:
                stop_reason = event.stop_reason
            if event.raw_usage:
                _merge_usage(raw_usage, event.raw_usage)
            if event.error:
                error = event.error
            if event.complete:
                complete = True

    async def close_iterator() -> None:
        closer = getattr(iterator, "aclose", None)
        if closer is not None:
            try:
                await closer()
            except Exception:
                pass

    def snapshot() -> StreamResult:
        text = "".join(text_parts)
        if not text and text_snapshot:
            text = text_snapshot
        return StreamResult(
            provider=provider.name,
            model=model,
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            usage_kind=(
                "provider_reported_streaming"
                if complete and not error
                else "provider_stream_partial"
            ),
            complete=complete and not cancelled and not timed_out and not error,
            cancelled=cancelled,
            timed_out=timed_out,
            stop_reason=stop_reason,
            response_id=response_id,
            error=error,
            raw_usage=dict(raw_usage),
            events=tuple(events),
        )

    try:
        if timeout_seconds is None:
            await consume()
        else:
            if timeout_seconds <= 0:
                raise ValueError("timeout_seconds must be greater than zero")
            await asyncio.wait_for(consume(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        timed_out = True
        error = f"provider stream timed out after {timeout_seconds} seconds"
    except asyncio.CancelledError as exc:
        cancelled = True
        error = "provider stream task was cancelled"
        await close_iterator()
        raise ProviderStreamCancelled(snapshot()) from exc
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        await close_iterator()

    result = snapshot()
    if require_complete and not result.complete:
        raise ProviderStreamError(result)
    return result


__all__ = [
    "AsyncProvider",
    "PROVIDER_STREAM_RESULT_SCHEMA",
    "ProviderStreamCancelled",
    "ProviderStreamError",
    "StreamEvent",
    "StreamResult",
    "StreamingProvider",
    "SyncProviderAdapter",
    "collect_stream",
    "execute_provider_async",
]
