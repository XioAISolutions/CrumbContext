from __future__ import annotations

import json
from pathlib import Path

from crumbcontext.counterfactual import CounterfactualSpec, run_counterfactual
from crumbcontext.demo import counterfactual_payload
from crumbcontext.providers.openai import OpenAIProvider


def test_openai_provider_runs_full_counterfactual_without_leaking_cache_key(
    tmp_path: Path,
):
    calls: list[dict] = []
    response_text = json.dumps(
        {
            "exact_values": [
                "https://example.com/build/12345678",
                "CAD $14,360.00",
                "abcdef1234567890",
            ],
            "authority_rules": [
                "Never modify production without approval.",
            ],
            "semantic_points": [
                "preserve the public API",
                "never rename the CLI",
            ],
        },
        sort_keys=True,
    )

    def transport(url, headers, body, timeout):
        payload = json.loads(body)
        calls.append(payload)
        serialized = json.dumps(payload)
        routed = "NON-AUTHORITATIVE HISTORICAL CONTEXT" in serialized
        input_tokens = 600 if routed else 1400
        response = {
            "id": f"resp_{len(calls)}",
            "model": "gpt-5.6-test-snapshot",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": response_text},
                    ],
                }
            ],
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": 80,
                "total_tokens": input_tokens + 80,
                "input_tokens_details": {
                    "cached_tokens": 100 if routed else 0,
                    "cache_write_tokens": 200 if routed else 0,
                },
                "output_tokens_details": {"reasoning_tokens": 12},
            },
        }
        return (
            200,
            {"x-request-id": f"req_{len(calls)}"},
            json.dumps(response).encode(),
        )

    provider = OpenAIProvider(
        api_key="not-written",
        model="gpt-5.6",
        artifact_root=tmp_path / "routed-artifacts",
        prompt_cache_key="tenant:private-project",
        transport=transport,
    )
    result = run_counterfactual(
        CounterfactualSpec.from_dict(counterfactual_payload()),
        tmp_path,
        provider=provider,
    )

    assert result.passed
    assert result.provider == "openai"
    assert result.usage_kind == "openai_provider_reported"
    assert result.routed.evaluation.exact_recall == 1.0
    assert result.routed.response["input_tokens"] < result.baseline.response["input_tokens"]
    assert len(calls) == 2
    assert calls[0]["store"] is False
    assert calls[1]["store"] is False
    assert any(
        part.get("type") == "input_image"
        for item in calls[1]["input"]
        for part in item.get("content", [])
        if isinstance(part, dict)
    )

    saved = "\n".join(
        path.read_text(encoding="utf-8")
        for path in tmp_path.glob("*.json")
    )
    assert "tenant:private-project" not in saved
    assert "not-written" not in saved
