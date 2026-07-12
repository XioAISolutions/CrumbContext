from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .models import ContextBlock


@dataclass(frozen=True)
class EvaluationSpec:
    expected_exact: tuple[str, ...] = ()
    required_substrings: tuple[str, ...] = ()
    expect_json: bool = True

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "EvaluationSpec":
        value = value or {}
        return cls(
            expected_exact=tuple(str(item) for item in value.get("expected_exact", [])),
            required_substrings=tuple(
                str(item) for item in value.get("required_substrings", [])
            ),
            expect_json=bool(value.get("expect_json", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CounterfactualSpec:
    task: str
    blocks: tuple[ContextBlock, ...]
    evaluation: EvaluationSpec = field(default_factory=EvaluationSpec)
    name: str = "counterfactual"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CounterfactualSpec":
        blocks_raw = value.get("blocks")
        if not isinstance(blocks_raw, list) or not blocks_raw:
            raise ValueError("counterfactual input requires a non-empty 'blocks' array")
        task = str(value.get("task") or "").strip()
        if not task:
            raise ValueError("counterfactual input requires a non-empty 'task'")
        return cls(
            name=str(value.get("name") or "counterfactual"),
            task=task,
            blocks=tuple(
                ContextBlock.from_dict(item, index)
                for index, item in enumerate(blocks_raw)
            ),
            evaluation=EvaluationSpec.from_dict(value.get("evaluation")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "task": self.task,
            "blocks": [asdict(block) for block in self.blocks],
            "evaluation": self.evaluation.to_dict(),
        }


@dataclass(frozen=True)
class ResponseEvaluation:
    json_valid: bool
    exact_expected: int
    exact_found: int
    exact_recall: float
    required_expected: int
    required_found: int
    required_recall: float
    task_complete: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunRecord:
    request_sha256: str
    response_sha256: str
    request: dict[str, Any]
    response: dict[str, Any]
    evaluation: ResponseEvaluation

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_sha256": self.request_sha256,
            "response_sha256": self.response_sha256,
            "request": self.request,
            "response": self.response,
            "evaluation": self.evaluation.to_dict(),
        }


@dataclass(frozen=True)
class CounterfactualResult:
    passed: bool
    provider: str
    model: str
    usage_kind: str
    task_sha256: str
    source_sha256: str
    baseline: RunRecord
    routed: RunRecord
    input_token_reduction_percent: float
    total_token_reduction_percent: float
    latency_delta_ms: float
    response_similarity: float
    same_task: bool
    plan: dict[str, Any]
    disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "provider": self.provider,
            "model": self.model,
            "usage_kind": self.usage_kind,
            "task_sha256": self.task_sha256,
            "source_sha256": self.source_sha256,
            "baseline": self.baseline.to_dict(),
            "routed": self.routed.to_dict(),
            "comparison": {
                "input_token_reduction_percent": self.input_token_reduction_percent,
                "total_token_reduction_percent": self.total_token_reduction_percent,
                "latency_delta_ms": self.latency_delta_ms,
                "response_similarity": self.response_similarity,
                "same_task": self.same_task,
            },
            "plan": self.plan,
            "disclaimer": self.disclaimer,
        }
