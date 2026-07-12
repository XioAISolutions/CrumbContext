from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

from crumbcontext import build_baseline_request
from crumbcontext.async_api import (
    AnthropicStreamingProvider,
    MockStreamingProvider,
    OpenAIStreamingProvider,
    ProviderStreamCancelled,
    ProviderStreamError,
    StreamEvent,
    collect_stream,
    decode_sse,
    execute_named_provider_async,
    execute_provider_stream,
)


BLOCKS = [
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
        "content": "Return status ok and exact ID ABC-42.",
        "age_turns": 0,
    },
]


def request():
    return build_baseline_request("Return JSON with status and ID.", BLOCKS)


def sse(*events: dict[str, Any]) -> list[bytes]:
    chunks: list[bytes] = []
    for event in events:
        event_type = str(event.get("type") or "message")
        chunks.append(
            (
                f"event: {event_type}\n"
                f"data: {json.dumps(event, separators=(',', ':'))}\n\n"
            ).encode()
        )
    return chunks


def source_from_chunks(chunks: list[bytes], captured: dict[str, Any] | None = None):
    async def source(url, headers, body, timeout_seconds) -> AsyncIterator[bytes]:
        if captured is not None:
            captured.update(
                {
                    "url": url,
                    "headers": dict(headers),
                    "body": json.loads(body),
                    "timeout_seconds": timeout_seconds,
                }
            )
        for chunk in chunks:
            yield chunk

    return source


def test_sse_decoder_handles_fragmented_multiline_and_comments():
    async def chunks():
        yield b": keep-alive\nevent: custom\nid: 7\ndata: {\"a\":"
        yield b"1}\ndata: second\nretry: 2500\n\n"

    async def run():
        return [message async for message in decode_sse(chunks())]

    messages = asyncio.run(run())
    assert len(messages) == 1
    assert messages[0].event == "custom"
    assert messages[0].event_id == "7"
    assert messages[0].retry_ms == 2500
    assert messages[0].data == '{"a":1}\nsecond'


def test_mock_stream_matches_sync_provider_and_reports_complete_usage():
    async def run():
        return await execute_provider_stream(
            request(),
            MockStreamingProvider(chunk_chars=7),
            retain_events=True,
            require_complete=True,
        )

    result = asyncio.run(run())
    assert result.complete
    assert result.provider == "mock"
    assert result.text.startswith("{")
    assert json.loads(result.text)["status"] == "ok"
    assert result.input_tokens > 0
    assert result.output_tokens > 0
    assert result.stop_reason == "completed"
    assert any(event.text_delta for event in result.events)
    assert result.to_provider_response().raw_usage["stream_complete"] is True


def test_existing_sync_provider_runs_without_blocking_async_api():
    response = asyncio.run(execute_named_provider_async(request(), "mock"))
    assert response.provider == "mock"
    assert response.input_tokens > 0
    assert json.loads(response.text)["status"] == "ok"


def test_anthropic_stream_preserves_text_usage_cache_and_omits_thinking():
    captured: dict[str, Any] = {}
    chunks = sse(
        {
            "type": "message_start",
            "message": {
                "id": "msg_test",
                "model": "claude-test",
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 0,
                    "cache_creation_input_tokens": 40,
                    "cache_read_input_tokens": 70,
                },
            },
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "{\"status\":"},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "thinking_delta", "thinking": "private reasoning"},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "\"ok\"}"},
        },
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"output_tokens": 9},
        },
        {"type": "message_stop"},
    )
    provider = AnthropicStreamingProvider(
        model="claude-test",
        api_key="test-key",
        event_source=source_from_chunks(chunks, captured),
    )

    result = asyncio.run(
        execute_provider_stream(
            request(),
            provider,
            retain_events=True,
            require_complete=True,
        )
    )
    assert result.complete
    assert result.text == '{"status":"ok"}'
    assert "private reasoning" not in result.text
    assert result.input_tokens == 120
    assert result.output_tokens == 9
    assert result.raw_usage["cache_read_input_tokens"] == 70
    assert result.response_id == "msg_test"
    assert result.stop_reason == "end_turn"
    assert captured["body"]["stream"] is True
    assert captured["headers"]["x-api-key"] == "test-key"


def test_openai_stream_preserves_text_usage_cache_reasoning_and_store_false():
    captured: dict[str, Any] = {}
    chunks = sse(
        {
            "type": "response.created",
            "response": {
                "id": "resp_test",
                "model": "gpt-test",
                "usage": None,
            },
        },
        {"type": "response.output_text.delta", "delta": "{\"status\":"},
        {"type": "response.output_text.delta", "delta": "\"ok\"}"},
        {
            "type": "response.completed",
            "response": {
                "id": "resp_test",
                "model": "gpt-test",
                "status": "completed",
                "output": [],
                "usage": {
                    "input_tokens": 95,
                    "output_tokens": 11,
                    "input_tokens_details": {"cached_tokens": 60},
                    "output_tokens_details": {"reasoning_tokens": 4},
                },
            },
        },
    )
    provider = OpenAIStreamingProvider(
        model="gpt-test",
        api_key="test-key",
        event_source=source_from_chunks(chunks, captured),
    )
    result = asyncio.run(
        execute_provider_stream(
            request(),
            provider,
            retain_events=True,
            require_complete=True,
        )
    )
    assert result.complete
    assert result.text == '{"status":"ok"}'
    assert result.input_tokens == 95
    assert result.output_tokens == 11
    assert result.raw_usage["input_tokens_details"]["cached_tokens"] == 60
    assert result.raw_usage["output_tokens_details"]["reasoning_tokens"] == 4
    assert result.response_id == "resp_test"
    assert captured["body"]["stream"] is True
    assert captured["body"]["store"] is False
    assert captured["headers"]["authorization"] == "Bearer test-key"


def test_openai_completed_snapshot_is_used_when_no_delta_arrives():
    chunks = sse(
        {
            "type": "response.completed",
            "response": {
                "id": "resp_snapshot",
                "model": "gpt-test",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": "snapshot text"}
                        ],
                    }
                ],
                "usage": {"input_tokens": 10, "output_tokens": 2},
            },
        }
    )
    provider = OpenAIStreamingProvider(
        model="gpt-test",
        api_key="test-key",
        event_source=source_from_chunks(chunks),
    )
    result = asyncio.run(execute_provider_stream(request(), provider))
    assert result.complete
    assert result.text == "snapshot text"


def test_provider_incomplete_result_is_explicit_and_require_complete_raises():
    chunks = sse(
        {"type": "response.output_text.delta", "delta": "partial"},
        {
            "type": "response.incomplete",
            "response": {
                "id": "resp_partial",
                "model": "gpt-test",
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "usage": {"input_tokens": 10, "output_tokens": 1},
                "output": [],
            },
        },
    )
    provider = OpenAIStreamingProvider(
        model="gpt-test",
        api_key="test-key",
        event_source=source_from_chunks(chunks),
    )
    result = asyncio.run(execute_provider_stream(request(), provider))
    assert not result.complete
    assert result.text == "partial"
    assert result.error == "max_output_tokens"
    assert result.usage_kind == "provider_stream_partial"

    provider_again = OpenAIStreamingProvider(
        model="gpt-test",
        api_key="test-key",
        event_source=source_from_chunks(chunks),
    )
    with pytest.raises(ProviderStreamError) as raised:
        asyncio.run(
            execute_provider_stream(
                request(),
                provider_again,
                require_complete=True,
            )
        )
    assert raised.value.result.text == "partial"
    assert not raised.value.result.complete


def test_timeout_returns_partial_result_and_closes_stream():
    closed = asyncio.Event()

    class SlowProvider:
        name = "slow"
        model = "slow-v1"

        async def stream(self, request):
            try:
                yield StreamEvent(
                    provider="slow",
                    event_type="delta",
                    text_delta="partial",
                )
                await asyncio.sleep(10)
            finally:
                closed.set()

    async def run():
        result = await collect_stream(
            SlowProvider(),
            request(),
            timeout_seconds=0.02,
        )
        await asyncio.wait_for(closed.wait(), timeout=1)
        return result

    result = asyncio.run(run())
    assert not result.complete
    assert result.timed_out
    assert result.text == "partial"
    assert "timed out" in (result.error or "")


def test_cooperative_cancellation_returns_partial_result():
    cancel = asyncio.Event()

    class CooperativeProvider:
        name = "cooperative"
        model = "cooperative-v1"

        async def stream(self, request):
            yield StreamEvent(
                provider=self.name,
                event_type="delta",
                text_delta="first",
            )
            cancel.set()
            yield StreamEvent(
                provider=self.name,
                event_type="delta",
                text_delta="second",
            )

    result = asyncio.run(
        collect_stream(
            CooperativeProvider(),
            request(),
            cancel_event=cancel,
        )
    )
    assert result.cancelled
    assert not result.complete
    assert result.text == "first"


def test_native_task_cancellation_raises_with_partial_snapshot():
    started = asyncio.Event()

    class CancelProvider:
        name = "cancel"
        model = "cancel-v1"

        async def stream(self, request):
            yield StreamEvent(
                provider=self.name,
                event_type="delta",
                text_delta="partial",
            )
            started.set()
            await asyncio.sleep(10)

    async def run():
        task = asyncio.create_task(collect_stream(CancelProvider(), request()))
        await started.wait()
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except ProviderStreamCancelled as exc:
            return exc.result
        raise AssertionError("cancellation did not raise ProviderStreamCancelled")

    result = asyncio.run(run())
    assert result.cancelled
    assert result.text == "partial"
    assert not result.complete


def test_stream_result_redaction_keeps_hashes_usage_and_completion():
    result = asyncio.run(execute_provider_stream(request(), "mock"))
    value = result.to_dict(redact_text=True)
    assert value["schema_version"] == "crumbcontext.provider-stream-result.v1"
    assert value["text_redacted"] is True
    assert value["text"].startswith("[REDACTED")
    assert len(value["text_sha256"]) == 64
    assert value["input_tokens"] > 0
    assert value["complete"] is True


def test_provider_options_are_rejected_for_injected_stream_provider():
    async def run():
        return await execute_provider_stream(
            request(),
            MockStreamingProvider(),
            provider_options={"chunk_chars": 5},
        )

    with pytest.raises(ValueError, match="provider_options cannot be used"):
        asyncio.run(run())
