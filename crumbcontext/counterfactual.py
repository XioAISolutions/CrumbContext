from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .counterfactual_evaluation import record_run, reduction, similarity
from .counterfactual_models import CounterfactualResult, CounterfactualSpec
from .counterfactual_payloads import (
    all_exact_values,
    baseline_request,
    canonical_json,
    routed_request,
    sha256_text,
)
from .counterfactual_report import (
    write_counterfactual_card,
    write_counterfactual_report,
)
from .providers import Provider, get_provider
from .router import RouterConfig


def run_counterfactual(
    spec: CounterfactualSpec,
    output_dir: Path,
    provider: Provider | str = "mock",
    config: RouterConfig | None = None,
    provider_options: dict[str, Any] | None = None,
) -> CounterfactualResult:
    """Run the same task against baseline and routed context payloads."""

    resolved_config = config or RouterConfig()
    output_dir.mkdir(parents=True, exist_ok=True)
    routed_artifact_root = output_dir / "routed-artifacts"
    options = dict(provider_options or {})
    if isinstance(provider, str):
        if provider.strip().lower() in {"anthropic", "openai"}:
            options.setdefault("artifact_root", routed_artifact_root)
        resolved_provider = get_provider(provider, **options)
    else:
        if options:
            raise ValueError("provider_options cannot be used with a provider instance")
        resolved_provider = provider

    baseline_req = baseline_request(spec)
    routed_req, plan = routed_request(spec, routed_artifact_root, resolved_config)
    baseline_response = resolved_provider.run(baseline_req)
    routed_response = resolved_provider.run(routed_req)
    expected = all_exact_values(spec.blocks)
    baseline = record_run(
        baseline_req,
        baseline_response,
        spec.evaluation,
        expected,
    )
    routed = record_run(
        routed_req,
        routed_response,
        spec.evaluation,
        expected,
    )
    same_task = baseline_req.task == routed_req.task == spec.task
    result = CounterfactualResult(
        passed=(
            same_task
            and baseline.evaluation.task_complete
            and routed.evaluation.task_complete
            and routed.evaluation.exact_recall == 1.0
            and routed_response.input_tokens <= baseline_response.input_tokens
        ),
        provider=baseline_response.provider,
        model=baseline_response.model,
        usage_kind=baseline_response.usage_kind,
        task_sha256=sha256_text(spec.task),
        source_sha256=sha256_text(canonical_json(spec.to_dict())),
        baseline=baseline,
        routed=routed,
        input_token_reduction_percent=reduction(
            baseline_response.input_tokens,
            routed_response.input_tokens,
        ),
        total_token_reduction_percent=reduction(
            baseline_response.total_tokens,
            routed_response.total_tokens,
        ),
        latency_delta_ms=round(
            routed_response.latency_ms - baseline_response.latency_ms,
            3,
        ),
        response_similarity=similarity(
            baseline_response.text,
            routed_response.text,
        ),
        same_task=same_task,
        plan=plan.to_dict(),
        disclaimer=(
            "Mock usage is simulated. Anthropic and OpenAI usage is provider-reported, "
            "including cache details when the provider returns them. A single synthetic "
            "task is still not a universal cost or quality claim; publish the model, "
            "fixture, request hashes, routing policy, and evaluation results."
        ),
    )
    _write_outputs(
        output_dir,
        spec,
        baseline_req,
        routed_req,
        baseline_response.to_dict(),
        routed_response.to_dict(),
        result,
    )
    return result


def _write_outputs(
    output_dir: Path,
    spec: CounterfactualSpec,
    baseline_request_value,
    routed_request_value,
    baseline_response: dict,
    routed_response: dict,
    result: CounterfactualResult,
) -> None:
    values = {
        "counterfactual-input.json": spec.to_dict(),
        "baseline-request.json": baseline_request_value.to_dict(),
        "routed-request.json": routed_request_value.to_dict(),
        "baseline-response.json": baseline_response,
        "routed-response.json": routed_response,
        "counterfactual.json": result.to_dict(),
    }
    for name, value in values.items():
        (output_dir / name).write_text(
            json.dumps(value, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    write_counterfactual_report(result, output_dir / "counterfactual.html")
    write_counterfactual_card(result, output_dir / "counterfactual-card.svg")


def load_counterfactual_spec(path: Path) -> CounterfactualSpec:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("counterfactual input must be a JSON object")
    return CounterfactualSpec.from_dict(raw)
