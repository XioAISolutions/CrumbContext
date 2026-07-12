from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, AsyncIterator

from .anthropic import build_anthropic_payload
from .async_base import StreamEvent
from .base import ProviderRequest
from .openai import build_openai_payload
from .sse import AsyncSSESource, SSEMessage, decode_sse, urllib_sse_source

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def _json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _required_text(value: str | None, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _usage_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return max(0, value)
    return None


def _anthropic_event(message: SSEMessage) -> StreamEvent | None:
    if message.data == "[DONE]":
        return None
    value = message.json()
    event_type = str(value.get("type") or message.event or "message")

    if event_type == "message_start":
        provider_message = value.get("message")
        provider_message = provider_message if isinstance(provider_message, dict) else {}
        usage = provider_message.get("usage")
        usage = usage if isinstance(usage, dict) else {}
        return StreamEvent(
            provider="anthropic",
            event_type=event_type,
            input_tokens=_usage_int(usage.get("input_tokens")),
            output_tokens=_usage_int(usage.get("output_tokens")),
            model=(
                str(provider_message.get("model"))
                if provider_message.get("model")
                else None
            ),
            response_id=(
                str(provider_message.get("id"))
                if provider_message.get("id")
                else None
            ),
            raw_usage=dict(usage),
            raw=value,
        )

    if event_type == "content_block_start":
        block = value.get("content_block")
        block = block if isinstance(block, dict) else {}
        text = block.get("text") if block.get("type") == "text" else ""
        return StreamEvent(
            provider="anthropic",
            event_type=event_type,
            text_delta=text if isinstance(text, str) else "",
            raw=value,
        )

    if event_type == "content_block_delta":
        delta = value.get("delta")
        delta = delta if isinstance(delta, dict) else {}
        delta_type = str(delta.get("type") or "unknown_delta")
        text = delta.get("text") if delta_type == "text_delta" else ""
        # Thinking/signature deltas are intentionally not accumulated as answer
        # text. They remain event metadata only when callers explicitly retain
        # raw events.
        return StreamEvent(
            provider="anthropic",
            event_type=delta_type,
            text_delta=text if isinstance(text, str) else "",
            raw=value,
        )

    if event_type == "message_delta":
        delta = value.get("delta")
        delta = delta if isinstance(delta, dict) else {}
        usage = value.get("usage")
        usage = usage if isinstance(usage, dict) else {}
        return StreamEvent(
            provider="anthropic",
            event_type=event_type,
            output_tokens=_usage_int(usage.get("output_tokens")),
            stop_reason=(
                str(delta.get("stop_reason"))
                if delta.get("stop_reason") is not None
                else None
            ),
            raw_usage=dict(usage),
            raw=value,
        )

    if event_type == "message_stop":
        return StreamEvent(
            provider="anthropic",
            event_type=event_type,
            complete=True,
            raw=value,
        )

    if event_type == "error":
        error = value.get("error")
        if isinstance(error, dict):
            message_value = error.get("message") or error.get("type")
        else:
            message_value = error
        return StreamEvent(
            provider="anthropic",
            event_type=event_type,
            error=str(message_value or "Anthropic stream error"),
            raw=value,
        )

    return StreamEvent(provider="anthropic", event_type=event_type, raw=value)


def _openai_output_text(response: dict[str, Any]) -> str:
    values: list[str] = []
    output = response.get("output")
    if not isinstance(output, list):
        return ""
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") in {"output_text", "text"}:
                text = part.get("text")
                if isinstance(text, str):
                    values.append(text)
            elif part.get("type") == "refusal":
                refusal = part.get("refusal")
                if isinstance(refusal, str):
                    values.append(refusal)
    return "".join(values)


def _openai_usage(response: dict[str, Any]) -> dict[str, Any]:
    usage = response.get("usage")
    return dict(usage) if isinstance(usage, dict) else {}


def _openai_event(message: SSEMessage) -> StreamEvent | None:
    if message.data == "[DONE]":
        return None
    value = message.json()
    event_type = str(value.get("type") or message.event or "message")

    if event_type in {"response.created", "response.in_progress"}:
        response = value.get("response")
        response = response if isinstance(response, dict) else {}
        usage = _openai_usage(response)
        return StreamEvent(
            provider="openai",
            event_type=event_type,
            input_tokens=_usage_int(usage.get("input_tokens")),
            output_tokens=_usage_int(usage.get("output_tokens")),
            model=str(response.get("model")) if response.get("model") else None,
            response_id=str(response.get("id")) if response.get("id") else None,
            raw_usage=usage,
            raw=value,
        )

    if event_type in {"response.output_text.delta", "response.refusal.delta"}:
        delta = value.get("delta")
        return StreamEvent(
            provider="openai",
            event_type=event_type,
            text_delta=delta if isinstance(delta, str) else "",
            raw=value,
        )

    if event_type == "response.completed":
        response = value.get("response")
        response = response if isinstance(response, dict) else {}
        usage = _openai_usage(response)
        return StreamEvent(
            provider="openai",
            event_type=event_type,
            text_snapshot=_openai_output_text(response),
            input_tokens=_usage_int(usage.get("input_tokens")),
            output_tokens=_usage_int(usage.get("output_tokens")),
            model=str(response.get("model")) if response.get("model") else None,
            response_id=str(response.get("id")) if response.get("id") else None,
            stop_reason=(
                str(response.get("status")) if response.get("status") else "completed"
            ),
            complete=True,
            raw_usage=usage,
            raw=value,
        )

    if event_type in {"response.failed", "response.incomplete"}:
        response = value.get("response")
        response = response if isinstance(response, dict) else {}
        usage = _openai_usage(response)
        details = response.get("error") or response.get("incomplete_details")
        if isinstance(details, dict):
            message_value = details.get("message") or details.get("reason") or details.get("code")
        else:
            message_value = details
        return StreamEvent(
            provider="openai",
            event_type=event_type,
            text_snapshot=_openai_output_text(response),
            input_tokens=_usage_int(usage.get("input_tokens")),
            output_tokens=_usage_int(usage.get("output_tokens")),
            model=str(response.get("model")) if response.get("model") else None,
            response_id=str(response.get("id")) if response.get("id") else None,
            stop_reason=str(response.get("status") or event_type),
            error=str(message_value or event_type),
            raw_usage=usage,
            raw=value,
        )

    if event_type == "error":
        error = value.get("error")
        if isinstance(error, dict):
            message_value = error.get("message") or error.get("code") or error.get("type")
        else:
            message_value = error
        return StreamEvent(
            provider="openai",
            event_type=event_type,
            error=str(message_value or "OpenAI stream error"),
            raw=value,
        )

    return StreamEvent(provider="openai", event_type=event_type, raw=value)


class AnthropicStreamingProvider:
    name = "anthropic"

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        artifact_root: str | Path = ".",
        max_tokens: int = 1024,
        timeout_seconds: float = 120.0,
        enable_cache: bool = True,
        api_url: str = ANTHROPIC_MESSAGES_URL,
        event_source: AsyncSSESource = urllib_sse_source,
    ) -> None:
        self.model = _required_text(model, "Anthropic model")
        self.api_key = _required_text(
            api_key or os.environ.get("ANTHROPIC_API_KEY"),
            "ANTHROPIC_API_KEY",
        )
        self.artifact_root = Path(artifact_root)
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.enable_cache = enable_cache
        self.api_url = _required_text(api_url, "Anthropic API URL")
        self.event_source = event_source
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

    async def stream(self, request: ProviderRequest) -> AsyncIterator[StreamEvent]:
        payload = build_anthropic_payload(
            request,
            model=self.model,
            max_tokens=self.max_tokens,
            artifact_root=self.artifact_root,
            enable_cache=self.enable_cache,
        )
        payload["stream"] = True
        headers = {
            "accept": "text/event-stream",
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        chunks = self.event_source(
            self.api_url,
            headers,
            _json_bytes(payload),
            self.timeout_seconds,
        )
        async for message in decode_sse(chunks):
            event = _anthropic_event(message)
            if event is not None:
                yield event


class OpenAIStreamingProvider:
    name = "openai"

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        artifact_root: str | Path = ".",
        max_tokens: int = 1024,
        timeout_seconds: float = 120.0,
        enable_cache: bool = True,
        prompt_cache_key: str | None = None,
        image_detail: str = "high",
        api_url: str = OPENAI_RESPONSES_URL,
        event_source: AsyncSSESource = urllib_sse_source,
    ) -> None:
        self.model = _required_text(model, "OpenAI model")
        self.api_key = _required_text(
            api_key or os.environ.get("OPENAI_API_KEY"),
            "OPENAI_API_KEY",
        )
        self.artifact_root = Path(artifact_root)
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.enable_cache = enable_cache
        self.prompt_cache_key = prompt_cache_key
        self.image_detail = image_detail
        self.api_url = _required_text(api_url, "OpenAI API URL")
        self.event_source = event_source
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

    async def stream(self, request: ProviderRequest) -> AsyncIterator[StreamEvent]:
        payload = build_openai_payload(
            request,
            model=self.model,
            max_tokens=self.max_tokens,
            artifact_root=self.artifact_root,
            enable_cache=self.enable_cache,
            prompt_cache_key=self.prompt_cache_key,
            image_detail=self.image_detail,
        )
        payload["stream"] = True
        headers = {
            "accept": "text/event-stream",
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }
        chunks = self.event_source(
            self.api_url,
            headers,
            _json_bytes(payload),
            self.timeout_seconds,
        )
        async for message in decode_sse(chunks):
            event = _openai_event(message)
            if event is not None:
                yield event


__all__ = [
    "ANTHROPIC_MESSAGES_URL",
    "OPENAI_RESPONSES_URL",
    "AnthropicStreamingProvider",
    "OpenAIStreamingProvider",
]
