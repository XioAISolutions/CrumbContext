from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from . import _workloads_impl as _impl
from .profiles import available_profiles
from .schemas import (
    WORKLOAD_MANIFEST_SCHEMA,
    WORKLOAD_RESULT_SCHEMA,
    WORKLOAD_SUITE_RESULT_SCHEMA,
)

DEFAULT_MANIFEST = _impl.DEFAULT_MANIFEST
DEFAULT_PROFILES = _impl.DEFAULT_PROFILES
DISCLAIMER = _impl.DISCLAIMER
WorkloadManifest = _impl.WorkloadManifest
WorkloadSpec = _impl.WorkloadSpec
load_workload_manifest = _impl.load_workload_manifest

# These names are the stable v1 evidence contract enforced by release-check.py.
WORKLOAD_RESULT_CHECKS = (
    "all_exact_anchors_preserved",
    "authority_blocks_stay_exact",
    "deterministic_plan",
)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _upgrade_result_contract(root: Path, suite: dict[str, Any]) -> dict[str, Any]:
    runs = list(suite.get("runs", ()))
    workload_metadata = {
        item["id"]: item for item in suite.get("manifest", {}).get("workloads", ())
    }

    for run in runs:
        planning = run["planning"]
        exact = run["exact_anchors"]
        lanes = dict(run.get("lanes", {}))
        metadata = workload_metadata.get(run["workload_id"], {})
        plan_path = root / run["artifacts"]["plan"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))

        run.update(
            {
                "license": metadata.get("license"),
                "provenance": metadata.get("provenance"),
                "estimated_text_tokens": planning["baseline_estimated_tokens"],
                "estimated_routed_tokens": planning["routed_estimated_tokens"],
                "estimated_reduction_percent": planning[
                    "estimated_token_reduction_percent"
                ],
                "exact_anchors_preserved": exact["found"],
                "exact_anchors_expected": exact["expected"],
                "lane_counts": lanes,
                "plan": plan,
                "artifact_root": run["artifacts"]["root"],
            }
        )
        result_path = (
            root
            / "results"
            / f"{run['workload_id']}--{run['profile']}.json"
        )
        _write_json(result_path, run)

    summary = suite["summary"]
    exact = summary["exact_anchors"]
    lanes = dict(summary.get("lanes", {}))
    selected = tuple(suite.get("profiles", ()))
    checks = {
        "complete_matrix": len(runs)
        == summary["workloads"] * summary["profiles"],
        "all_runs_pass": all(run["passed"] for run in runs),
        "all_exact_anchors_preserved": exact["found"] == exact["expected"],
        "required_lane_coverage": (
            {"exact", "cache", "crumb", "image", "summary"} <= set(lanes)
            if set(DEFAULT_PROFILES).issubset(selected)
            else True
        ),
    }
    summary.update(
        {
            "exact_anchors_preserved": exact["found"],
            "exact_anchors_expected": exact["expected"],
            "lane_counts": lanes,
        }
    )
    suite.update(
        {
            "passed": all(checks.values()),
            "checks": checks,
            "results": runs,
            "runs": runs,
        }
    )
    _write_json(root / "suite.json", suite)
    return suite


def run_workload_suite(
    output_dir: str | Path,
    *,
    manifest_path: str | Path | None = None,
    profiles: Sequence[str] | None = None,
) -> dict[str, Any]:
    selected = tuple(profiles) if profiles is not None else DEFAULT_PROFILES
    unknown = sorted(set(selected) - set(available_profiles()))
    if unknown:
        raise ValueError(
            f"unknown workload-suite profiles: {', '.join(unknown)}"
        )

    # The implementation predates the stable RoutePlan property names. These aliases keep
    # its deterministic planning math intact without changing the serialized route plan.
    route_plan = _impl.RoutePlan
    if not hasattr(route_plan, "baseline_estimated_tokens"):
        route_plan.baseline_estimated_tokens = property(  # type: ignore[attr-defined]
            lambda self: self.estimated_text_tokens
        )
    if not hasattr(route_plan, "routed_estimated_tokens"):
        route_plan.routed_estimated_tokens = property(  # type: ignore[attr-defined]
            lambda self: self.estimated_routed_tokens
        )
    if not hasattr(route_plan, "estimated_token_reduction_percent"):
        route_plan.estimated_token_reduction_percent = property(  # type: ignore[attr-defined]
            lambda self: self.reduction_percent
        )

    root = Path(output_dir)
    suite = _impl.run_workload_suite(
        output_dir=root,
        manifest_path=manifest_path,
        profiles=selected,
    )
    return _upgrade_result_contract(root, suite)


def __getattr__(name: str) -> Any:
    return getattr(_impl, name)


__all__ = [
    "DEFAULT_MANIFEST",
    "DEFAULT_PROFILES",
    "DISCLAIMER",
    "WORKLOAD_MANIFEST_SCHEMA",
    "WORKLOAD_RESULT_SCHEMA",
    "WORKLOAD_SUITE_RESULT_SCHEMA",
    "WORKLOAD_RESULT_CHECKS",
    "WorkloadManifest",
    "WorkloadSpec",
    "load_workload_manifest",
    "run_workload_suite",
]
