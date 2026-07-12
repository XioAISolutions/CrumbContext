from __future__ import annotations

import json
from pathlib import Path

import pytest

from crumbcontext.evidence import (
    EvidenceError,
    load_report,
    render_summary,
    scan_for_secret_leaks,
    validate_provider_report,
)
from crumbcontext.schemas import COUNTERFACTUAL_RESULT_SCHEMA, SchemaError


def valid_report(*, versioned: bool = True) -> dict:
    response = {
        "input_tokens": 100,
        "output_tokens": 20,
        "total_tokens": 120,
    }
    evaluation = {
        "json_valid": True,
        "exact_expected": 3,
        "exact_found": 3,
        "exact_recall": 1.0,
        "required_expected": 2,
        "required_found": 2,
        "required_recall": 1.0,
        "task_complete": True,
    }
    run = {
        "request_sha256": "a" * 64,
        "response_sha256": "b" * 64,
        "request": {},
        "response": response,
        "evaluation": evaluation,
    }
    plan = {}
    report = {
        "passed": True,
        "provider": "openai",
        "model": "model-version",
        "usage_kind": "provider_reported",
        "task_sha256": "c" * 64,
        "source_sha256": "d" * 64,
        "baseline": run,
        "routed": run,
        "comparison": {
            "input_token_reduction_percent": 25.0,
            "total_token_reduction_percent": 20.0,
            "latency_delta_ms": -10.0,
            "response_similarity": 0.95,
            "same_task": True,
        },
        "plan": plan,
        "disclaimer": "fixture-specific evidence",
    }
    if versioned:
        report["schema_version"] = COUNTERFACTUAL_RESULT_SCHEMA
        report["redaction"] = {
            "response_bodies": True,
            "hashes_and_evaluation_preserved": True,
        }
        plan.update(
            {
                "schema_version": "crumbcontext.route-plan.v1",
                "routing": {
                    "profile": "text-only",
                    "config": {"vision_allowed": False},
                },
            }
        )
    return report


def test_valid_provider_report_and_summary():
    report = valid_report()
    validate_provider_report(report, "openai")
    summary = render_summary(report, "openai", "model-version")
    assert "Evidence schema: `crumbcontext.counterfactual-result.v1`" in summary
    assert "Routing profile: `text-only`" in summary
    assert "Saved response bodies redacted: `True`" in summary
    assert "Input-token reduction: 25.0%" in summary
    assert "Exact recall: 3/3" in summary
    assert "Response similarity: 95.0%" in summary


def test_legacy_v01_provider_report_remains_readable(tmp_path: Path):
    report = valid_report(versioned=False)
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    loaded = load_report(path)
    validate_provider_report(loaded, "openai")
    summary = render_summary(loaded, "openai", "model-version")
    assert "legacy-v0.1-without-schema" in summary
    assert "legacy-unspecified" in summary


def test_unknown_explicit_schema_is_rejected(tmp_path: Path):
    report = valid_report()
    report["schema_version"] = "crumbcontext.counterfactual-result.v99"
    path = tmp_path / "unknown.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(SchemaError, match="unsupported schema_version"):
        load_report(path)


def test_rejects_mock_accounting():
    report = valid_report()
    report["usage_kind"] = "mock_simulated_not_billed"
    with pytest.raises(EvidenceError, match="simulated"):
        validate_provider_report(report, "openai")


def test_rejects_incomplete_exact_recall():
    report = valid_report()
    report["routed"]["evaluation"]["exact_found"] = 2
    with pytest.raises(EvidenceError, match="exact recall is incomplete"):
        validate_provider_report(report, "openai")


def test_rejects_wrong_provider():
    with pytest.raises(EvidenceError, match="does not match"):
        validate_provider_report(valid_report(), "anthropic")


def test_versioned_plan_requires_profile_and_config():
    report = valid_report()
    report["plan"]["routing"] = {}
    with pytest.raises(EvidenceError, match="missing a profile name"):
        validate_provider_report(report, "openai")


def test_secret_scan_rejects_leak(tmp_path: Path):
    (tmp_path / "counterfactual.json").write_text(
        '{"token":"super-secret-key"}', encoding="utf-8"
    )
    with pytest.raises(EvidenceError, match="credential leakage"):
        scan_for_secret_leaks(tmp_path, ["super-secret-key"])


def test_secret_scan_accepts_clean_bundle(tmp_path: Path):
    (tmp_path / "counterfactual.json").write_text("{}", encoding="utf-8")
    scan_for_secret_leaks(tmp_path, ["super-secret-key"])
