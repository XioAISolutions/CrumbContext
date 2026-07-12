from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

from .schemas import COUNTERFACTUAL_RESULT_SCHEMA, SchemaError, require_schema


class EvidenceError(ValueError):
    """Raised when a provider evidence bundle violates the publication contract."""


def load_report(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EvidenceError("counterfactual report must be a JSON object")
    require_schema(
        value,
        COUNTERFACTUAL_RESULT_SCHEMA,
        allow_legacy_missing=True,
    )
    return value


def validate_provider_report(report: dict[str, Any], expected_provider: str) -> None:
    require_schema(
        report,
        COUNTERFACTUAL_RESULT_SCHEMA,
        allow_legacy_missing=True,
    )
    provider = str(report.get("provider") or "").strip().lower()
    if provider != expected_provider.strip().lower():
        raise EvidenceError(
            f"reported provider {provider!r} does not match requested provider "
            f"{expected_provider!r}"
        )
    if report.get("passed") is not True:
        raise EvidenceError("counterfactual result did not pass")
    model = report.get("model")
    if not isinstance(model, str) or not model.strip():
        raise EvidenceError("provider report is missing a model identifier")
    if report.get("usage_kind") == "mock_simulated_not_billed":
        raise EvidenceError("provider benchmark cannot use simulated mock accounting")

    routed = _mapping(report, "routed")
    evaluation = _mapping(routed, "evaluation")
    _require_equal_counts(evaluation, "exact_found", "exact_expected", "exact recall")
    _require_equal_counts(
        evaluation,
        "required_found",
        "required_expected",
        "required-rule recall",
    )
    if evaluation.get("task_complete") is not True:
        raise EvidenceError("routed response did not complete the task")

    comparison = _mapping(report, "comparison")
    for key in (
        "input_token_reduction_percent",
        "total_token_reduction_percent",
        "latency_delta_ms",
        "response_similarity",
    ):
        if not isinstance(comparison.get(key), (int, float)):
            raise EvidenceError(f"comparison is missing numeric {key}")

    plan = _mapping(report, "plan")
    if plan.get("schema_version") is not None:
        routing = _mapping(plan, "routing")
        profile = routing.get("profile")
        config = routing.get("config")
        if not isinstance(profile, str) or not profile.strip():
            raise EvidenceError("versioned routing plan is missing a profile name")
        if not isinstance(config, dict):
            raise EvidenceError("versioned routing plan is missing resolved config")

    for key in ("task_sha256", "source_sha256"):
        _require_sha256(report.get(key), key)
    for run_name in ("baseline", "routed"):
        run = _mapping(report, run_name)
        _require_sha256(run.get("request_sha256"), f"{run_name}.request_sha256")
        _require_sha256(run.get("response_sha256"), f"{run_name}.response_sha256")
        response = _mapping(run, "response")
        for token_key in ("input_tokens", "output_tokens", "total_tokens"):
            value = response.get(token_key)
            if not isinstance(value, int) or value < 0:
                raise EvidenceError(
                    f"{run_name}.response.{token_key} must be a non-negative integer"
                )


def scan_for_secret_leaks(root: Path, secrets: Iterable[str]) -> None:
    encoded = [value.encode() for value in secrets if value]
    if not root.is_dir():
        raise EvidenceError(f"artifact root does not exist: {root}")
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        payload = path.read_bytes()
        for secret in encoded:
            if secret in payload:
                raise EvidenceError(f"credential leakage detected in {path}")


def render_summary(
    report: dict[str, Any],
    requested_provider: str,
    requested_model: str,
) -> str:
    baseline = _mapping(report, "baseline")
    routed = _mapping(report, "routed")
    baseline_response = _mapping(baseline, "response")
    routed_response = _mapping(routed, "response")
    evaluation = _mapping(routed, "evaluation")
    comparison = _mapping(report, "comparison")
    plan = _mapping(report, "plan")
    routing = plan.get("routing") if isinstance(plan.get("routing"), dict) else {}
    redaction = (
        report.get("redaction")
        if isinstance(report.get("redaction"), dict)
        else {}
    )
    schema = report.get("schema_version") or "legacy-v0.1-without-schema"
    profile = routing.get("profile") or "legacy-unspecified"
    lines = [
        "# CrumbContext provider benchmark",
        "",
        f"- Evidence schema: `{schema}`",
        f"- Routing profile: `{profile}`",
        f"- Saved response bodies redacted: `{bool(redaction.get('response_bodies'))}`",
        f"- Requested provider/model: `{requested_provider}` / `{requested_model}`",
        f"- Reported provider/model: `{report['provider']}` / `{report['model']}`",
        f"- Usage kind: `{report['usage_kind']}`",
        f"- Task SHA-256: `{report['task_sha256']}`",
        f"- Source SHA-256: `{report['source_sha256']}`",
        f"- Baseline request SHA-256: `{baseline['request_sha256']}`",
        f"- Routed request SHA-256: `{routed['request_sha256']}`",
        f"- Baseline input tokens: {baseline_response['input_tokens']:,}",
        f"- Routed input tokens: {routed_response['input_tokens']:,}",
        (
            "- Input-token reduction: "
            f"{comparison['input_token_reduction_percent']}%"
        ),
        (
            "- Exact recall: "
            f"{evaluation['exact_found']}/{evaluation['exact_expected']}"
        ),
        (
            "- Required-rule recall: "
            f"{evaluation['required_found']}/{evaluation['required_expected']}"
        ),
        (
            "- Response similarity: "
            f"{comparison['response_similarity'] * 100:.1f}%"
        ),
        f"- Passed: `{report['passed']}`",
        "",
    ]
    return "\n".join(lines)


def _mapping(value: dict[str, Any], key: str) -> dict[str, Any]:
    item = value.get(key)
    if not isinstance(item, dict):
        raise EvidenceError(f"report is missing object {key}")
    return item


def _require_equal_counts(
    value: dict[str, Any],
    found_key: str,
    expected_key: str,
    label: str,
) -> None:
    found = value.get(found_key)
    expected = value.get(expected_key)
    if not isinstance(found, int) or not isinstance(expected, int):
        raise EvidenceError(f"{label} counts must be integers")
    if found != expected:
        raise EvidenceError(f"{label} is incomplete: {found}/{expected}")


def _require_sha256(value: Any, label: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise EvidenceError(f"{label} must be a SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise EvidenceError(f"{label} must be hexadecimal") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a provider-measured CrumbContext evidence bundle."
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--requested-model", required=True)
    parser.add_argument("--summary", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = load_report(args.report)
        validate_provider_report(report, args.provider)
        scan_for_secret_leaks(
            args.artifact_root,
            (
                os.environ.get("ANTHROPIC_API_KEY", ""),
                os.environ.get("OPENAI_API_KEY", ""),
            ),
        )
        summary = render_summary(report, args.provider, args.requested_model)
        if args.summary:
            with args.summary.open("a", encoding="utf-8") as handle:
                handle.write(summary)
        else:
            print(summary, end="")
    except (OSError, json.JSONDecodeError, EvidenceError, SchemaError) as exc:
        print(f"provider evidence rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
