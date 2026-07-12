from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias

from .counterfactual_models import CounterfactualSpec, EvaluationSpec
from .counterfactual_payloads import baseline_request, routed_request
from .models import ContextBlock, RoutePlan
from .profiles import ResolvedProfile, custom_profile, resolve_profile
from .providers import Provider, ProviderRequest, ProviderResponse, get_provider
from .router import RouterConfig

BlockInput: TypeAlias = ContextBlock | Mapping[str, Any]


@dataclass(frozen=True)
class RoutedRequestBundle:
    """A provider-neutral routed request plus its inspectable routing artifacts."""

    request: ProviderRequest
    plan: RoutePlan
    artifact_root: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "plan": self.plan.to_dict(),
            "artifact_root": str(self.artifact_root),
        }


def normalize_blocks(blocks: Iterable[BlockInput]) -> tuple[ContextBlock, ...]:
    """Normalize mappings or ``ContextBlock`` objects and reject ambiguous IDs."""

    normalized: list[ContextBlock] = []
    seen_ids: set[str] = set()
    for index, value in enumerate(blocks):
        if isinstance(value, ContextBlock):
            block = value
        elif isinstance(value, Mapping):
            block = ContextBlock.from_dict(dict(value), index)
        else:
            raise TypeError(
                "context blocks must be ContextBlock objects or mapping objects; "
                f"received {type(value).__name__} at index {index}"
            )
        if not block.id.strip():
            raise ValueError(f"context block at index {index} has an empty id")
        if block.id in seen_ids:
            raise ValueError(f"duplicate context block id: {block.id!r}")
        seen_ids.add(block.id)
        normalized.append(block)
    if not normalized:
        raise ValueError("at least one context block is required")
    return tuple(normalized)


def create_spec(
    task: str,
    blocks: Iterable[BlockInput],
    *,
    name: str = "request",
    evaluation: EvaluationSpec | Mapping[str, Any] | None = None,
) -> CounterfactualSpec:
    """Create a validated provider-neutral task specification."""

    if not isinstance(task, str) or not task.strip():
        raise ValueError("task must be non-empty text")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be non-empty text")
    if evaluation is None:
        resolved_evaluation = EvaluationSpec()
    elif isinstance(evaluation, EvaluationSpec):
        resolved_evaluation = evaluation
    elif isinstance(evaluation, Mapping):
        resolved_evaluation = EvaluationSpec.from_dict(dict(evaluation))
    else:
        raise TypeError("evaluation must be EvaluationSpec, a mapping, or None")
    return CounterfactualSpec(
        task=task,
        blocks=normalize_blocks(blocks),
        evaluation=resolved_evaluation,
        name=name,
    )


def build_baseline_request(
    task: str,
    blocks: Iterable[BlockInput],
    *,
    name: str = "request",
    evaluation: EvaluationSpec | Mapping[str, Any] | None = None,
) -> ProviderRequest:
    """Build the complete uncompressed provider-neutral request."""

    return baseline_request(
        create_spec(task, blocks, name=name, evaluation=evaluation)
    )


def _resolve_routing_policy(
    config: RouterConfig | None,
    profile: str | None,
    config_overrides: Mapping[str, Any] | None,
) -> ResolvedProfile:
    if config is not None:
        if profile is not None or config_overrides:
            raise ValueError(
                "use either an explicit RouterConfig or a named profile with overrides, not both"
            )
        return custom_profile(config)
    return resolve_profile(profile or "safe-default", config_overrides)


def build_routed_request(
    task: str,
    blocks: Iterable[BlockInput],
    output_dir: str | Path,
    *,
    config: RouterConfig | None = None,
    profile: str | None = None,
    config_overrides: Mapping[str, Any] | None = None,
    name: str = "request",
    evaluation: EvaluationSpec | Mapping[str, Any] | None = None,
) -> RoutedRequestBundle:
    """Route context and build a provider-neutral request with inspectable artifacts."""

    policy = _resolve_routing_policy(config, profile, config_overrides)
    artifact_root = Path(output_dir)
    request, plan = routed_request(
        create_spec(task, blocks, name=name, evaluation=evaluation),
        artifact_root,
        policy.config,
        profile_name=policy.name,
    )
    return RoutedRequestBundle(
        request=request,
        plan=plan,
        artifact_root=artifact_root,
    )


def execute_provider(
    request: ProviderRequest,
    provider: str | Provider = "mock",
    *,
    provider_options: Mapping[str, Any] | None = None,
) -> ProviderResponse:
    """Execute one canonical request through a named or injected provider."""

    options = dict(provider_options or {})
    if isinstance(provider, str):
        resolved = get_provider(provider, **options)
    else:
        if options:
            raise ValueError(
                "provider_options cannot be used with an injected provider instance"
            )
        resolved = provider
    return resolved.run(request)


__all__ = [
    "BlockInput",
    "RoutedRequestBundle",
    "build_baseline_request",
    "build_routed_request",
    "create_spec",
    "execute_provider",
    "normalize_blocks",
]
