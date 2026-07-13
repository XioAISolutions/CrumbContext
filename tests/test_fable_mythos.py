from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

from crumbcontext import available_profiles, resolve_profile
from crumbcontext.async_api import (
    AnthropicStreamingProvider,
    ProviderStreamError,
    execute_provider_stream,
)
from crumbcontext.cli import _provider_options, build_parser
from crumbcontext.providers.anthropic import (
    ANTHROPIC_VERSION,
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_FALLBACK_MODEL,
    SERVER_SIDE_FALLBACK_BETA,
    AnthropicProvider,
    AnthropicRefusalError,
    build_anthropic_payload,
)
from crumbcontext.providers.base import ProviderRequest


def request(*blocks: dict[str, Any]) -> ProviderRequest:
    return ProviderRequest(
        mode="routed",
        task="Return JSON.",
        blocks=list(blocks) or [{"id": "u", "role": "user", "content": "Hello"}],
    )


def cache_markers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    system = payload.get("system")
    if isinstance(system, list):
        blocks.extend(item for item in system if isinstance(item, dict))
    for message in payload.get("messages", []):
        if isinstance(message, dict) and isinstance(message.get("content"), list):
            blocks.extend(item for item in message["content"] if isinstance(item, dict))
    return [item for item in blocks if "cache_control" in item]


def sse(*events: dict[str, Any]) -> list[bytes]:
    return [
        (
            f"event: {event.get('type', 'message')}\n"
            f"data: {json.dumps(event, separators=(',', ':'))}\n\n"
        ).encode()
        for event in events
    ]


def source_from_chunks(chunks: list[bytes], captured: dict[str, Any] | None = None):
    async def source(url, headers, body, timeout_seconds) -> AsyncIterator[bytes]:
        if captured is not None:
            captured.update(url=url, headers=dict(headers), body=json.loads(body))
        for chunk in chunks:
            yield chunk

    return source


def test_fable_defaults_enable_server_fallback_and_versioned_user_agent():
    captured: dict[str, Any] = {}

    def transport(url, headers, body, timeout):
        captured.update(headers=dict(headers), body=json.loads(body))
        response = {
            "model": "claude-fable-5",
            "content": [{"type": "text", "text": "ok"}],
            "stop_reason": "end_turn",
            "stop_details": None,
            "usage": {"input_tokens": 2, "output_tokens": 1},
        }
        return 200, {"request-id": "req-default"}, json.dumps(response).encode()

    provider = AnthropicProvider(api_key="test", transport=transport)
    response = provider.run(request())
    assert provider.model == DEFAULT_ANTHROPIC_MODEL == "claude-fable-5"
    assert provider.max_tokens == 4096
    assert captured["body"]["max_tokens"] == 4096
    assert captured["body"]["fallbacks"] == [{"model": DEFAULT_FALLBACK_MODEL}]
    assert captured["headers"]["anthropic-beta"] == SERVER_SIDE_FALLBACK_BETA
    assert captured["headers"]["anthropic-version"] == ANTHROPIC_VERSION
    assert captured["headers"]["user-agent"].startswith("crumb-context/")
    assert response.raw_usage["stop_details"] is None


def test_fallback_is_fable_only_and_can_be_disabled():
    common = dict(max_tokens=100, artifact_root=None, enable_cache=True)
    fable = build_anthropic_payload(request(), model="claude-fable-5", **common)
    mythos = build_anthropic_payload(request(), model="claude-mythos-5", **common)
    sonnet = build_anthropic_payload(request(), model="claude-sonnet-4-6", **common)
    disabled = build_anthropic_payload(
        request(), model="claude-fable-5", enable_fallback=False, **common
    )
    assert fable["fallbacks"] == [{"model": "claude-opus-4-8"}]
    assert "fallbacks" not in mythos
    assert "fallbacks" not in sonnet
    assert "fallbacks" not in disabled


def test_cache_ttl_and_breakpoint_cap_keep_last_four():
    blocks = [
        {
            "id": f"cache-{index}",
            "role": "user",
            "kind": "docs",
            "lane": "cache",
            "cached_content": f"stable-{index}",
        }
        for index in range(6)
    ]
    payload = build_anthropic_payload(
        request(*blocks),
        model="claude-fable-5",
        max_tokens=100,
        artifact_root=None,
        enable_cache=True,
        cache_ttl="1h",
    )
    marked = cache_markers(payload)
    assert len(marked) == 4
    assert all(item["cache_control"] == {"type": "ephemeral", "ttl": "1h"} for item in marked)
    assert [item["text"].rsplit("-", 1)[-1] for item in marked] == ["2", "3", "4", "5"]


def test_invalid_cache_ttl_fails_closed():
    with pytest.raises(ValueError, match="cache_ttl"):
        AnthropicProvider(api_key="test", cache_ttl="24h")


def test_refusal_error_carries_stop_details_and_request_id():
    def transport(url, headers, body, timeout):
        response = {
            "model": "claude-fable-5",
            "content": [],
            "stop_reason": "refusal",
            "stop_details": {
                "type": "refusal",
                "category": "cyber",
                "explanation": "Request could enable cyber harm.",
            },
            "usage": {"input_tokens": 12, "output_tokens": 0},
        }
        return 200, {"request-id": "req-refusal"}, json.dumps(response).encode()

    provider = AnthropicProvider(
        api_key="test", enable_fallback=False, transport=transport
    )
    with pytest.raises(AnthropicRefusalError) as raised:
        provider.run(request())
    message = str(raised.value)
    assert "cyber" in message
    assert "Request could enable cyber harm" in message
    assert "req-refusal" in message
    assert raised.value.raw_usage["stop_details"]["category"] == "cyber"


def test_empty_text_max_tokens_error_suggests_cli_flag():
    def transport(url, headers, body, timeout):
        response = {
            "model": "claude-fable-5",
            "content": [],
            "stop_reason": "max_tokens",
            "stop_details": None,
            "usage": {"input_tokens": 12, "output_tokens": 4096},
        }
        return 200, {"request-id": "req-max"}, json.dumps(response).encode()

    provider = AnthropicProvider(api_key="test", transport=transport)
    with pytest.raises(ValueError, match=r"raise --max-tokens"):
        provider.run(request())


def test_fallback_metadata_records_serving_model_blocks_and_iterations():
    def transport(url, headers, body, timeout):
        response = {
            "model": "claude-opus-4-8",
            "content": [
                {
                    "type": "fallback",
                    "from": {"model": "claude-fable-5"},
                    "to": {"model": "claude-opus-4-8"},
                },
                {"type": "text", "text": "served"},
            ],
            "stop_reason": "end_turn",
            "stop_details": None,
            "usage": {
                "input_tokens": 10,
                "output_tokens": 2,
                "iterations": [
                    {"type": "message", "model": "claude-fable-5"},
                    {"type": "fallback_message", "model": "claude-opus-4-8"},
                ],
            },
        }
        return 200, {"request-id": "req-fallback"}, json.dumps(response).encode()

    response = AnthropicProvider(api_key="test", transport=transport).run(request())
    assert response.model == "claude-opus-4-8"
    assert response.raw_usage["fallback_used"] is True
    assert response.raw_usage["fallback_blocks"][0]["to"]["model"] == "claude-opus-4-8"
    assert response.raw_usage["iterations"][1]["type"] == "fallback_message"


def test_streaming_refusal_is_an_explicit_provider_error():
    chunks = sse(
        {
            "type": "message_start",
            "message": {
                "id": "msg-refusal",
                "model": "claude-fable-5",
                "usage": {"input_tokens": 20, "output_tokens": 0},
            },
        },
        {
            "type": "message_delta",
            "delta": {
                "stop_reason": "refusal",
                "stop_details": {
                    "category": "bio",
                    "explanation": "Request could enable biological harm.",
                },
            },
            "usage": {"output_tokens": 0},
        },
        {"type": "message_stop"},
    )
    provider = AnthropicStreamingProvider(
        api_key="test",
        enable_fallback=False,
        event_source=source_from_chunks(chunks),
    )
    with pytest.raises(ProviderStreamError) as raised:
        asyncio.run(execute_provider_stream(request(), provider, require_complete=True))
    assert raised.value.result.stop_reason == "refusal"
    assert "bio" in (raised.value.result.error or "")
    assert "biological harm" in (raised.value.result.error or "")


def test_streaming_defaults_match_sync_and_send_fable_fallback():
    captured: dict[str, Any] = {}
    chunks = sse(
        {
            "type": "message_start",
            "message": {
                "id": "msg-ok",
                "model": "claude-fable-5",
                "usage": {"input_tokens": 1, "output_tokens": 0},
            },
        },
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "ok"}},
        {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 1}},
        {"type": "message_stop"},
    )
    provider = AnthropicStreamingProvider(
        api_key="test", event_source=source_from_chunks(chunks, captured)
    )
    result = asyncio.run(execute_provider_stream(request(), provider, require_complete=True))
    assert provider.model == "claude-fable-5"
    assert provider.max_tokens == 4096
    assert result.text == "ok"
    assert captured["body"]["fallbacks"] == [{"model": "claude-opus-4-8"}]
    assert captured["headers"]["anthropic-beta"] == SERVER_SIDE_FALLBACK_BETA
    assert captured["headers"]["anthropic-version"] == ANTHROPIC_VERSION


def test_frontier_vision_profile_and_cli_controls():
    assert "frontier-vision" in available_profiles()
    profile = resolve_profile("frontier-vision")
    assert profile.config.image_width == 2576
    assert profile.config.image_height == 1196
    assert profile.config.image_page_chars == 24000
    parser = build_parser()
    args = parser.parse_args(
        [
            "counterfactual",
            "--provider",
            "anthropic",
            "--cache-ttl",
            "1h",
            "--no-fallback",
        ]
    )
    assert args.max_tokens == 4096
    assert _provider_options(args)["cache_ttl"] == "1h"
    assert _provider_options(args)["enable_fallback"] is False
