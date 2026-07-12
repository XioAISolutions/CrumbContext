from __future__ import annotations

import json
from pathlib import Path

from crumbcontext import (
    COUNTERFACTUAL_RESULT_SCHEMA,
    ROUTE_PLAN_SCHEMA,
    RouterConfig,
    create_spec,
    run_counterfactual,
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
        "id": "history",
        "role": "user",
        "kind": "memory",
        "content": (
            "Decision: keep response evidence inspectable. "
            "The exact SHA is abcdef1234567890abcdef1234567890. "
        )
        * 80,
        "age_turns": 12,
    },
    {
        "id": "current",
        "role": "user",
        "kind": "message",
        "content": "Return the decision and exact SHA.",
        "age_turns": 0,
    },
]


def spec():
    return create_spec(
        "Return JSON containing the decision and exact SHA.",
        BLOCKS,
        name="redaction-test",
        evaluation={
            "expected_exact": ["abcdef1234567890abcdef1234567890"],
            "required_substrings": ["decision"],
            "expect_json": True,
        },
    )


def test_redacted_counterfactual_preserves_hashes_usage_and_evaluation(tmp_path: Path):
    out = tmp_path / "redacted"
    result = run_counterfactual(
        spec(),
        out,
        provider="mock",
        config=RouterConfig(vision_allowed=False),
        profile_name="text-only",
        redact_responses=True,
    )
    assert result.passed
    original_baseline_text = result.baseline.response["text"]
    original_routed_text = result.routed.response["text"]
    assert original_baseline_text
    assert original_routed_text

    saved = json.loads((out / "counterfactual.json").read_text(encoding="utf-8"))
    assert saved["schema_version"] == COUNTERFACTUAL_RESULT_SCHEMA
    assert saved["plan"]["schema_version"] == ROUTE_PLAN_SCHEMA
    assert saved["plan"]["routing"]["profile"] == "text-only"
    assert saved["redaction"] == {
        "response_bodies": True,
        "hashes_and_evaluation_preserved": True,
    }
    assert saved["baseline"]["response"]["text_redacted"] is True
    assert saved["routed"]["response"]["text_redacted"] is True
    assert saved["baseline"]["request_sha256"] == result.baseline.request_sha256
    assert saved["routed"]["response_sha256"] == result.routed.response_sha256
    assert saved["routed"]["evaluation"]["exact_recall"] == 1.0
    assert saved["routed"]["response"]["input_tokens"] >= 0

    for name in (
        "counterfactual.json",
        "baseline-response.json",
        "routed-response.json",
        "counterfactual.html",
    ):
        payload = (out / name).read_text(encoding="utf-8")
        assert original_baseline_text not in payload
        assert original_routed_text not in payload
        assert "REDACTED: response body omitted by policy" in payload


def test_unredacted_counterfactual_keeps_response_bodies(tmp_path: Path):
    out = tmp_path / "raw"
    result = run_counterfactual(
        spec(),
        out,
        provider="mock",
        config=RouterConfig(vision_allowed=False),
        profile_name="text-only",
    )
    assert result.passed
    saved = json.loads((out / "counterfactual.json").read_text(encoding="utf-8"))
    assert saved["redaction"]["response_bodies"] is False
    assert saved["baseline"]["response"]["text"] == result.baseline.response["text"]
    assert saved["routed"]["response"]["text"] == result.routed.response["text"]
    assert "text_redacted" not in saved["baseline"]["response"]
