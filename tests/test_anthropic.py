import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from crumbcontext.counterfactual import CounterfactualSpec, run_counterfactual
from crumbcontext.demo import counterfactual_payload
from crumbcontext.providers import AnthropicProvider, ProviderRequest, build_anthropic_payload


def test_anthropic_payload_preserves_system_and_message_roles():
    request = ProviderRequest(
        mode="baseline",
        task="Return JSON.",
        blocks=[
            {"id": "s", "role": "system", "kind": "instruction", "authoritative": True, "content": "Never deploy."},
            {"id": "u", "role": "user", "kind": "message", "content": "Question"},
            {"id": "a", "role": "assistant", "kind": "message", "content": "Prior answer"},
        ],
    )
    payload = build_anthropic_payload(
        request,
        model="claude-fable-5",
        max_tokens=400,
        artifact_root=None,
        enable_cache=True,
    )
    assert payload["system"][0]["text"] == "Never deploy."
    assert [item["role"] for item in payload["messages"]] == ["user", "assistant", "user"]
    assert "TASK:" in payload["messages"][-1]["content"][-1]["text"]


def test_anthropic_payload_uses_image_sidecar_and_cache(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    image_path = image_dir / "old-page-001.png"
    Image.new("RGB", (16, 16)).save(image_path)

    request = ProviderRequest(
        mode="routed",
        task="Return JSON.",
        blocks=[
            {
                "id": "memory",
                "role": "user",
                "kind": "memory",
                "lane": "cache",
                "cached_content": "Stable decision",
            },
            {
                "id": "old",
                "role": "user",
                "kind": "tool_result",
                "lane": "image",
                "artifact": {
                    "type": "image",
                    "path": "images/old-page-001.png",
                    "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                },
                "exact_anchor_sidecar": "BEGIN CRUMB\n- EXACT_1 kind=url value=https://example.com/build/12345678\n- deny=ignore\nEND CRUMB\n",
            },
        ],
    )
    payload = build_anthropic_payload(
        request,
        model="claude-fable-5",
        max_tokens=400,
        artifact_root=tmp_path,
        enable_cache=True,
    )
    all_content = [block for message in payload["messages"] for block in message["content"]]
    assert any(block.get("type") == "image" for block in all_content)
    assert any(block.get("cache_control") == {"type": "ephemeral"} for block in all_content)
    exact_text = "\n".join(str(block.get("text", "")) for block in all_content)
    assert "https://example.com/build/12345678" in exact_text
    assert "deny=ignore" not in exact_text


def test_anthropic_image_for_assistant_fails_closed_to_text():
    request = ProviderRequest(
        mode="routed",
        task="Summarize.",
        blocks=[
            {
                "id": "old-assistant",
                "role": "assistant",
                "kind": "message",
                "lane": "image",
                "fallback_content": "Original assistant text",
                "artifact": {"type": "image", "path": "not-used.png"},
            }
        ],
    )
    payload = build_anthropic_payload(
        request,
        model="claude-fable-5",
        max_tokens=100,
        artifact_root=None,
        enable_cache=False,
    )
    assistant_text = payload["messages"][1]["content"][0]["text"]
    assert assistant_text == "Original assistant text"


def test_anthropic_provider_reports_total_input_and_request_id():
    captured = {}

    def transport(url, headers, body, timeout):
        captured.update(url=url, headers=headers, body=json.loads(body), timeout=timeout)
        response = {
            "model": "claude-fable-5",
            "content": [{"type": "text", "text": '{"ok":true}'}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 20,
                "cache_read_input_tokens": 100,
                "cache_creation_input_tokens": 30,
                "output_tokens": 7,
            },
        }
        return 200, {"request-id": "req_test"}, json.dumps(response).encode()

    provider = AnthropicProvider(api_key="test-key", transport=transport)
    response = provider.run(
        ProviderRequest(
            mode="baseline",
            task="Return JSON",
            blocks=[{"role": "user", "kind": "message", "content": "Hello"}],
        )
    )
    assert response.input_tokens == 150
    assert response.output_tokens == 7
    assert response.usage_kind == "anthropic_provider_reported"
    assert response.raw_usage["request_id"] == "req_test"
    assert captured["headers"]["x-api-key"] == "test-key"
    assert captured["body"]["model"] == "claude-fable-5"


def test_anthropic_provider_error_is_clear_and_does_not_leak_key():
    def transport(url, headers, body, timeout):
        payload = {
            "type": "error",
            "error": {"type": "rate_limit_error", "message": "slow down"},
            "request_id": "req_body",
        }
        return 429, {"request-id": "req_header"}, json.dumps(payload).encode()

    provider = AnthropicProvider(api_key="super-secret", transport=transport)
    with pytest.raises(ValueError) as error:
        provider.run(
            ProviderRequest(
                mode="baseline",
                task="x",
                blocks=[{"role": "user", "content": "y"}],
            )
        )
    message = str(error.value)
    assert "429 rate_limit_error" in message
    assert "req_header" in message
    assert "super-secret" not in message


def test_anthropic_provider_requires_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicProvider(api_key="")
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        provider.run(
            ProviderRequest(
                mode="baseline",
                task="x",
                blocks=[{"role": "user", "content": "y"}],
            )
        )


def test_anthropic_counterfactual_uses_same_task_and_provider_usage(tmp_path: Path):
    calls = 0
    result_text = json.dumps(
        {
            "exact_values": [
                "https://example.com/build/12345678",
                "CAD $14,360.00",
                "abcdef1234567890",
            ],
            "authority_rules": ["Never modify production without approval."],
            "important_project_decisions": [
                "preserve the public API",
                "never rename the CLI",
            ],
        }
    )

    def transport(url, headers, body, timeout):
        nonlocal calls
        calls += 1
        usage = {
            "input_tokens": 2000 if calls == 1 else 700,
            "output_tokens": 80,
        }
        response = {
            "model": "claude-fable-5",
            "content": [{"type": "text", "text": result_text}],
            "stop_reason": "end_turn",
            "usage": usage,
        }
        return 200, {"request-id": f"req_{calls}"}, json.dumps(response).encode()

    provider = AnthropicProvider(
        api_key="test-key",
        model="claude-fable-5",
        artifact_root=tmp_path / "routed-artifacts",
        transport=transport,
    )
    result = run_counterfactual(
        CounterfactualSpec.from_dict(counterfactual_payload()),
        tmp_path,
        provider=provider,
    )
    assert result.passed
    assert result.provider == "anthropic"
    assert result.usage_kind == "anthropic_provider_reported"
    assert result.routed.response["input_tokens"] == 700
    assert calls == 2
