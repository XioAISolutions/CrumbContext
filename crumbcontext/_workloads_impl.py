from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from xml.sax.saxutils import escape

from .anchors import extract_anchors, unique_anchors
from .bundle import route_to_directory
from .models import ContextBlock, Lane, RoutePlan
from .profiles import available_profiles, resolve_profile
from .router import route_blocks
from .schemas import (
    WORKLOAD_MANIFEST_SCHEMA,
    WORKLOAD_RESULT_SCHEMA,
    WORKLOAD_SUITE_RESULT_SCHEMA,
    require_schema,
)

DEFAULT_PROFILES = tuple(
    name for name in available_profiles() if name != "frontier-vision"
)
DEFAULT_MANIFEST = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "workloads"
    / "v1"
    / "manifest.json"
)
_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_MAX_WORKLOADS = 100
_MAX_BLOCKS_PER_WORKLOAD = 500
_MAX_EXPANDED_BLOCK_CHARS = 2_000_000
DISCLAIMER = (
    "Token figures are deterministic routing estimates for these public synthetic "
    "fixtures. They are not provider billing records, model-quality scores, or "
    "universal savings claims."
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _string_list(value: Any, label: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array of strings")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_required_text(item, f"{label}[{index}]"))
    if not allow_empty and not result:
        raise ValueError(f"{label} must not be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{label} must not contain duplicates")
    return tuple(result)


def _expand_segments(value: Any, label: str) -> str:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty array")
    chunks: list[str] = []
    for index, segment in enumerate(value):
        if not isinstance(segment, dict):
            raise ValueError(f"{label}[{index}] must be an object")
        text = _required_text(segment.get("text"), f"{label}[{index}].text")
        repeat = segment.get("repeat", 1)
        if not isinstance(repeat, int) or isinstance(repeat, bool) or not 1 <= repeat <= 500:
            raise ValueError(f"{label}[{index}].repeat must be an integer from 1 to 500")
        for occurrence in range(1, repeat + 1):
            chunks.append(text.replace("{index}", str(occurrence)))
    expanded = "\n".join(chunks)
    if len(expanded) > _MAX_EXPANDED_BLOCK_CHARS:
        raise ValueError(
            f"{label} expands beyond {_MAX_EXPANDED_BLOCK_CHARS:,} characters"
        )
    return expanded


def _expand_block(value: Any, index: int, workload_id: str) -> ContextBlock:
    if not isinstance(value, dict):
        raise ValueError(f"workload {workload_id!r} block {index} must be an object")
    has_content = "content" in value
    has_segments = "segments" in value
    if has_content == has_segments:
        raise ValueError(
            f"workload {workload_id!r} block {index} must declare exactly one of "
            "content or segments"
        )
    content = (
        _required_text(value.get("content"), f"workload {workload_id} block {index}.content")
        if has_content
        else _expand_segments(
            value.get("segments"),
            f"workload {workload_id} block {index}.segments",
        )
    )
    normalized = dict(value)
    normalized.pop("segments", None)
    normalized["content"] = content
    block = ContextBlock.from_dict(normalized, index=index)
    if not _ID.fullmatch(block.id):
        raise ValueError(
            f"workload {workload_id!r} block id {block.id!r} must match {_ID.pattern}"
        )
    return block


def _block_to_dict(block: ContextBlock) -> dict[str, Any]:
    value = asdict(block)
    if not value["metadata"]:
        value.pop("metadata")
    return value


@dataclass(frozen=True)
class WorkloadSpec:
    id: str
    title: str
    description: str
    tags: tuple[str, ...]
    license: str
    provenance: str
    task: str
    expected_exact: tuple[str, ...]
    required_rules: tuple[str, ...]
    blocks: tuple[ContextBlock, ...]
    fixture_sha256: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], index: int) -> "WorkloadSpec":
        workload_id = _required_text(value.get("id"), f"workloads[{index}].id")
        if not _ID.fullmatch(workload_id):
            raise ValueError(f"workload id {workload_id!r} must match {_ID.pattern}")
        raw_blocks = value.get("blocks")
        if not isinstance(raw_blocks, list) or not raw_blocks:
            raise ValueError(f"workload {workload_id!r} blocks must be a non-empty array")
        if len(raw_blocks) > _MAX_BLOCKS_PER_WORKLOAD:
            raise ValueError(
                f"workload {workload_id!r} exceeds {_MAX_BLOCKS_PER_WORKLOAD} blocks"
            )
        blocks = tuple(
            _expand_block(item, block_index, workload_id)
            for block_index, item in enumerate(raw_blocks)
        )
        ids = [block.id for block in blocks]
        if len(set(ids)) != len(ids):
            raise ValueError(f"workload {workload_id!r} has duplicate block IDs")

        expected_exact = _string_list(
            value.get("expected_exact"),
            f"workload {workload_id}.expected_exact",
        )
        required_rules = _string_list(
            value.get("required_rules"),
            f"workload {workload_id}.required_rules",
        )
        extracted = {
            anchor.value
            for block in blocks
            for anchor in unique_anchors(extract_anchors(block.content))
        }
        missing_exact = sorted(set(expected_exact) - extracted)
        if missing_exact:
            raise ValueError(
                f"workload {workload_id!r} declares exact values not recognized by the "
                f"anchor extractor: {', '.join(missing_exact)}"
            )
        authority_text = "\n".join(
            block.content
            for block in blocks
            if block.authoritative or block.role.lower() in {"system", "developer"}
        )
        missing_rules = [rule for rule in required_rules if rule not in authority_text]
        if missing_rules:
            raise ValueError(
                f"workload {workload_id!r} required rules must originate in authority "
                f"blocks: {', '.join(missing_rules)}"
            )

        normalized = {
            "id": workload_id,
            "title": _required_text(value.get("title"), f"workload {workload_id}.title"),
            "description": _required_text(
                value.get("description"), f"workload {workload_id}.description"
            ),
            "tags": list(_string_list(value.get("tags"), f"workload {workload_id}.tags")),
            "license": _required_text(
                value.get("license"), f"workload {workload_id}.license"
            ),
            "provenance": _required_text(
                value.get("provenance"), f"workload {workload_id}.provenance"
            ),
            "task": _required_text(value.get("task"), f"workload {workload_id}.task"),
            "expected_exact": list(expected_exact),
            "required_rules": list(required_rules),
            "blocks": [_block_to_dict(block) for block in blocks],
        }
        return cls(
            id=workload_id,
            title=normalized["title"],
            description=normalized["description"],
            tags=tuple(normalized["tags"]),
            license=normalized["license"],
            provenance=normalized["provenance"],
            task=normalized["task"],
            expected_exact=expected_exact,
            required_rules=required_rules,
            blocks=blocks,
            fixture_sha256=_sha256_json(normalized),
        )

    def to_dict(self, *, include_blocks: bool = True) -> dict[str, Any]:
        value: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "tags": list(self.tags),
            "license": self.license,
            "provenance": self.provenance,
            "task": self.task,
            "expected_exact": list(self.expected_exact),
            "required_rules": list(self.required_rules),
            "fixture_sha256": self.fixture_sha256,
        }
        if include_blocks:
            value["blocks"] = [_block_to_dict(block) for block in self.blocks]
        return value


@dataclass(frozen=True)
class WorkloadManifest:
    suite_id: str
    version: str
    title: str
    license: str
    provenance: str
    workloads: tuple[WorkloadSpec, ...]
    source_sha256: str
    schema_version: str = WORKLOAD_MANIFEST_SCHEMA

    def to_dict(self, *, include_blocks: bool = False) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "suite_id": self.suite_id,
            "version": self.version,
            "title": self.title,
            "license": self.license,
            "provenance": self.provenance,
            "source_sha256": self.source_sha256,
            "workloads": [
                workload.to_dict(include_blocks=include_blocks)
                for workload in self.workloads
            ],
        }


def load_workload_manifest(path: str | Path | None = None) -> WorkloadManifest:
    source = Path(path) if path is not None else DEFAULT_MANIFEST
    raw = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("workload manifest must be a JSON object")
    require_schema(raw, WORKLOAD_MANIFEST_SCHEMA, allow_legacy_missing=False)
    raw_workloads = raw.get("workloads")
    if not isinstance(raw_workloads, list) or not raw_workloads:
        raise ValueError("workload manifest workloads must be a non-empty array")
    if len(raw_workloads) > _MAX_WORKLOADS:
        raise ValueError(f"workload manifest exceeds {_MAX_WORKLOADS} workloads")
    workloads = tuple(
        WorkloadSpec.from_dict(item, index)
        for index, item in enumerate(raw_workloads)
        if isinstance(item, dict)
    )
    if len(workloads) != len(raw_workloads):
        raise ValueError("every workload manifest entry must be an object")
    ids = [workload.id for workload in workloads]
    if len(set(ids)) != len(ids):
        raise ValueError("workload manifest contains duplicate workload IDs")
    return WorkloadManifest(
        suite_id=_required_text(raw.get("suite_id"), "suite_id"),
        version=_required_text(raw.get("version"), "version"),
        title=_required_text(raw.get("title"), "title"),
        license=_required_text(raw.get("license"), "license"),
        provenance=_required_text(raw.get("provenance"), "provenance"),
        workloads=workloads,
        source_sha256=_sha256_json(raw),
    )


def _all_anchor_values(blocks: Iterable[ContextBlock]) -> tuple[str, ...]:
    seen: set[tuple[str, str]] = set()
    values: list[str] = []
    for block in blocks:
        for anchor in unique_anchors(extract_anchors(block.content)):
            key = (anchor.kind, anchor.value)
            if key not in seen:
                seen.add(key)
                values.append(anchor.value)
    return tuple(values)


def _artifacts_exist(plan: RoutePlan, root: Path) -> bool:
    for routed in plan.blocks:
        if routed.lane in {Lane.IMAGE, Lane.CRUMB, Lane.SUMMARY}:
            if not routed.artifact:
                return False
            for relative in routed.artifact.split(","):
                if not (root / relative).is_file():
                    return False
    return all(
        (root / name).is_file()
        for name in ("plan.json", "report.html", "anchors-all.txt")
    )


def _run_workload(
    manifest: WorkloadManifest,
    workload: WorkloadSpec,
    profile_name: str,
    output_dir: Path,
) -> dict[str, Any]:
    policy = resolve_profile(profile_name)
    blocks = list(workload.blocks)
    first = route_blocks(blocks, policy.config, profile_name=policy.name)
    second = route_blocks(blocks, policy.config, profile_name=policy.name)
    deterministic_plan = first.to_dict() == second.to_dict()

    run_root = output_dir / "runs" / workload.id / profile_name
    plan = route_to_directory(
        blocks,
        run_root,
        policy.config,
        profile_name=policy.name,
    )
    by_id = {item.block_id: item for item in plan.blocks}
    exact_values = _all_anchor_values(blocks)
    sidecars = (run_root / "anchors-all.txt").read_text(encoding="utf-8")
    exact_found = sum(1 for value in exact_values if value in sidecars)

    authority_blocks = [
        block
        for block in blocks
        if block.authoritative or block.role.lower() in {"system", "developer"}
    ]
    recent_blocks = [
        block for block in blocks if block.age_turns <= policy.config.recent_turns
    ]
    rule_blocks_exact = all(
        any(
            rule in block.content and by_id[block.id].lane is Lane.EXACT
            for block in authority_blocks
        )
        for rule in workload.required_rules
    )
    image_routes = [item for item in plan.blocks if item.lane is Lane.IMAGE]
    image_policy_honored = (
        not image_routes if not policy.config.vision_allowed else True
    ) and all(item.artifact for item in image_routes)

    checks = {
        "all_exact_anchors_preserved": exact_found == len(exact_values),
        "declared_exact_values_preserved": all(
            value in sidecars for value in workload.expected_exact
        ),
        "authority_blocks_stay_exact": all(
            by_id[block.id].lane is Lane.EXACT for block in authority_blocks
        ),
        "required_rules_stay_exact": rule_blocks_exact,
        "recent_context_stays_exact": all(
            by_id[block.id].lane is Lane.EXACT for block in recent_blocks
        ),
        "image_policy_honored": image_policy_honored,
        "strict_exact_is_all_exact": (
            profile_name != "strict-exact"
            or all(item.lane is Lane.EXACT for item in plan.blocks)
        ),
        "deterministic_plan": deterministic_plan,
        "referenced_artifacts_exist": _artifacts_exist(plan, run_root),
    }
    return {
        "schema_version": WORKLOAD_RESULT_SCHEMA,
        "suite_id": manifest.suite_id,
        "suite_version": manifest.version,
        "workload_id": workload.id,
        "workload_title": workload.title,
        "workload_tags": list(workload.tags),
        "fixture_sha256": workload.fixture_sha256,
        "manifest_sha256": manifest.source_sha256,
        "profile": profile_name,
        "resolved_config": asdict(policy.config),
        "task": workload.task,
        "expected_exact": list(workload.expected_exact),
        "required_rules": list(workload.required_rules),
        "exact_anchors": {"found": exact_found, "expected": len(exact_values)},
        "planning": {
            "baseline_estimated_tokens": plan.baseline_estimated_tokens,
            "routed_estimated_tokens": plan.routed_estimated_tokens,
            "estimated_token_reduction_percent": plan.estimated_token_reduction_percent,
        },
        "lanes": dict(Counter(item.lane.value for item in plan.blocks)),
        "checks": checks,
        "passed": all(checks.values()),
        "disclaimer": DISCLAIMER,
        "artifacts": {
            "root": str(run_root.relative_to(output_dir)),
            "plan": str((run_root / "plan.json").relative_to(output_dir)),
            "report": str((run_root / "report.html").relative_to(output_dir)),
            "anchors": str((run_root / "anchors-all.txt").relative_to(output_dir)),
        },
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _render_html(result: Mapping[str, Any]) -> str:
    summary = result["summary"]
    rows = []
    for run in result["runs"]:
        badge = "PASS" if run["passed"] else "FAIL"
        rows.append(
            "<tr>"
            f"<td><strong>{escape(run['workload_id'])}</strong></td>"
            f"<td>{escape(run['profile'])}</td>"
            f"<td>{badge}</td>"
            f"<td>{run['planning']['baseline_estimated_tokens']:,}</td>"
            f"<td>{run['planning']['routed_estimated_tokens']:,}</td>"
            f"<td>{run['planning']['estimated_token_reduction_percent']}%</td>"
            f"<td>{run['exact_anchors']['found']}/{run['exact_anchors']['expected']}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CrumbContext workload suite</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
body {{ margin: 0; background: #07111f; color: #e6f3ff; }}
main {{ max-width: 1180px; margin: auto; padding: 48px 24px 80px; }}
h1 {{ font-size: clamp(2rem, 5vw, 4rem); margin-bottom: 8px; }}
p {{ color: #a9bdd1; line-height: 1.6; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin: 28px 0; }}
.card {{ background: #0e2033; border: 1px solid #28415b; border-radius: 14px; padding: 18px; }}
.card strong {{ display: block; font-size: 1.7rem; margin-top: 4px; }}
.table {{ overflow-x: auto; border: 1px solid #28415b; border-radius: 14px; }}
table {{ width: 100%; border-collapse: collapse; background: #0a1929; }}
th, td {{ padding: 12px 14px; text-align: left; border-bottom: 1px solid #20384e; }}
th {{ color: #7dd3fc; }}
code {{ color: #c4b5fd; }}
</style>
</head>
<body><main>
<p><strong>CRUMB ecosystem / reproducible evidence</strong></p>
<h1>Public multi-workload suite</h1>
<p>{escape(result['disclaimer'])}</p>
<div class="grid">
<div class="card">Workloads<strong>{summary['workloads']}</strong></div>
<div class="card">Profiles<strong>{summary['profiles']}</strong></div>
<div class="card">Runs passed<strong>{summary['passed_runs']}/{summary['runs']}</strong></div>
<div class="card">Exact anchors<strong>{summary['exact_anchors']['found']}/{summary['exact_anchors']['expected']}</strong></div>
<div class="card">Planning reduction<strong>{summary['estimated_token_reduction_percent']}%</strong></div>
</div>
<div class="table"><table>
<thead><tr><th>Workload</th><th>Profile</th><th>Status</th><th>Baseline est.</th><th>Routed est.</th><th>Reduction est.</th><th>Exact</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table></div>
<p>Schema <code>{escape(result['schema_version'])}</code> · manifest <code>{escape(result['manifest']['source_sha256'])}</code></p>
</main></body></html>
"""


def _write_card(path: Path, result: Mapping[str, Any]) -> None:
    summary = result["summary"]
    status = "PASS" if result["passed"] else "FAIL"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#07111f"/>
<rect x="55" y="55" width="1090" height="520" rx="28" fill="#0e2033" stroke="#28415b"/>
<text x="95" y="128" fill="#7dd3fc" font-family="Arial,sans-serif" font-size="25">CRUMB ecosystem · public evidence</text>
<text x="95" y="205" fill="#f8fafc" font-family="Arial,sans-serif" font-weight="700" font-size="53">Multi-workload routing suite</text>
<text x="95" y="282" fill="#c4b5fd" font-family="Arial,sans-serif" font-size="42">{status} · {summary['passed_runs']}/{summary['runs']} runs</text>
<text x="95" y="360" fill="#e2e8f0" font-family="Arial,sans-serif" font-size="31">{summary['workloads']} workloads × {summary['profiles']} profiles</text>
<text x="95" y="414" fill="#e2e8f0" font-family="Arial,sans-serif" font-size="31">Exact anchors {summary['exact_anchors']['found']}/{summary['exact_anchors']['expected']}</text>
<text x="95" y="468" fill="#e2e8f0" font-family="Arial,sans-serif" font-size="31">Planning reduction {summary['estimated_token_reduction_percent']}%</text>
<text x="95" y="530" fill="#94a3b8" font-family="Arial,sans-serif" font-size="21">Deterministic estimates — not provider billing or model quality</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def run_workload_suite(
    *,
    output_dir: str | Path,
    manifest_path: str | Path | None = None,
    profiles: Sequence[str] | None = None,
) -> dict[str, Any]:
    manifest = load_workload_manifest(manifest_path)
    selected = tuple(profiles) if profiles is not None else DEFAULT_PROFILES
    if not selected:
        raise ValueError("at least one routing profile is required")
    if len(set(selected)) != len(selected):
        raise ValueError("routing profiles must not contain duplicates")
    available = set(available_profiles())
    unknown = sorted(set(selected) - available)
    if unknown:
        raise ValueError(f"unknown routing profiles: {', '.join(unknown)}")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    expanded_manifest = manifest.to_dict(include_blocks=True)
    _write_json(root / "manifest-expanded.json", expanded_manifest)

    runs: list[dict[str, Any]] = []
    for workload in manifest.workloads:
        for profile_name in selected:
            result = _run_workload(manifest, workload, profile_name, root)
            runs.append(result)
            _write_json(
                root / "results" / f"{workload.id}--{profile_name}.json",
                result,
            )

    baseline_total = sum(
        run["planning"]["baseline_estimated_tokens"] for run in runs
    )
    routed_total = sum(run["planning"]["routed_estimated_tokens"] for run in runs)
    exact_found = sum(run["exact_anchors"]["found"] for run in runs)
    exact_expected = sum(run["exact_anchors"]["expected"] for run in runs)
    lane_totals: Counter[str] = Counter()
    for run in runs:
        lane_totals.update(run["lanes"])
    estimated_reduction = (
        round((baseline_total - routed_total) * 100 / baseline_total, 1)
        if baseline_total
        else 0.0
    )
    result = {
        "schema_version": WORKLOAD_SUITE_RESULT_SCHEMA,
        "passed": all(run["passed"] for run in runs),
        "generated_from": "public-synthetic-fixtures",
        "manifest": manifest.to_dict(include_blocks=False),
        "profiles": list(selected),
        "summary": {
            "workloads": len(manifest.workloads),
            "profiles": len(selected),
            "runs": len(runs),
            "passed_runs": sum(1 for run in runs if run["passed"]),
            "failed_runs": sum(1 for run in runs if not run["passed"]),
            "baseline_estimated_tokens": baseline_total,
            "routed_estimated_tokens": routed_total,
            "estimated_token_reduction_percent": estimated_reduction,
            "exact_anchors": {"found": exact_found, "expected": exact_expected},
            "lanes": dict(lane_totals),
        },
        "runs": runs,
        "disclaimer": DISCLAIMER,
    }
    _write_json(root / "suite.json", result)
    (root / "report.html").write_text(_render_html(result), encoding="utf-8")
    _write_card(root / "share-card.svg", result)
    return result


__all__ = [
    "DEFAULT_MANIFEST",
    "DEFAULT_PROFILES",
    "DISCLAIMER",
    "WorkloadManifest",
    "WorkloadSpec",
    "load_workload_manifest",
    "run_workload_suite",
]
